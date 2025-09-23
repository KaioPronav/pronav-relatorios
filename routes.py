from flask import request, send_file, render_template, jsonify, Response
from functools import wraps
import requests
from models import ReportRequest, Activity
from normalizers import normalize_payload
from pdf_service import PDFService
from config import Config
import json
from datetime import datetime

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
    
    @app.teardown_appcontext
    def close_db(error):
        db_manager.close_db(error)

    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception:
            return "PRONAV Report Service"

    @app.route('/salvar-rascunho', methods=['POST'])
    @handle_errors(logger)
    def salvar_rascunho():
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

        norm = normalize_payload(payload)
        report_request = ReportRequest(**norm)
        atividades_list = [a.model_dump() for a in report_request.activities]
        equipments_list = report_request.EQUIPAMENTOS or []

        now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        with db_manager.db_connection() as db:
            cur = db.execute('''
                INSERT INTO reports (
                    user_id, client, ship, contact, work, location, os_number,
                    equipment, manufacturer, model, serial_number, reported_problem,
                    service_performed, result, pending_issues, client_material,
                    pronav_material, activities, equipments, city, state, created_at, updated_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            report_id = cur.lastrowid
        return jsonify({'message': 'Rascunho salvo', 'report_id': report_id}), 201

    @app.route('/relatorios-salvos', methods=['GET'])
    @handle_errors(logger)
    def relatorios_salvos():
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id é obrigatório na query string'}), 400
        with db_manager.db_connection() as db:
            rows = db.execute('SELECT id, client, ship, status, created_at, updated_at FROM reports WHERE user_id = ? ORDER BY COALESCE(updated_at, created_at) DESC', [user_id]).fetchall()
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
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

        norm = normalize_payload(payload)
        report_request = ReportRequest(**norm)
        atividades_list = [a.model_dump() for a in report_request.activities]
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
            if cur.rowcount == 0:
                return jsonify({'error': 'Relatório não encontrado'}), 404
        return jsonify({'message': 'Relatório atualizado'}), 200

    @app.route('/relatorio/<int:report_id>', methods=['DELETE'])
    @handle_errors(logger)
    def delete_report(report_id):
        with db_manager.db_connection() as db:
            cur = db.execute('DELETE FROM reports WHERE id = ?', [report_id])
            db.commit()
            if cur.rowcount == 0:
                return jsonify({'error': 'Relatório não encontrado'}), 404
        return jsonify({'message': 'Relatório removido'}), 200

    @app.route('/gerar-relatorio', methods=['POST'])
    @handle_errors(logger)
    def gerar_relatorio():
        form_data = request.get_json()
        if not form_data:
            return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

        norm = normalize_payload(form_data)
        report_id = norm.get('report_id') or form_data.get('report_id')

        report_request = ReportRequest(**norm)
        atividades_list = [a.model_dump() for a in report_request.activities]
        equipments_list = report_request.EQUIPAMENTOS or []

        now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        with db_manager.db_connection() as db:
            if report_id:
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
                    report_id
                ])
                if cur.rowcount == 0:
                    return jsonify({'error': 'Relatório para atualizar não encontrado'}), 404
                db.commit()
                saved_report_id = report_id
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
                saved_report_id = cur.lastrowid

        pdf_buffer, saved_report_id = pdf_service.generate_pdf(report_request, atividades_list, equipments_list, saved_report_id)
        filename = pdf_service.get_filename(report_request, equipments_list)

        resp = send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
        try:
            resp.headers['X-Report-Id'] = str(saved_report_id)
        except Exception:
            pass
        return resp