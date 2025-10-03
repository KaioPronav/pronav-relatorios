# core/routes.py
import io
import inspect
import json
import logging
from typing import Optional, Any, List, Dict, Union
from datetime import datetime
from functools import wraps

from flask import request, send_file, render_template, jsonify

from core.models import ReportRequest
from core.normalizers import normalize_payload
from core.pdf_service import PDFService
from core.config import Config

logger = logging.getLogger(__name__)


def handle_errors(logger):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.exception("Unexpected error")
                return jsonify({'error': 'Erro interno do servidor', 'msg': str(e)}), 500
        return decorated
    return decorator


def init_routes(app, db_manager, logger):
    pdf_service = PDFService(Config)

    def _attach_captions_to_report_request(report_request_obj: Any, captions: List[str]) -> Union[Any, bool]:
        """
        Tenta diversas estratégias para garantir que o objeto report_request contenha as legendas:
         - atribuição direta (report_request.captions = captions)
         - setattr
         - manipulação de __dict__
         - usar métodos de cópia do pydantic (copy / model_copy) se disponíveis (retorna novo objeto)
        Retorna:
         - True  => foi anexado in-place
         - novo_obj => objeto substituto (quando usamos copy/model_copy)
         - False => falhou em anexar
        """
        if report_request_obj is None:
            return False
        try:
            # 1) tentar atribuição direta
            try:
                report_request_obj.captions = captions
                return True
            except Exception:
                pass

            # 2) tentar setattr
            try:
                setattr(report_request_obj, 'captions', captions)
                return True
            except Exception:
                pass

            # 3) tentar __dict__
            try:
                if hasattr(report_request_obj, '__dict__'):
                    report_request_obj.__dict__['captions'] = captions
                    return True
            except Exception:
                pass

            # 4) tentar copy/update (pydantic v1 .copy / v2 .model_copy)
            try:
                if hasattr(report_request_obj, 'copy'):
                    new_rr = report_request_obj.copy(update={'captions': captions})
                    return new_rr
            except Exception:
                pass
            try:
                if hasattr(report_request_obj, 'model_copy'):
                    new_rr = report_request_obj.model_copy(update={'captions': captions})
                    return new_rr
            except Exception:
                pass
        except Exception:
            logger.exception("Erro ao tentar anexar captions ao report_request")
        return False

    @app.teardown_appcontext
    def close_db(error):
        try:
            db_manager.close_db(error)
        except Exception:
            logger.exception("Erro ao fechar DB no teardown")

    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception:
            return "PRONAV Report Service"

    @app.route('/salvar-rascunho', methods=['POST'])
    @handle_errors(logger)
    def salvar_rascunho():
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

        norm = normalize_payload(payload)
        report_request = ReportRequest(**norm)
        atividades_list = [a.model_dump() for a in getattr(report_request, 'activities', [])]
        equipments_list = report_request.EQUIPAMENTOS or []

        now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        with db_manager.db_connection() as db:
            cur = db.execute('''
                INSERT INTO reports (
                    user_id, client, ship, contact, work, location, os_number,
                    equipment, manufacturer, model, serial_number, reported_problem,
                    service_performed, result, pending_issues, client_material,
                    pronav_material, activities, equipments, city, state, created_at, updated_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                report_request.user_id,
                report_request.CLIENTE,
                report_request.NAVIO,
                report_request.CONTATO,
                report_request.OBRA,
                report_request.LOCAL,
                report_request.OS,
                report_request.EQUIPAMENTO,
                report_request.FABRICANTE,
                report_request.MODELO,
                report_request.NUMERO_SERIE,
                report_request.PROBLEMA_RELATADO,
                report_request.SERVICO_REALIZADO,
                report_request.RESULTADO,
                report_request.PENDENCIAS,
                report_request.MATERIAL_CLIENTE,
                report_request.MATERIAL_PRONAV,
                json.dumps(atividades_list, ensure_ascii=False),
                json.dumps(equipments_list, ensure_ascii=False),
                report_request.CIDADE or '',
                report_request.ESTADO or '',
                now_iso,
                now_iso,
                'draft'
            ])
            db.commit()
            try:
                report_id = cur.lastrowid
            except Exception:
                report_id = None

        return jsonify({'message': 'Rascunho salvo', 'report_id': report_id}), 201

    @app.route('/relatorios-salvos', methods=['GET'])
    @handle_errors(logger)
    def relatorios_salvos():
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id é obrigatório na query string'}), 400
        with db_manager.db_connection() as db:
            rows = db.execute(
                'SELECT id, client, ship, status, created_at, updated_at FROM reports WHERE user_id = ? ORDER BY COALESCE(updated_at, created_at) DESC',
                [user_id]
            ).fetchall()
            result = []
            for r in rows:
                mapped = dict(r)
                mapped['CLIENTE'] = mapped.get('client')
                mapped['NAVIO'] = mapped.get('ship')
                result.append(mapped)
        return jsonify(result)

    @app.route('/relatorio/<int:report_id>', methods=['GET'])
    @handle_errors(logger)
    def get_report(report_id):
        with db_manager.db_connection() as db:
            row = db.execute('SELECT * FROM reports WHERE id = ?', [report_id]).fetchone()
            if not row:
                return jsonify({'error': 'Relatório não encontrado'}), 404
            data = db_manager.map_db_row_to_api(row)
        return jsonify(data)

    @app.route('/atualizar-relatorio/<int:report_id>', methods=['PUT'])
    @handle_errors(logger)
    def atualizar_relatorio(report_id):
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

        norm = normalize_payload(payload)
        report_request = ReportRequest(**norm)
        atividades_list = [a.model_dump() for a in getattr(report_request, 'activities', [])]
        equipments_list = report_request.EQUIPAMENTOS or []

        now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        with db_manager.db_connection() as db:
            cur = db.execute('''
                UPDATE reports SET
                    client=?, ship=?, contact=?, work=?, location=?, os_number=?,
                    equipment=?, manufacturer=?, model=?, serial_number=?,
                    reported_problem=?, service_performed=?, result=?, pending_issues=?,
                    client_material=?, pronav_material=?, activities=?, equipments=?, city=?, state=?, updated_at=?, status='draft'
                WHERE id=?
            ''', [
                report_request.CLIENTE,
                report_request.NAVIO,
                report_request.CONTATO,
                report_request.OBRA,
                report_request.LOCAL,
                report_request.OS,
                report_request.EQUIPAMENTO,
                report_request.FABRICANTE,
                report_request.MODELO,
                report_request.NUMERO_SERIE,
                report_request.PROBLEMA_RELATADO,
                report_request.SERVICO_REALIZADO,
                report_request.RESULTADO,
                report_request.PENDENCIAS,
                report_request.MATERIAL_CLIENTE,
                report_request.MATERIAL_PRONAV,
                json.dumps(atividades_list, ensure_ascii=False),
                json.dumps(equipments_list, ensure_ascii=False),
                report_request.CIDADE or '',
                report_request.ESTADO or '',
                now_iso,
                report_id
            ])
            db.commit()
            if getattr(cur, 'rowcount', None) == 0:
                return jsonify({'error': 'Relatório não encontrado'}), 404
        return jsonify({'message': 'Relatório atualizado'}), 200

    @app.route('/relatorio/<int:report_id>', methods=['DELETE'])
    @handle_errors(logger)
    def delete_report(report_id):
        with db_manager.db_connection() as db:
            cur = db.execute('DELETE FROM reports WHERE id = ?', [report_id])
            db.commit()
            if getattr(cur, 'rowcount', None) == 0:
                return jsonify({'error': 'Relatório não encontrado'}), 404
        return jsonify({'message': 'Relatório removido'}), 200

    @app.route('/gerar-relatorio', methods=['POST'])
    @handle_errors(logger)
    def gerar_relatorio():
        """
        Aceita:
         - application/json com o payload do relatório (sem imagens), ou
         - multipart/form-data com:
             - campo 'payload' (JSON string) e
             - arquivos em 'images' (lista de arquivos)
             - legendas em 'captions[]' ou 'caption_0', 'caption_1', ...
        Esta rota agora garante que as legendas (captions) sejam extraídas tanto do payload JSON
        quanto do form-data e que sejam repassadas ao serviço de PDF de maneira consistente.
        """
        payload_json = None
        images_from_form = []

        # --- tentar multipart/form-data primeiro (se enviado) ---
        content_type = (request.content_type or '').lower()
        is_multipart = 'multipart/form-data' in content_type
        if is_multipart:
            raw_payload = request.form.get('payload') if 'payload' in request.form else None
            if isinstance(raw_payload, (str, bytes)):
                try:
                    payload_json = json.loads(raw_payload)
                except Exception:
                    payload_json = None
            else:
                payload_json = None

            try:
                if 'images' in request.files:
                    images_from_form = request.files.getlist('images') or []
            except Exception:
                images_from_form = []

        if payload_json is None:
            payload_json = request.get_json(silent=True)

        if not payload_json:
            return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

        # --- EXTRAI/UNIFICA legendas (captions) ---
        captions_list: List[str] = []
        try:
            if isinstance(payload_json, dict):
                c1 = payload_json.get('captions')
                c2 = payload_json.get('captions[]')
                if isinstance(c1, list):
                    captions_list = [str(x) if x is not None else '' for x in c1]
                elif isinstance(c2, list):
                    captions_list = [str(x) if x is not None else '' for x in c2]
        except Exception:
            captions_list = []

        if not captions_list and is_multipart:
            try:
                raw_list = request.form.getlist('captions') or request.form.getlist('captions[]') or []
                if raw_list:
                    captions_list = [str(x) if x is not None else '' for x in raw_list]
            except Exception:
                captions_list = []

        if not captions_list:
            try:
                files_count = len(images_from_form) if images_from_form else 0
                if files_count:
                    tmp = []
                    for i in range(files_count):
                        val = request.form.get(f'caption_{i}', '')
                        tmp.append(val or '')
                    captions_list = tmp
            except Exception:
                captions_list = []

        # garantir que payload_json contenha as captions (por compatibilidade)
        try:
            if isinstance(payload_json, dict):
                payload_json['captions'] = captions_list
                payload_json['captions[]'] = captions_list
        except Exception:
            logger.exception("Não foi possível injetar captions no payload_json (ignorar se não crítico)")

        # normalizar payload e construir objetos
        norm = normalize_payload(payload_json)
        report_id_from_payload = norm.get('report_id') or payload_json.get('report_id')

        report_request = ReportRequest(**norm)

        # --- ANEXAR LEGENDAS AO OBJETO report_request (robusto) ---
        attach_result = _attach_captions_to_report_request(report_request, captions_list)
        if attach_result is False:
            logger.warning("Não foi possível anexar captions diretamente ao objeto ReportRequest; o serviço poderá não encontrar legendas.")
        elif attach_result is True:
            logger.debug("Captions anexadas ao report_request in-place.")
        else:
            # attach_result é um novo objeto (cópia) retornado pela estratégia de copy/model_copy
            report_request = attach_result
            logger.debug("ReportRequest substituído por cópia com captions (copy/model_copy).")

        atividades_list = [a.model_dump() for a in getattr(report_request, 'activities', [])]
        equipments_list = report_request.EQUIPAMENTOS or []

        now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        with db_manager.db_connection() as db:
            if report_id_from_payload:
                cur = db.execute('''
                    UPDATE reports SET
                        client=?, ship=?, contact=?, work=?, location=?, os_number=?,
                        equipment=?, manufacturer=?, model=?, serial_number=?,
                        reported_problem=?, service_performed=?, result=?, pending_issues=?,
                        client_material=?, pronav_material=?, activities=?, equipments=?, city=?, state=?, updated_at=?, status='final'
                    WHERE id=?
                ''', [
                    report_request.CLIENTE,
                    report_request.NAVIO,
                    report_request.CONTATO,
                    report_request.OBRA,
                    report_request.LOCAL,
                    report_request.OS,
                    report_request.EQUIPAMENTO,
                    report_request.FABRICANTE,
                    report_request.MODELO,
                    report_request.NUMERO_SERIE,
                    report_request.PROBLEMA_RELATADO,
                    report_request.SERVICO_REALIZADO,
                    report_request.RESULTADO,
                    report_request.PENDENCIAS,
                    report_request.MATERIAL_CLIENTE,
                    report_request.MATERIAL_PRONAV,
                    json.dumps(atividades_list, ensure_ascii=False),
                    json.dumps(equipments_list, ensure_ascii=False),
                    report_request.CIDADE or '',
                    report_request.ESTADO or '',
                    now_iso,
                    report_id_from_payload
                ])
                if getattr(cur, 'rowcount', None) == 0:
                    return jsonify({'error': 'Relatório para atualizar não encontrado'}), 404
                db.commit()
                saved_report_id: Optional[int] = report_id_from_payload
            else:
                cur = db.execute('''
                    INSERT INTO reports (
                        user_id, client, ship, contact, work, location, os_number,
                        equipment, manufacturer, model, serial_number, reported_problem,
                        service_performed, result, pending_issues, client_material,
                        pronav_material, activities, equipments, city, state, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    report_request.user_id,
                    report_request.CLIENTE,
                    report_request.NAVIO,
                    report_request.CONTATO,
                    report_request.OBRA,
                    report_request.LOCAL,
                    report_request.OS,
                    report_request.EQUIPAMENTO,
                    report_request.FABRICANTE,
                    report_request.MODELO,
                    report_request.NUMERO_SERIE,
                    report_request.PROBLEMA_RELATADO,
                    report_request.SERVICO_REALIZADO,
                    report_request.RESULTADO,
                    report_request.PENDENCIAS,
                    report_request.MATERIAL_CLIENTE,
                    report_request.MATERIAL_PRONAV,
                    json.dumps(atividades_list, ensure_ascii=False),
                    json.dumps(equipments_list, ensure_ascii=False),
                    report_request.CIDADE or '',
                    report_request.ESTADO or '',
                    'final',
                    now_iso,
                    now_iso
                ])
                db.commit()
                try:
                    saved_report_id = cur.lastrowid  # type: Optional[int]
                except Exception:
                    saved_report_id = None

        # preparar images_list para passar ao PDFService
        images_list_for_pdf: Optional[List[Dict[str, Any]]] = None
        try:
            if images_from_form:
                images_list_for_pdf = []
                try:
                    if not isinstance(captions_list, list):
                        captions_list = []
                except Exception:
                    captions_list = []
                for idx, f in enumerate(images_from_form):
                    try:
                        content = f.read()
                        if not isinstance(content, (bytes, bytearray)):
                            continue
                        caption_for_image = ''
                        try:
                            if idx < len(captions_list):
                                caption_for_image = captions_list[idx] or ''
                            else:
                                caption_for_image = request.form.get(f'caption_{idx}', '') or ''
                        except Exception:
                            caption_for_image = ''
                        images_list_for_pdf.append({'bytes': bytes(content), 'caption': caption_for_image})
                    except Exception:
                        logger.exception("Erro ao processar arquivo de imagem do form (idx=%s): %s", idx, getattr(f, "filename", "unknown"))
                        continue
            else:
                imgs_from_payload = None
                try:
                    imgs_from_payload = getattr(report_request, 'IMAGES', None)
                except Exception:
                    imgs_from_payload = None
                if not imgs_from_payload:
                    imgs_from_payload = getattr(report_request, 'images', None)
                if imgs_from_payload:
                    images_list_for_pdf = []
                    for it in imgs_from_payload:
                        try:
                            if isinstance(it, dict):
                                b = it.get('bytes') or it.get('content') or it.get('data')
                                c = it.get('caption') or it.get('legend') or ''
                                images_list_for_pdf.append({'bytes': b, 'caption': c})
                            else:
                                images_list_for_pdf.append({'bytes': it, 'caption': ''})
                        except Exception:
                            images_list_for_pdf.append({'bytes': it, 'caption': ''})
        except Exception:
            images_list_for_pdf = None

        # garantir aplicação de captions_list a imagens sem caption
        try:
            if images_list_for_pdf and isinstance(images_list_for_pdf, list):
                for i, entry in enumerate(images_list_for_pdf):
                    try:
                        if not entry.get('caption'):
                            if i < len(captions_list):
                                entry['caption'] = captions_list[i] or ''
                            else:
                                entry['caption'] = entry.get('caption') or ''
                    except Exception:
                        entry['caption'] = entry.get('caption') or ''
        except Exception:
            logger.exception("Erro ao associar captions às imagens (ignorar se não crítico)")

        # CHAVE: passar o report_request (objeto) ao PDFService — agora o objeto contém as captions
        saved_report_id_for_pdf: Optional[str] = str(saved_report_id) if saved_report_id is not None else None

        res = pdf_service.generate_pdf(report_request, atividades_list, equipments_list, saved_report_id_for_pdf, images_list_for_pdf)

        if res is None:
            logger.exception("routes: pdf_service.generate_pdf retornou None (isso não deveria ocorrer).")
            raise RuntimeError("pdf_service.generate_pdf retornou None — verifique logs do servidor para traceback.")

        # Normalizar retorno para BytesIO
        pdf_buffer: Optional[io.BytesIO] = None
        returned_saved_id: Optional[Any] = None

        if isinstance(res, (tuple, list)):
            if len(res) >= 1:
                pdf_buffer = res[0]
            if len(res) >= 2:
                returned_saved_id = res[1]
        else:
            pdf_buffer = res

        if isinstance(pdf_buffer, (bytes, bytearray)):
            pdf_buffer = io.BytesIO(pdf_buffer)

        if pdf_buffer is not None and not isinstance(pdf_buffer, io.BytesIO):
            if hasattr(pdf_buffer, 'read'):
                try:
                    content = pdf_buffer.read()
                    if isinstance(content, (bytes, bytearray)):
                        pdf_buffer = io.BytesIO(content)
                    else:
                        if hasattr(pdf_buffer, 'getvalue'):
                            raw = pdf_buffer.getvalue()
                            if raw is None:
                                raise RuntimeError("getvalue() retornou None — não foi possível normalizar o conteúdo do PDF")
                            if isinstance(raw, (bytes, bytearray)):
                                pdf_buffer = io.BytesIO(raw)
                            else:
                                try:
                                    pdf_buffer = io.BytesIO(bytes(raw))
                                except Exception:
                                    raise RuntimeError("Tipo retornado pelo serviço PDF não é compatível (getvalue retornou tipo não conversível)")
                        else:
                            raise RuntimeError("Tipo retornado pelo serviço PDF não é compatível (read retornou não-bytes).")
                except Exception as e:
                    logger.exception("Erro ao normalizar objeto retornado pelo generate_pdf: %s", e)
                    raise
            else:
                logger.exception("Tipo retornado por generate_pdf não é compatível com send_file")
                raise RuntimeError("O serviço de PDF retornou um tipo inválido para envio (esperado BytesIO/bytes/file-like).")

        if pdf_buffer is None:
            logger.exception("Nenhum buffer PDF disponível após chamada a generate_pdf.")
            raise RuntimeError("Nenhum PDF foi gerado pelo serviço.")

        try:
            pdf_buffer.seek(0)
        except Exception:
            logger.debug("Não foi possível realizar seek no buffer do PDF (ignorar se for stream já posicionado).")

        filename = pdf_service.get_filename(report_request, equipments_list)

        send_file_kwargs = {'mimetype': 'application/pdf', 'as_attachment': True}
        try:
            sig = inspect.signature(send_file)
            if 'download_name' in sig.parameters:
                send_file_kwargs['download_name'] = filename
            elif 'attachment_filename' in sig.parameters:
                send_file_kwargs['attachment_filename'] = filename
            else:
                send_file_kwargs['download_name'] = filename
        except Exception:
            send_file_kwargs['download_name'] = filename

        resp = send_file(pdf_buffer, **send_file_kwargs)

        try:
            header_id = returned_saved_id if returned_saved_id is not None else saved_report_id
            if header_id is not None:
                resp.headers['X-Report-Id'] = str(header_id)
        except Exception:
            logger.exception("Não foi possível setar X-Report-Id no response headers")

        return resp

    # fim init_routes
