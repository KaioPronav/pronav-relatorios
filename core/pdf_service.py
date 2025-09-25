# core/pdf_service.py
import io
import os
import re
import pkgutil
import unicodedata
import string
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from core.normalizers import ensure_upper_safe
from core.utils import format_date_br


class HR(Flowable):
    """Linha horizontal fina usada para indicar corte/continuação."""
    def __init__(self, width, thickness=0.6, pad_top=1, pad_bottom=1):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.pad_top = pad_top
        self.pad_bottom = pad_bottom
        # altura total do flowable (considerando pads)
        self.height = float(self.pad_top + self.thickness + self.pad_bottom)

    def wrap(self, aW, aH):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        x0 = 0
        x1 = self.width
        y = self.pad_bottom
        c.setLineWidth(self.thickness)
        c.line(x0, y, x1, y)
        c.restoreState()


class PDFService:
    def __init__(self, config):
        self.config = config
        self.setup_fonts()

        # Layout constants
        self.LINE_WIDTH = 0.6
        self.GRAY = colors.HexColor('#D9D9D9')
        # pads compactos para economizar espaço
        self.SMALL_PAD = 2
        self.MED_PAD = 3
        self.BASE_TITLE_FONT_SIZE = 9.5
        self.BASE_LABEL_FONT_SIZE = 8.5
        self.BASE_VALUE_FONT_SIZE = 8.1

    def setup_fonts(self):
        self.FONT_REGULAR = 'Helvetica'
        self.FONT_BOLD = 'Helvetica-Bold'
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            arial = os.path.join(BASE_DIR, 'arial.ttf')
            arialbd = os.path.join(BASE_DIR, 'arialbd.ttf')
            if os.path.exists(arial):
                pdfmetrics.registerFont(TTFont('Arial', arial))
                self.FONT_REGULAR = 'Arial'
                if os.path.exists(arialbd):
                    pdfmetrics.registerFont(TTFont('Arial-Bold', arialbd))
                    self.FONT_BOLD = 'Arial-Bold'
                else:
                    pdfmetrics.registerFont(TTFont('Arial-Bold', arial))
                    self.FONT_BOLD = 'Arial-Bold'
        except Exception:
            pass

    # -------------------------------
    # Sanitização para Paragraphs
    # -------------------------------
    def sanitize_for_paragraph(self, text):
        try:
            if text is None:
                return ''
            txt = str(text)
            txt = txt.replace('\r\n', '\n').replace('\r', '\n')
            escaped = xml_escape(txt)
            safe = escaped.replace('\n', '<br/>')
            return safe
        except Exception:
            try:
                return xml_escape(str(text or '')).replace('\n', '<br/>')
            except Exception:
                return ''

    # -------------------------------
    # Estimador de altura (simples)
    # -------------------------------
    def estimate_height(self, flowables, avail_width, avail_height):
        h = 0.0
        from reportlab.platypus import Spacer as _Spacer
        for f in flowables:
            try:
                if isinstance(f, _Spacer):
                    h += f.height
                    continue
                w, fh = f.wrap(avail_width, avail_height)
                h += fh
            except Exception:
                h += 10
        return h

    # -------------------------------
    # Geração do PDF
    # -------------------------------
    def generate_pdf(self, report_request, atividades_list, equipments_list, saved_report_id):
        pdf_buffer = io.BytesIO()
        PAGE_SIZE = letter
        PAGE_W, PAGE_H = PAGE_SIZE

        # margins
        MARG = 0.35 * inch  # left/right fixed
        preserved_top_margin_base = 0.25 * inch
        preserved_bottom_margin_base = 0.12 * inch

        square_side = 1.18 * inch
        header_row0 = 0.22 * inch
        header_row = 0.26 * inch
        header_height_base = header_row0 + header_row * 3

        sig_header_h_base = 0.24 * inch
        sig_area_h_base = 0.6 * inch
        footer_h_base = 0.24 * inch  # leve aumento p/ legibilidade
        footer_total_height_base = footer_h_base + sig_header_h_base + sig_area_h_base

        # scaling bounds
        MIN_SCALE = float(getattr(self.config, 'MIN_SCALE', 0.55))
        MAX_SCALE = 1.0
        margin_reduction_factors = [1.0, 0.9, 0.8, 0.7]

        # -------------------------------
        # Helpers: normalization and logo finding
        # -------------------------------
        def _norm_text(cell):
            try:
                if hasattr(cell, 'getPlainText'):
                    s = cell.getPlainText()
                else:
                    s = str(cell or '')
            except Exception:
                s = str(cell or '')
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not unicodedata.category(ch).startswith('M'))
            s = re.sub(r'\s+', ' ', s).strip()
            s = s.strip(" " + string.punctuation)
            return s.lower()

        def find_logo_bytes(config_obj):
            logo_val = getattr(config_obj, 'LOGO_PATH', None)
            if isinstance(logo_val, (bytes, bytearray)):
                try:
                    return bytes(logo_val)
                except Exception:
                    pass
            if logo_val and isinstance(logo_val, str):
                p = Path(logo_val)
                if not p.is_absolute():
                    base = Path(__file__).resolve().parent
                    p_try = (base / p).resolve()
                    if p_try.exists():
                        try:
                            return p_try.read_bytes()
                        except Exception:
                            pass
                try:
                    if p.exists():
                        return p.read_bytes()
                except Exception:
                    pass
            base = Path(__file__).resolve().parent.parent
            candidates = [
                base / 'static' / 'images' / 'logo.png',
                base / 'static' / 'logo.png',
                Path.cwd() / 'static' / 'images' / 'logo.png',
                Path.cwd() / 'static' / 'logo.png',
                Path(__file__).resolve().parent / 'static' / 'images' / 'logo.png'
            ]
            for c in candidates:
                try:
                    if c.exists():
                        return c.read_bytes()
                except Exception:
                    pass
            try:
                for pkg_name in (getattr(self, '__package__', None), 'pronav', None):
                    try:
                        if pkg_name:
                            b = pkgutil.get_data(pkg_name, 'static/images/logo.png')
                            if b:
                                return b
                    except Exception:
                        continue
            except Exception:
                pass
            return None

        def make_styles(scale=1.0):
            base_title = max(6.0, self.BASE_TITLE_FONT_SIZE * scale)
            base_label = max(6.0, self.BASE_LABEL_FONT_SIZE * scale)
            base_value = max(6.0, self.BASE_VALUE_FONT_SIZE * scale)

            try:
                resp_mult = float(getattr(self.config, 'RESPONSE_VALUE_MULTIPLIER', 1.0))
            except Exception:
                resp_mult = 1.0
            try:
                label_mult = float(getattr(self.config, 'LABEL_VALUE_MULTIPLIER', 1.05))
            except Exception:
                label_mult = 1.05

            response_sz = max(6.0, float(base_value) * resp_mult)
            label_sz = max(6.0, float(base_label) * label_mult)
            title_sz = max(7.0, base_title * 1.0)

            pad_small = max(1, int(max(1, self.SMALL_PAD * scale)))
            pad_med = max(1, int(max(1, self.MED_PAD * scale)))

            styles = getSampleStyleSheet()

            styles.add(ParagraphStyle(
                name='TitleCenter',
                fontName=self.FONT_BOLD,
                fontSize=title_sz,
                alignment=1,
                leading=max(8, title_sz * 1.15)
            ))

            styles.add(ParagraphStyle(
                name='label',
                fontName=self.FONT_BOLD,
                fontSize=label_sz,
                leading=max(7, label_sz * 1.05),
                alignment=0,
                spaceAfter=2,
                spaceBefore=2
            ))

            styles.add(ParagraphStyle(
                name='response',
                fontName=self.FONT_REGULAR,
                fontSize=response_sz,
                leading=max(7, response_sz * 1.06),
                alignment=0,
                spaceAfter=0,
                spaceBefore=0
            ))

            styles.add(ParagraphStyle(
                name='label_center',
                fontName=self.FONT_BOLD,
                fontSize=label_sz,
                leading=max(7, label_sz * 1.05),
                alignment=1,
                spaceAfter=2,
                spaceBefore=2
            ))

            styles.add(ParagraphStyle(
                name='response_center',
                fontName=self.FONT_REGULAR,
                fontSize=response_sz,
                leading=max(7, response_sz * 1.06),
                alignment=1,
                spaceAfter=0,
                spaceBefore=0
            ))

            styles.add(ParagraphStyle(name='td', fontName=self.FONT_REGULAR, fontSize=response_sz, leading=max(7, response_sz * 1.06), alignment=0, spaceBefore=0, spaceAfter=0))
            styles.add(ParagraphStyle(name='td_left', fontName=self.FONT_REGULAR, fontSize=response_sz, alignment=0, leading=max(7, response_sz * 1.06), spaceBefore=0, spaceAfter=0))
            styles.add(ParagraphStyle(name='td_right', fontName=self.FONT_REGULAR, fontSize=response_sz, alignment=0, leading=max(7, response_sz * 1.06), spaceBefore=0, spaceAfter=0))
            styles.add(ParagraphStyle(name='sec_title', fontName=self.FONT_BOLD, fontSize=label_sz, alignment=0, leading=max(7, label_sz * 1.05), spaceAfter=2, spaceBefore=2))

            try:
                service_mult = float(getattr(self.config, 'SERVICE_VALUE_MULTIPLIER', 1.20))
            except Exception:
                service_mult = 1.20
            svc_sz = max(response_sz, int(response_sz * service_mult))
            svc_sz = max(6.0, svc_sz)
            styles.add(ParagraphStyle(name='section_value_large', fontName=self.FONT_REGULAR, fontSize=svc_sz, leading=max(8, svc_sz * 1.06), alignment=0, spaceAfter=0, spaceBefore=0))

            return styles, pad_small, pad_med

        # constrói o story; frame_height opcional para detectar quebras e ajustar a primeira parte
        def build_story(styles, pad_small, pad_med, usable_w, frame_height=None):
            from copy import deepcopy
            from reportlab.platypus import Paragraph, Table, Spacer

            story_local = []
            # reduzir o spacer inicial ao mínimo (mantendo o bloco perto do cabeçalho)
            story_local.append(Spacer(1, 0.002 * inch))

            def shrink_paragraph_to_fit(text, base_style, max_w, max_h, min_font=6):
                txt = str(text or '')
                base_text_for_try = self.sanitize_for_paragraph(txt)
                for try_size in range(int(getattr(base_style, 'fontSize', 10)), min_font - 1, -1):
                    tmp_style = deepcopy(base_style)
                    tmp_style.fontSize = try_size
                    tmp_style.leading = max(try_size * 1.04, (tmp_style.leading if hasattr(tmp_style, 'leading') else try_size * 1.06))
                    p = Paragraph(base_text_for_try, tmp_style)
                    try:
                        w, h = p.wrap(max_w, max_h)
                    except Exception:
                        continue
                    if h <= max_h:
                        return p
                tmp_style = deepcopy(base_style)
                tmp_style.fontSize = min_font
                tmp_style.leading = min_font * 1.04
                return Paragraph(self.sanitize_for_paragraph(txt), tmp_style)

            def _get(e, *keys):
                if not isinstance(e, dict):
                    return str(e or '')
                for k in keys:
                    if k in e and e[k] not in (None, ''):
                        return e[k]
                return ''

            def split_text_into_chunks_for_row(text, style, max_w, max_row_h, min_chunk_chars=20):
                out = []
                remaining = str(text or '')
                while remaining:
                    try:
                        p = Paragraph(self.sanitize_for_paragraph(remaining), style)
                        w, h = p.wrap(max_w, max_row_h)
                    except Exception:
                        h = max_row_h + 1
                    if h <= max_row_h:
                        out.append(remaining)
                        break
                    lo = min_chunk_chars
                    hi = len(remaining)
                    best = None
                    while lo <= hi:
                        mid = (lo + hi) // 2
                        cand = remaining[:mid].rstrip()
                        try:
                            cand_p = Paragraph(self.sanitize_for_paragraph(cand), style)
                            w_c, h_c = cand_p.wrap(max_w, max_row_h)
                        except Exception:
                            h_c = max_row_h + 1
                        if h_c <= max_row_h:
                            best = mid
                            lo = mid + 1
                        else:
                            hi = mid - 1
                    if not best:
                        best = max(1, min_chunk_chars)
                    chunk = remaining[:best].rstrip()
                    if ' ' in chunk:
                        last_space = chunk.rfind(' ')
                        if last_space >= int(best * 0.4):
                            chunk = chunk[:last_space].rstrip()
                    out.append(chunk)
                    remaining = remaining[len(chunk):].lstrip()
                    if len(out) > 500:
                        out.append(remaining[:200] + '…')
                        break
                return out

            # Equipamentos (compacto)
            equipments = []
            if equipments_list and len(equipments_list) > 0:
                equipments = equipments_list
            else:
                equipments = [{
                    'equipamento': report_request.EQUIPAMENTO or '',
                    'fabricante': report_request.FABRICANTE or '',
                    'modelo': report_request.MODELO or '',
                    'numero_serie': report_request.NUMERO_SERIE or ''
                }]

            equip_data = [[
                Paragraph("EQUIPAMENTO", styles['label_center']),
                Paragraph("FABRICANTE", styles['label_center']),
                Paragraph("MODELO", styles['label_center']),
                Paragraph("Nº DE SÉRIE", styles['label_center'])
            ]]

            # para EQUIPAMENTO/FABRICANTE/MODELO/Nº DE SÉRIE mantemos proporção fixa: 4 colunas iguais
            equip_col = usable_w / 4.0
            equip_cols = [equip_col] * 4
            header_h = 0.16 * inch
            value_h = 0.14 * inch
            inner_max_h = value_h - 1

            equip_left_pad = max(1, pad_small)
            equip_right_pad = max(1, pad_small)

            for eq in equipments:
                c0 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'equipamento', 'EQUIPAMENTO') or '')),
                                            styles['response'], equip_cols[0] - 2 * equip_left_pad, inner_max_h)
                c1 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'fabricante', 'FABRICANTE') or '')),
                                            styles['response'], equip_cols[1] - 2 * equip_left_pad, inner_max_h)
                c2 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'modelo', 'MODELO') or '')),
                                            styles['response'], equip_cols[2] - 2 * equip_left_pad, inner_max_h)
                c3 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'numero_serie', 'NUMERO_SERIE') or '')),
                                            styles['response'], equip_cols[3] - 2 * equip_left_pad, inner_max_h)
                equip_data.append([c0, c1, c2, c3])

            row_heights = [header_h] + [value_h] * (len(equip_data) - 1)
            equip_table = Table(equip_data, colWidths=equip_cols, rowHeights=row_heights, repeatRows=1)
            equip_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.GRAY),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
                ('ALIGN', (0,1), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                ('INNERGRID', (0,0), (-1,-1), self.LINE_WIDTH / 2.0, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), equip_left_pad),
                ('RIGHTPADDING', (0,0), (-1,-1), equip_right_pad),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ]))
            story_local.append(equip_table)
            story_local.append(Spacer(1, 0.04 * inch))

            # Sections
            sections = [
                ("PROBLEMA RELATADO/ENCONTRADO", report_request.PROBLEMA_RELATADO),
                ("SERVIÇO REALIZADO", report_request.SERVICO_REALIZADO),
                ("RESULTADO", report_request.RESULTADO),
                ("PENDÊNCIAS", report_request.PENDENCIAS),
                ("MATERIAL FORNECIDO PELO CLIENTE", report_request.MATERIAL_CLIENTE),
                ("MATERIAL FORNECIDO PELA PRONAV", report_request.MATERIAL_PRONAV),
            ]

            max_row_h = 0.9 * inch
            content_left_pad = max(1, pad_small)
            content_right_pad = max(1, pad_small)

            for idx, (title, content) in enumerate(sections, start=1):
                title_par = Paragraph(f"{idx}. {title}", styles['label'])
                title_tbl = Table([[title_par]], colWidths=[usable_w])
                title_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), self.GRAY),
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), max(1, pad_small - 1)),
                    ('RIGHTPADDING', (0,0), (-1,-1), max(1, pad_small - 1)),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ]))

                raw_text = str(content or '').strip()
                if '\r\n\r\n' in raw_text or '\n\n' in raw_text:
                    paragraphs = [p.strip() for p in raw_text.replace('\r\n', '\n').split('\n\n') if p.strip()]
                else:
                    paragraphs = [p.strip() for p in raw_text.replace('\r\n', '\n').split('\n') if p.strip()]

                style_for_content = styles.get('section_value_large', styles['response']) if title.strip().upper().startswith("SERVIÇO REALIZADO") else styles['response']

                if not paragraphs:
                    empty_par = Paragraph('', style_for_content)
                    content_tbl = Table([[empty_par]], colWidths=[usable_w])
                    content_tbl.setStyle(TableStyle([
                        ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                        ('LEFTPADDING', (0,0), (-1,-1), content_left_pad),
                        ('RIGHTPADDING', (0,0), (-1,-1), content_right_pad),
                        ('TOPPADDING', (0,0), (-1,-1), 1),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ]))
                    story_local.append(title_tbl)
                    story_local.append(content_tbl)
                    story_local.append(Spacer(1, 0.04 * inch))
                    continue

                # build rows from paragraphs -> cada chunk é uma linha
                rows = []
                for ptext in paragraphs:
                    chunks = split_text_into_chunks_for_row(ptext, style_for_content, usable_w - 2 * content_left_pad, max_row_h)
                    for ch in chunks:
                        rows.append([Paragraph(self.sanitize_for_paragraph(ch), style_for_content)])

                content_tbl = Table(rows, colWidths=[usable_w])
                content_tbl.setStyle(TableStyle([
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), content_left_pad),
                    ('RIGHTPADDING', (0,0), (-1,-1), content_right_pad),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))

                # Se frame_height foi fornecido, tentamos dividir a tabela,
                # mas NORMALIZANDO para evitar duplicação de linha na quebra
                if frame_height is not None:
                    used_before = self.estimate_height(story_local, usable_w, frame_height)
                    remaining_space = frame_height - used_before
                    remaining_space = max(0.0, remaining_space - (0.01 * inch))

                    try:
                        w_t, h_t = title_tbl.wrap(usable_w, frame_height)
                    except Exception:
                        h_t = 0.0

                    min_needed_after_title = 0.06 * inch
                    if remaining_space < (h_t + min_needed_after_title):
                        parts = [(content_tbl, getattr(content_tbl, '_cellvalues', None) or [])]
                    else:
                        remaining_space_for_table = remaining_space - h_t
                        if remaining_space_for_table <= 0:
                            parts = [(content_tbl, getattr(content_tbl, '_cellvalues', None) or [])]
                        else:
                            # --- NOVA LÓGICA DE SPLIT (RESERVA ESPAÇO PARA HR + TÍTULO DE CONTINUAÇÃO) ---
                            try:
                                hr_height_pts = 1.0 + float(self.LINE_WIDTH) + 1.0
                            except Exception:
                                hr_height_pts = 2.0 + float(self.LINE_WIDTH)

                            cont_title_text_tmp = f"{idx}. {title} - CONTINUAÇÃO"
                            try:
                                cont_par_tmp = Paragraph(cont_title_text_tmp, styles['label'])
                                w_ct, cont_title_h = cont_par_tmp.wrap(usable_w, frame_height)
                            except Exception:
                                cont_title_h = (self.BASE_LABEL_FONT_SIZE * best_found['scale']) * 1.2

                            safety_margin = 4.0
                            reserve_space = hr_height_pts + cont_title_h + safety_margin
                            min_row_estimate = max(10.0, (self.BASE_VALUE_FONT_SIZE * best_found['scale']) * 0.8)

                            if remaining_space_for_table <= (reserve_space + min_row_estimate):
                                parts = [(content_tbl, getattr(content_tbl, '_cellvalues', None) or [])]
                            else:
                                try:
                                    raw_parts = content_tbl.split(usable_w, max(0.0, remaining_space_for_table - reserve_space))
                                except Exception:
                                    raw_parts = [content_tbl]

                                base_table_style = TableStyle([
                                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                                    ('LEFTPADDING', (0,0), (-1,-1), content_left_pad),
                                    ('RIGHTPADDING', (0,0), (-1,-1), content_right_pad),
                                    ('TOPPADDING', (0,0), (-1,-1), 1),
                                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                ])

                                parts = []
                                for rp in raw_parts:
                                    rows_chunk = getattr(rp, '_cellvalues', None) or []
                                    if not rows_chunk:
                                        rows_chunk = [[Paragraph('', style_for_content)]]

                                    if parts and rows_chunk:
                                        prev_rows = parts[-1][1] or []
                                        if prev_rows and prev_rows[-1] and rows_chunk[0]:
                                            prev_last_cell = prev_rows[-1][0]
                                            curr_first_cell = rows_chunk[0][0]

                                            def _plain_text_from_cell(cell_obj):
                                                try:
                                                    if hasattr(cell_obj, 'getPlainText'):
                                                        return cell_obj.getPlainText().strip()
                                                    return str(cell_obj).strip()
                                                except Exception:
                                                    return str(cell_obj or '').strip()

                                            try:
                                                prev_txt = _plain_text_from_cell(prev_last_cell)
                                                curr_txt = _plain_text_from_cell(curr_first_cell)
                                                n_prev = _norm_text(prev_txt)
                                                n_curr = _norm_text(curr_txt)

                                                dup = False
                                                if n_prev and n_curr:
                                                    if n_prev == n_curr:
                                                        dup = True
                                                    elif n_prev in n_curr or n_curr in n_prev:
                                                        dup = True
                                                    else:
                                                        min_overlap = int(max(6, min(len(n_prev), len(n_curr)) * 0.5))
                                                        if n_prev[:min_overlap] == n_curr[:min_overlap]:
                                                            dup = True

                                                if dup:
                                                    rows_chunk = rows_chunk[1:] or [[Paragraph('', style_for_content)]]
                                            except Exception:
                                                pass

                                    tbl = Table(rows_chunk, colWidths=[usable_w])
                                    tbl.setStyle(base_table_style)
                                    parts.append((tbl, rows_chunk))

                                normalized_parts = []
                                for j, (tbl_obj, rows_list) in enumerate(parts):
                                    rcopy = list(rows_list)
                                    if normalized_parts and rcopy:
                                        prev_rows = normalized_parts[-1][1]
                                        if prev_rows and prev_rows[-1] and rcopy and rcopy[0]:
                                            try:
                                                prev_cell = prev_rows[-1][0]
                                                curr_cell = rcopy[0][0]
                                                prev_text = prev_cell.getPlainText().strip() if hasattr(prev_cell, 'getPlainText') else str(prev_cell).strip()
                                                curr_text = curr_cell.getPlainText().strip() if hasattr(curr_cell, 'getPlainText') else str(curr_cell).strip()
                                                if _norm_text(prev_text) and _norm_text(curr_text) and _norm_text(prev_text) == _norm_text(curr_text):
                                                    rcopy = rcopy[1:] or [[Paragraph('', style_for_content)]]
                                            except Exception:
                                                pass
                                    if rcopy != rows_list:
                                        try:
                                            new_tbl = Table(rcopy, colWidths=[usable_w])
                                            new_tbl.setStyle(base_table_style)
                                            normalized_parts.append((new_tbl, rcopy))
                                        except Exception:
                                            normalized_parts.append((tbl_obj, rows_list))
                                    else:
                                        normalized_parts.append((tbl_obj, rows_list))
                                parts = normalized_parts
                else:
                    parts = [(content_tbl, getattr(content_tbl, '_cellvalues', None) or [])]

                if len(parts) <= 1:
                    story_local.append(title_tbl)
                    story_local.append(content_tbl)
                    story_local.append(Spacer(1, 0.04 * inch))
                else:
                    story_local.append(title_tbl)
                    story_local.append(parts[0][0])

                    hr = HR(width=usable_w, thickness=self.LINE_WIDTH, pad_top=1, pad_bottom=1)
                    story_local.append(hr)

                    cont_title_text = f"{idx}. {title} - CONTINUAÇÃO"
                    cont_title_par = Paragraph(cont_title_text, styles['label'])
                    cont_title_tbl = Table([[cont_title_par]], colWidths=[usable_w])
                    cont_title_tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,-1), self.GRAY),
                        ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                        ('LEFTPADDING', (0,0), (-1,-1), max(1, pad_small - 1)),
                        ('RIGHTPADDING', (0,0), (-1,-1), max(1, pad_small - 1)),
                        ('TOPPADDING', (0,0), (-1,-1), 1),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ]))
                    story_local.append(cont_title_tbl)

                    for p_part in parts[1:]:
                        story_local.append(p_part[0])
                    story_local.append(Spacer(1, 0.04 * inch))

            # Activities table (mantive as regras anteriores)
            if atividades_list:
                proportions = [0.09, 0.12, 0.24, 0.45, 0.05, 0.04, 0.04]
                try:
                    delta_prop = min(0.12, (square_side / usable_w) * 1.0)
                except Exception:
                    delta_prop = 0.0

                idx_desc = 3
                idx_tec1 = 5
                idx_tec2 = 6

                proportions[idx_desc] = max(0.08, proportions[idx_desc] - delta_prop)
                proportions[idx_tec1] = proportions[idx_tec1] + (delta_prop / 2.0)
                proportions[idx_tec2] = proportions[idx_tec2] + (delta_prop / 2.0)

                total_prop = sum(proportions)
                if total_prop <= 0:
                    proportions = [0.12, 0.12, 0.14, 0.30, 0.06, 0.13, 0.13]
                else:
                    proportions = [p / total_prop for p in proportions]

                col_widths = [p * usable_w for p in proportions]

                delta_desc_pts = 18.0
                delta_tec_pts = 8.0
                delta_desc = (delta_desc_pts / 72.0) * inch
                delta_tec = (delta_tec_pts / 72.0) * inch

                col_widths[idx_desc] = max(0.08 * usable_w, col_widths[idx_desc] - delta_desc)
                col_widths[idx_tec1] = col_widths[idx_tec1] + delta_tec
                col_widths[idx_tec2] = col_widths[idx_tec2] + delta_tec

                header_cells = [
                    Paragraph("DATA", styles['label_center']),
                    Paragraph("HORA", styles['label_center']),
                    Paragraph("TIPO", styles['label_center']),
                    Paragraph("DESCRIÇÃO", styles['label_center']),
                    Paragraph("KM", styles['label_center']),
                    Paragraph("TÉCNICOS", styles['label_center']),
                    Paragraph("", styles['label_center'])
                ]

                data = [header_cells]

                for at in atividades_list:
                    data_br = format_date_br(at.get('DATA')) if at.get('DATA') else ''
                    hora_comb = at.get('HORA') or ''
                    tipo = at.get('TIPO') or ''
                        # --- leitura e normalização da descrição ---
                    descricao_raw = (at.get('DESCRICAO') or '').strip()
                    # considera como vazia placeholders comuns
                    if descricao_raw.upper() in ('', 'X', '-', '—'):
                        descricao_raw = ''

                    km_final = at.get('KM') or ''

                    # --- normaliza chaves em lowercase para achar origem/destino ---
                    at_lc = {}
                    if isinstance(at, dict):
                        for k, v in at.items():
                            if v is None:
                                continue
                            at_lc[k.lower()] = v

                    origem = (at_lc.get('origem') or
                            at_lc.get('local_origem') or
                            at_lc.get('origem_local'))
                    destino = (at_lc.get('destino') or
                            at_lc.get('local_destino') or
                            at_lc.get('destino_local'))

                    # --- monta a string final sem adicionar travessão desnecessário ---
                    if origem and destino:
                        od = f"{ensure_upper_safe(str(origem))} x {ensure_upper_safe(str(destino))}"
                        if descricao_raw:
                            descricao_final = f"{ensure_upper_safe(descricao_raw)} — {od}"
                        else:
                            # se não há descrição válida, use apenas origem x destino
                            descricao_final = od
                    else:
                        descricao_final = ensure_upper_safe(descricao_raw)

                    # tratamento específico para tipo "mão-de-obra-técnica" (mantido)
                    if str(tipo).lower() == "mão-de-obra-técnica":
                        descricao_final = "Mão-de-Obra-Técnica"
                        km_final = ""


                    max_h_cell = 0.7 * inch
                    c0 = shrink_paragraph_to_fit(str(data_br or ''), styles['response'], col_widths[0] - 6, max_h_cell)
                    c1 = shrink_paragraph_to_fit(hora_comb, styles['response'], col_widths[1] - 6, max_h_cell)
                    c2 = shrink_paragraph_to_fit(tipo, styles['response'], col_widths[2] - 6, max_h_cell)
                    c3 = shrink_paragraph_to_fit(descricao_final, styles['response'], col_widths[3] - 6, max_h_cell)
                    c4 = shrink_paragraph_to_fit(km_final, styles['response'], col_widths[4] - 6, max_h_cell)
                    c5 = shrink_paragraph_to_fit(str(at.get('TECNICO1') or ''), styles['response'], col_widths[5] - 6, max_h_cell)
                    c6 = shrink_paragraph_to_fit(str(at.get('TECNICO2') or ''), styles['response'], col_widths[6] - 6, max_h_cell)

                    data.append([c0, c1, c2, c3, c4, c5, c6])

                activities_table = Table(data, colWidths=col_widths, repeatRows=1)
                activities_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), self.GRAY),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('ALIGN', (0,1), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('GRID', (0,0), (-1,-1), self.LINE_WIDTH / 2.0, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), pad_small),
                    ('RIGHTPADDING', (0,0), (-1,-1), pad_small),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                    ('SPAN', (5,0), (6,0)),
                ]))
                story_local.append(activities_table)

            return story_local

        def split_text_into_chunks_for_row(text, style, max_w, max_row_h, min_chunk_chars=20):
            out = []
            remaining = str(text or '')
            from reportlab.platypus import Paragraph
            while remaining:
                try:
                    p = Paragraph(self.sanitize_for_paragraph(remaining), style)
                    w, h = p.wrap(max_w, max_row_h)
                except Exception:
                    h = max_row_h + 1
                if h <= max_row_h:
                    out.append(remaining)
                    break
                lo = min_chunk_chars
                hi = len(remaining)
                best = None
                while lo <= hi:
                    mid = (lo + hi) // 2
                    cand = remaining[:mid].rstrip()
                    try:
                        cand_p = Paragraph(self.sanitize_for_paragraph(cand), style)
                        w_c, h_c = cand_p.wrap(max_w, max_row_h)
                    except Exception:
                        h_c = max_row_h + 1
                    if h_c <= max_row_h:
                        best = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1
                if not best:
                    best = max(1, min_chunk_chars)
                chunk = remaining[:best].rstrip()
                if ' ' in chunk:
                    last_space = chunk.rfind(' ')
                    if last_space >= int(best * 0.4):
                        chunk = chunk[:last_space].rstrip()
                out.append(chunk)
                remaining = remaining[len(chunk):].lstrip()
                if len(out) > 500:
                    out.append(remaining[:200] + '…')
                    break
            return out

        # Find best scale/margins (busca simples)
        best_found = {
            'fit': False,
            'scale': 1.0,
            'top_margin': preserved_top_margin_base,
            'bottom_margin': preserved_bottom_margin_base,
            'usable_w': PAGE_W - 2 * MARG,
            'frame_height': 0.0,
            'story': None,
            'styles': None,
            'pad_small': None,
            'pad_med': None
        }

        original_usable_w = PAGE_W - 2 * MARG

        for m_factor in margin_reduction_factors:
            preserved_top_margin = preserved_top_margin_base * m_factor
            preserved_bottom_margin = preserved_bottom_margin_base * m_factor

            usable_w = original_usable_w
            frame_top = PAGE_H - preserved_top_margin - header_height_base
            frame_bottom = preserved_bottom_margin + footer_total_height_base
            frame_height = frame_top - frame_bottom
            if frame_height <= 0:
                continue

            styles_test, ps, pm = make_styles(scale=MAX_SCALE)
            story_test = build_story(styles_test, ps, pm, usable_w)
            req = self.estimate_height(story_test, usable_w, frame_height)
            if req <= frame_height:
                best_found.update({
                    'fit': True,
                    'scale': MAX_SCALE,
                    'top_margin': preserved_top_margin,
                    'bottom_margin': preserved_bottom_margin,
                    'usable_w': usable_w,
                    'frame_height': frame_height,
                    'story': story_test,
                    'styles': styles_test,
                    'pad_small': ps,
                    'pad_med': pm
                })
                break
            else:
                found_story = found_styles = found_ps = found_pm = None
                lo = MIN_SCALE
                hi = MAX_SCALE
                found_scale = None
                for _ in range(12):
                    mid = (lo + hi) / 2.0
                    styles_mid, ps_mid, pm_mid = make_styles(scale=mid)
                    story_mid = build_story(styles_mid, ps_mid, pm_mid, usable_w)
                    req_mid = self.estimate_height(story_mid, usable_w, frame_height)
                    if req_mid <= frame_height:
                        found_scale = mid
                        found_story = story_mid
                        found_styles = styles_mid
                        found_ps = ps_mid
                        found_pm = pm_mid
                        lo = mid
                    else:
                        hi = mid
                    if (hi - lo) < 0.005:
                        break
                if found_scale:
                    best_found.update({
                        'fit': True,
                        'scale': found_scale,
                        'top_margin': preserved_top_margin,
                        'bottom_margin': preserved_bottom_margin,
                        'usable_w': usable_w,
                        'frame_height': frame_height,
                        'story': found_story,
                        'styles': found_styles,
                        'pad_small': found_ps,
                        'pad_med': found_pm
                    })
                    break

        if not best_found['fit']:
            last_m_factor = margin_reduction_factors[-1]
            preserved_top_margin = preserved_top_margin_base * last_m_factor
            preserved_bottom_margin = preserved_bottom_margin_base * last_m_factor
            usable_w = original_usable_w
            frame_top = PAGE_H - preserved_top_margin - header_height_base
            frame_bottom = preserved_bottom_margin + footer_total_height_base
            frame_height = max(1.0 * inch, frame_top - frame_bottom)
            styles_min, ps_min, pm_min = make_styles(scale=MIN_SCALE)
            story_min = build_story(styles_min, ps_min, pm_min, usable_w, frame_height=frame_height)
            best_found.update({
                'fit': False,
                'scale': MIN_SCALE,
                'top_margin': preserved_top_margin,
                'bottom_margin': preserved_bottom_margin,
                'usable_w': usable_w,
                'frame_height': frame_height,
                'story': story_min,
                'styles': styles_min,
                'pad_small': ps_min,
                'pad_med': pm_min
            })

        # escolha final
        chosen_top_margin = best_found['top_margin']
        chosen_bottom_margin = best_found['bottom_margin']
        chosen_styles = best_found['styles']
        chosen_pad_small = best_found['pad_small']
        chosen_pad_med = best_found['pad_med']
        usable_w = best_found['usable_w']
        frame_top = PAGE_H - chosen_top_margin - header_height_base
        frame_bottom = chosen_bottom_margin + footer_total_height_base
        frame_height = max(1.0 * inch, frame_top - frame_bottom)

        # final rebuild passando frame_height para detectar quebras corretamente
        story = build_story(chosen_styles, chosen_pad_small, chosen_pad_med, usable_w, frame_height=frame_height)

        # NÃO centralizamos verticalmente: sempre começamos logo abaixo do cabeçalho
        vertical_offset = 0.0

        # Document e frame
        doc = BaseDocTemplate(pdf_buffer, pagesize=PAGE_SIZE,
                             leftMargin=MARG, rightMargin=MARG,
                             topMargin=chosen_top_margin, bottomMargin=chosen_bottom_margin)

        topPadding_val = max(4, int(4 + vertical_offset))  # padding pequeno e determinístico
        content_frame = Frame(MARG, frame_bottom, usable_w, frame_height,
                              leftPadding=4, rightPadding=4, topPadding=topPadding_val, bottomPadding=4, id='content_frame')

        # logo lookup (automatic)
        logo_bytes = find_logo_bytes(self.config)

        def draw_header(canvas, doc_local):
            canvas.saveState()
            canvas.setLineJoin(1)
            canvas.setLineWidth(self.LINE_WIDTH)
            canvas.setStrokeColor(colors.black)

            left_x = MARG
            right_x = MARG + usable_w
            top_y = PAGE_H - doc_local.topMargin
            bottom_y = top_y - header_height_base

            logo_x0 = left_x
            logo_x1 = left_x + square_side

            sep_x1 = logo_x1
            sep_x2 = right_x

            eps = 0.4
            canvas.line(left_x - eps, top_y + eps, right_x + eps, top_y + eps)
            canvas.line(left_x - eps, bottom_y - eps, right_x + eps, bottom_y - eps)
            canvas.line(left_x - eps, bottom_y - eps, left_x - eps, top_y + eps)
            canvas.line(right_x + eps, bottom_y - eps, right_x + eps, top_y + eps)

            try:
                canvas.rect(logo_x0, bottom_y, square_side, header_height_base, stroke=1, fill=0)
            except Exception:
                pass

            y_top = top_y
            y_row0 = y_top - header_row0
            y_row1 = y_row0 - header_row
            y_row2 = y_row1 - header_row
            y_row3 = y_row2 - header_row

            canvas.line(logo_x1, y_row0, right_x, y_row0)
            canvas.line(logo_x1, y_row1, right_x, y_row1)
            canvas.line(logo_x1, y_row2, right_x, y_row2)
            canvas.line(logo_x1, y_row3, right_x, y_row3)

            left_increase = 1.30
            inner_label_w = 0.8 * inch * left_increase
            inner_val_w_left = 2.2 * inch * left_increase
            inner_label_w2 = 0.5 * inch
            total_center = sep_x2 - sep_x1
            inner_val_w_right = total_center - (inner_label_w + inner_val_w_left + inner_label_w2)

            min_right = 0.75 * inch
            if inner_val_w_right < min_right:
                deficit = min_right - inner_val_w_right
                reduce_each = deficit / 2.0
                inner_val_w_left = max(0.5 * inch, inner_val_w_left - reduce_each)
                inner_label_w = max(0.4 * inch, inner_label_w - reduce_each)
                inner_val_w_right = total_center - (inner_label_w + inner_val_w_left + inner_label_w2)
                inner_val_w_right = max(inner_val_w_right, min_right)

            col0_w, col1_w, col2_w, col3_w = inner_label_w, inner_val_w_left, inner_label_w2, inner_val_w_right
            col_x0 = sep_x1
            col_x1 = col_x0 + col0_w
            col_x2 = col_x1 + col1_w
            col_x3 = col_x2 + col2_w
            col_x4 = col_x3 + col3_w

            offset_left_line = 2.0
            offset_right_line = 4.0
            canvas.line(col_x1, bottom_y, col_x1, top_y)
            canvas.line(col_x2 + offset_left_line, bottom_y, col_x2 + offset_left_line, top_y)
            canvas.line(col_x3 + offset_right_line, bottom_y, col_x3 + offset_right_line, top_y)

            canvas.line(left_x, bottom_y, right_x, bottom_y)

            # contact line
            try:
                contact_line = "PRONAV COMÉRCIO E SERVIÇOS LTDA.   |   CNPJ: 56.286.063/0001-46   |   Tel.: (22) 2141-2458   |   Cel.: (22) 99221-1893   |   service@pronav.com.br   |   www.pronav.com.br"
                contact_font_size = max(7, int(7 * best_found['scale']))
                contact_y = top_y + (0.05 * inch)
                canvas.setFont(self.FONT_REGULAR, contact_font_size)
                canvas.setFillColor(colors.HexColor('#333333'))
                canvas.drawCentredString(PAGE_W / 2.0, contact_y, contact_line)
                canvas.setFillColor(colors.black)
            except Exception:
                pass

            # gray title background
            try:
                canvas.setFillColor(self.GRAY)
                canvas.rect(sep_x1, y_row0, (sep_x2 - sep_x1), header_row0, stroke=0, fill=1)
                canvas.setFillColor(colors.black)
            except Exception:
                pass

            title_font_size = max(9, int(self.BASE_TITLE_FONT_SIZE * best_found['scale']) + 1)
            canvas.setFont(self.FONT_BOLD, title_font_size)
            canvas.drawCentredString((sep_x1 + sep_x2) / 2.0, y_row0 + (header_row0 / 2.0) - 3, "RELATÓRIO DE SERVIÇO")

            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(self.LINE_WIDTH)
            canvas.line(sep_x1, y_row0, right_x, y_row0)

            # logo image (from bytes if available, otherwise fallback text)
            logo_drawn = False
            try:
                if logo_bytes:
                    try:
                        img_reader = ImageReader(io.BytesIO(logo_bytes))
                        iw, ih = img_reader.getSize()
                        pad = 6.0
                        max_w = max(1.0, square_side - 2 * pad)
                        max_h = max(1.0, header_height_base - 2 * pad)
                        ratio_w = max_w / iw if iw > 0 else 1.0
                        ratio_h = max_h / ih if ih > 0 else 1.0
                        ratio = min(1.0, ratio_w, ratio_h)
                        logo_w = iw * ratio
                        logo_h = ih * ratio
                        if logo_w > max_w:
                            factor = max_w / logo_w
                            logo_w *= factor
                            logo_h *= factor
                        logo_x = logo_x0 + (square_side - logo_w) / 2.0
                        logo_y = bottom_y + (header_height_base - logo_h) / 2.0
                        canvas.drawImage(img_reader, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
                        logo_drawn = True
                    except Exception:
                        logo_drawn = False
                else:
                    lp = getattr(self.config, 'LOGO_PATH', None)
                    if lp and isinstance(lp, str):
                        try:
                            pth = Path(lp)
                            if not pth.is_absolute():
                                pth = Path(__file__).resolve().parent / pth
                            if pth.exists():
                                img_reader = ImageReader(str(pth))
                                iw, ih = img_reader.getSize()
                                pad = 6.0
                                max_w = max(1.0, square_side - 2 * pad)
                                max_h = max(1.0, header_height_base - 2 * pad)
                                ratio_w = max_w / iw if iw > 0 else 1.0
                                ratio_h = max_h / ih if ih > 0 else 1.0
                                ratio = min(1.0, ratio_w, ratio_h)
                                logo_w = iw * ratio
                                logo_h = ih * ratio
                                if logo_w > max_w:
                                    factor = max_w / logo_w
                                    logo_w *= factor
                                    logo_h *= factor
                                logo_x = logo_x0 + (square_side - logo_w) / 2.0
                                logo_y = bottom_y + (header_height_base - logo_h) / 2.0
                                canvas.drawImage(img_reader, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
                                logo_drawn = True
                        except Exception:
                            logo_drawn = False
            except Exception:
                logo_drawn = False

            if not logo_drawn:
                try:
                    fsize = max(12, int(10 * best_found['scale']))
                    canvas.setFont(self.FONT_BOLD, fsize)
                    canvas.setFillColor(colors.HexColor('#333333'))
                    canvas.drawCentredString(logo_x0 + square_side/2.0, bottom_y + header_height_base/2.0 - (fsize/4.0), "PRONAV")
                    canvas.setFillColor(colors.black)
                except Exception:
                    pass

            # labels & values (font sizes made equal for labels and values)
            labels_left = ["NAVIO:", "CONTATO:", "LOCAL:"]
            values_left = [
                ensure_upper_safe(getattr(report_request, 'NAVIO', '') or ''),
                ensure_upper_safe(getattr(report_request, 'CONTATO', '') or ''),
                ' - '.join(filter(None, [
                    ensure_upper_safe(getattr(report_request, 'LOCAL', '') or ''),
                    ensure_upper_safe(getattr(report_request, 'CIDADE', '') or ''),
                    ensure_upper_safe(getattr(report_request, 'ESTADO', '') or '')
                ]))
            ]
            labels_right = ["CLIENTE", "OBRA:", "OS:"]
            values_right = [
                ensure_upper_safe(getattr(report_request, 'CLIENTE', '') or ''),
                ensure_upper_safe(getattr(report_request, 'OBRA', '') or ''),
                ensure_upper_safe(getattr(report_request, 'OS', '') or '')
            ]

            rows_y = [y_row0, y_row1, y_row2, y_row3]

            left_label_padding = 4
            left_value_padding = 4
            right_label_padding = 4
            right_value_padding = 6

            max_width = col_x4 - col_x3 - right_value_padding

            # compute unified font sizes
            label_font = max(7, int(self.BASE_LABEL_FONT_SIZE * best_found['scale']))
            value_font = label_font  # mantém MESMO tamanho entre labels e values

            for i in range(3):
                top = rows_y[i]
                bottom = rows_y[i + 1]
                center_y = (top + bottom) / 2.0 - 3

                canvas.setFont(self.FONT_BOLD, label_font)
                canvas.setFillColor(colors.black)
                canvas.drawString(col_x0 + left_label_padding, center_y, labels_left[i])

                canvas.setFont(self.FONT_REGULAR, value_font)
                canvas.drawString(col_x1 + left_value_padding, center_y, values_left[i])

                canvas.setFont(self.FONT_BOLD, label_font)
                canvas.drawString(col_x2 + right_label_padding, center_y, labels_right[i])
                canvas.setFont(self.FONT_REGULAR, value_font)

                value_text = values_right[i] or ''
                if canvas.stringWidth(value_text, self.FONT_REGULAR, value_font) > max_width:
                    while value_text and canvas.stringWidth(value_text + '…', self.FONT_REGULAR, value_font) > max_width:
                        value_text = value_text[:-1]
                    value_text = (value_text + '…') if value_text else ''

                value_x = col_x3 + right_value_padding
                canvas.drawString(value_x, center_y, value_text)

            canvas.restoreState()

        def draw_signatures_and_footer(canvas, doc_local):
            canvas.saveState()
            canvas.setLineWidth(self.LINE_WIDTH)
            canvas.setStrokeColor(colors.black)

            left = MARG
            right = MARG + usable_w
            mid = left + usable_w / 2.0

            bottom_margin = doc_local.bottomMargin
            sig_header_h_local = sig_header_h_base
            sig_area_h_local = sig_area_h_base
            footer_h_local = footer_h_base
            footer_y = bottom_margin

            canvas.setFillColor(self.GRAY)
            canvas.rect(left, footer_y, usable_w, footer_h_local, stroke=0, fill=1)
            canvas.setFillColor(colors.black)
            canvas.setFont(self.FONT_BOLD, max(7, int(self.BASE_VALUE_FONT_SIZE * best_found['scale']) + 1))
            canvas.drawCentredString(left + usable_w / 2.0, footer_y + footer_h_local / 2.0 - 3, "O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE")

            sig_bottom = footer_y + footer_h_local
            sig_total_h_local = sig_area_h_local + sig_header_h_local
            canvas.setFillColor(self.GRAY)
            canvas.rect(left, sig_bottom + sig_area_h_local, usable_w / 2.0, sig_header_h_local, stroke=0, fill=1)
            canvas.rect(mid, sig_bottom + sig_area_h_local, usable_w / 2.0, sig_header_h_local, stroke=0, fill=1)
            canvas.setFillColor(colors.black)
            canvas.setFont(self.FONT_BOLD, max(6, int(self.BASE_LABEL_FONT_SIZE * best_found['scale'])))
            canvas.drawCentredString(left + (usable_w / 4.0), sig_bottom + sig_area_h_local + sig_header_h_local / 2.0 - 2, "ASSINATURA DO COMANDANTE")
            canvas.drawCentredString(mid + (usable_w / 4.0), sig_bottom + sig_area_h_local + sig_header_h_local / 2.0 - 2, "ASSINATURA DO TÉCNICO")

            canvas.setLineWidth(self.LINE_WIDTH)
            canvas.rect(left, sig_bottom, usable_w / 2.0, sig_total_h_local, stroke=1, fill=0)
            canvas.rect(mid, sig_bottom, usable_w / 2.0, sig_total_h_local, stroke=1, fill=0)
            eps = 0.4
            canvas.line(mid, sig_bottom - eps, mid, sig_bottom + sig_total_h_local + eps)

            canvas.restoreState()

        def on_page_template(canvas, doc_local):
            draw_header(canvas, doc_local)
            draw_signatures_and_footer(canvas, doc_local)
            try:
                canvas.saveState()
                canvas.setFont(self.FONT_REGULAR, 7)
                canvas.setFillColor(colors.HexColor('#666666'))
                y_page = doc_local.bottomMargin - (0.04 * inch)
                if y_page < 6:
                    y_page = 6
                canvas.drawCentredString(MARG + usable_w / 2.0, y_page, f"Página {canvas.getPageNumber()}")
                canvas.restoreState()
            except Exception:
                pass

        template = PageTemplate(id='normal', frames=[content_frame], onPage=on_page_template)
        doc.addPageTemplates([template])

        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer, saved_report_id

    def get_filename(self, report_request, equipments_list):
        equip_name_for_file = ''
        try:
            if equipments_list and len(equipments_list) > 0:
                e0 = equipments_list[0]
                if isinstance(e0, dict):
                    equip_name_for_file = e0.get('equipamento') or e0.get('Equipamento') or ''
                else:
                    equip_name_for_file = str(e0)
            if not equip_name_for_file:
                equip_name_for_file = report_request.EQUIPAMENTO or ''
            equip_name_for_file = str(equip_name_for_file).strip().replace(' ', '_').replace('/', '-')
        except Exception:
            equip_name_for_file = ''

        safe_ship = (report_request.NAVIO or 'Geral').replace(' ', '_')
        date_str = datetime.utcnow().strftime('%Y%m%d')
        filename = f"RS_{date_str}_{safe_ship}"
        if equip_name_for_file:
            filename = f"{filename}_{equip_name_for_file}"
        filename = f"{filename}.pdf"

        return filename
