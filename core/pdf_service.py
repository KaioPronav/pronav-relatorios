import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from core.normalizers import ensure_upper_safe
from core.utils import format_date_br


class PDFService:
    def __init__(self, config):
        self.config = config
        self.setup_fonts()

        # Layout constants
        self.LINE_WIDTH = 0.6
        self.GRAY = colors.HexColor('#D9D9D9')
        self.SMALL_PAD = 4
        self.MED_PAD = 4
        self.BASE_TITLE_FONT_SIZE = 9.0
        self.BASE_LABEL_FONT_SIZE = 8.0
        self.BASE_VALUE_FONT_SIZE = 7.8

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

    def generate_pdf(self, report_request, atividades_list, equipments_list, saved_report_id):
        # --- PDF parameters (base values) ---
        pdf_buffer = io.BytesIO()
        PAGE_SIZE = letter
        PAGE_W, PAGE_H = PAGE_SIZE

        # margins - we'll allow reduction if necessary
        MARG = 0.35 * inch  # left/right fixed
        preserved_top_margin_base = 0.25 * inch
        preserved_bottom_margin_base = 0.12 * inch

        square_side = 1.18 * inch
        header_row0 = 0.22 * inch
        header_row = 0.26 * inch
        header_height_base = header_row0 + header_row * 3

        sig_header_h_base = 0.24 * inch
        sig_area_h_base = 0.6 * inch
        footer_h_base = 0.28 * inch
        footer_total_height_base = footer_h_base + sig_header_h_base + sig_area_h_base

        # scaling bounds (configurable via Config.MIN_SCALE)
        MIN_SCALE = getattr(self.config, 'MIN_SCALE', 0.40)
        MAX_SCALE = 1.0
        margin_reduction_factors = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]

        def make_styles(scale=1.0):
            """
            Cria estilos uniformes:
            - label (calculado a partir de BASE_LABEL_FONT_SIZE) e independente de RESPONSE_VALUE_MULTIPLIER
            - response (calculado a partir de BASE_VALUE_FONT_SIZE) afetado por RESPONSE_VALUE_MULTIPLIER
            - label_center / response_center usados onde necessário
            Ajustes via config:
            - RESPONSE_VALUE_MULTIPLIER
            - LABEL_VALUE_MULTIPLIER
            - SERVICE_VALUE_MULTIPLIER
            """
            base_title = max(6.0, self.BASE_TITLE_FONT_SIZE * scale)
            base_label = max(6.0, self.BASE_LABEL_FONT_SIZE * scale)
            base_value = max(6.0, self.BASE_VALUE_FONT_SIZE * scale)

            # multipliers configuráveis via config
            try:
                resp_mult = float(getattr(self.config, 'RESPONSE_VALUE_MULTIPLIER', 1.0))
            except Exception:
                resp_mult = 1.0
            try:
                label_mult = float(getattr(self.config, 'LABEL_VALUE_MULTIPLIER', 1.08))
            except Exception:
                label_mult = 1.08

            # response size = BASE_VALUE * RESPONSE_VALUE_MULTIPLIER
            response_sz = max(6.0, float(base_value) * resp_mult)

            # label size = BASE_LABEL * LABEL_VALUE_MULTIPLIER (independente de response_sz)
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
                leading=max(8, title_sz*1.15)
            ))

            # LABEL (LEFT) - seções / cabeçalhos quando for label
            styles.add(ParagraphStyle(
                name='label',
                fontName=self.FONT_BOLD,
                fontSize=label_sz,
                leading=max(8, label_sz*1.15),
                alignment=0,  # LEFT
                spaceAfter=2,
                spaceBefore=2
            ))

            # RESPONSE (LEFT) - seções / valores
            styles.add(ParagraphStyle(
                name='response',
                fontName=self.FONT_REGULAR,
                fontSize=response_sz,
                leading=max(9, response_sz*1.15),
                alignment=0,  # LEFT
                spaceAfter=2,
                spaceBefore=2
            ))

            # Centered variants for table HEADERS (labels centered)
            styles.add(ParagraphStyle(
                name='label_center',
                fontName=self.FONT_BOLD,
                fontSize=label_sz,
                leading=max(8, label_sz*1.15),
                alignment=1,  # CENTER
                spaceAfter=2,
                spaceBefore=2
            ))
            styles.add(ParagraphStyle(
                name='response_center',
                fontName=self.FONT_REGULAR,
                fontSize=response_sz,
                leading=max(9, response_sz*1.15),
                alignment=1,  # CENTER
                spaceAfter=2,
                spaceBefore=2
            ))

            # aliases (compatibilidade)
            styles.add(ParagraphStyle(name='td', fontName=self.FONT_REGULAR, fontSize=response_sz, leading=max(9, response_sz*1.15), alignment=0))
            styles.add(ParagraphStyle(name='td_left', fontName=self.FONT_REGULAR, fontSize=response_sz, alignment=0, leading=max(9, response_sz*1.15)))
            styles.add(ParagraphStyle(name='td_right', fontName=self.FONT_REGULAR, fontSize=response_sz, alignment=0, leading=max(9, response_sz*1.15)))
            styles.add(ParagraphStyle(name='sec_title', fontName=self.FONT_BOLD, fontSize=label_sz, alignment=0, leading=max(8, label_sz*1.15)))

            # service large (opcional)
            try:
                service_mult = float(getattr(self.config, 'SERVICE_VALUE_MULTIPLIER', 1.25))
            except Exception:
                service_mult = 1.25
            svc_sz = max(response_sz, int(response_sz * service_mult))
            svc_sz = max(6.0, svc_sz)
            styles.add(ParagraphStyle(name='section_value_large', fontName=self.FONT_REGULAR, fontSize=svc_sz, leading=max(9, svc_sz*1.15), alignment=0))

            return styles, pad_small, pad_med


        def build_story(styles, pad_small, pad_med, usable_w):
            story_local = []
            story_local.append(Spacer(1, 0.01 * inch))

            # Equipamento (TABLE)
            first_eq = None
            if equipments_list and len(equipments_list) > 0:
                first_eq = equipments_list[0]
            if not first_eq:
                first_eq = {
                    'equipamento': report_request.EQUIPAMENTO or '',
                    'fabricante': report_request.FABRICANTE or '',
                    'modelo': report_request.MODELO or '',
                    'numero_serie': report_request.NUMERO_SERIE or ''
                }

            equip_col = usable_w / 4.0
            equip_cols = [equip_col] * 4
            equip_data = [
                [Paragraph("EQUIPAMENTO", styles['label_center']),
                 Paragraph("FABRICANTE", styles['label_center']),
                 Paragraph("MODELO", styles['label_center']),
                 Paragraph("Nº DE SÉRIE", styles['label_center'])],
                [Paragraph(ensure_upper_safe(first_eq.get('equipamento') or ''), styles['response']),
                 Paragraph(ensure_upper_safe(first_eq.get('fabricante') or ''), styles['response']),
                 Paragraph(ensure_upper_safe(first_eq.get('modelo') or ''), styles['response']),
                 Paragraph(ensure_upper_safe(first_eq.get('numero_serie') or ''), styles['response'])],
            ]
            equip_table = Table(equip_data, colWidths=equip_cols, rowHeights=[0.28*inch, 0.2*inch])
            equip_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.GRAY),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),   # header center
                ('ALIGN', (0,1), (-1,1), 'LEFT'),     # values left
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), # vertical center all cells
                ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                ('INNERGRID', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                ('LEFTPADDING', (0,0), (-1,0), pad_small),
                ('RIGHTPADDING', (0,0), (-1,0), pad_small),
                ('TOPPADDING', (0,0), (-1,0), 0.5),
                ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
                ('LEFTPADDING', (0,1), (-1,1), pad_med),
                ('RIGHTPADDING', (0,1), (-1,1), pad_med),
                ('TOPPADDING', (0,1), (-1,1), 0.5),
                ('BOTTOMPADDING', (0,1), (-1,1), 0.5),
            ]))
            story_local.append(KeepTogether([equip_table]))
            story_local.append(Spacer(1, 0.12 * inch))

            # Sections (LEFT aligned)
            sections = [
                ("PROBLEMA RELATADO/ENCONTRADO", report_request.PROBLEMA_RELATADO),
                ("SERVIÇO REALIZADO", report_request.SERVICO_REALIZADO),
                ("RESULTADO", report_request.RESULTADO),
                ("PENDÊNCIAS", report_request.PENDENCIAS),
                ("MATERIAL FORNECIDO PELO CLIENTE", report_request.MATERIAL_CLIENTE),
                ("MATERIAL FORNECIDO PELA PRONAV", report_request.MATERIAL_PRONAV),
            ]
            for idx, (title, content) in enumerate(sections, start=1):
                title_tbl = Table([[Paragraph(f"{idx}. {title}", styles['label'])]], colWidths=[usable_w])
                title_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), self.GRAY),
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), pad_small),
                    ('RIGHTPADDING', (0,0), (-1,-1), pad_small),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ]))

                safe_content = (str(content or '')).replace('\r\n', '\n').replace('\r', '\n')
                safe_content = safe_content.replace('\n', '<br/>')

                # SERVIÇO pode usar style maior (left)
                if title.strip().upper().startswith("SERVIÇO REALIZADO"):
                    style_for_content = styles.get('section_value_large', styles['response'])
                else:
                    style_for_content = styles['response']

                content_par = Paragraph(safe_content, style_for_content)

                content_tbl = Table([[content_par]], colWidths=[usable_w])
                content_tbl.setStyle(TableStyle([
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), pad_med),
                    ('RIGHTPADDING', (0,0), (-1,-1), pad_med),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ]))

                story_local.append(KeepTogether([title_tbl, content_tbl]))
                story_local.append(Spacer(1, 0.12 * inch))

            # Activities table — cabeçalhos CENTRALIZADOS; respostas LEFT + VALIGN=MIDDLE
            if atividades_list:
                proportions = [0.09, 0.12, 0.24, 0.45, 0.05, 0.04, 0.04]
                try:
                    delta_prop = min(0.16, (square_side / usable_w) * 1.0)
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

                delta_desc_pts = 20.0
                delta_tec_pts = 10.0
                delta_desc = (delta_desc_pts / 72.0) * inch
                delta_tec = (delta_tec_pts / 72.0) * inch

                idx_desc = 3
                idx_tec1 = 5
                idx_tec2 = 6

                col_widths[idx_desc] = max(0.08 * usable_w, col_widths[idx_desc] - delta_desc)
                col_widths[idx_tec1] = col_widths[idx_tec1] + delta_tec
                col_widths[idx_tec2] = col_widths[idx_tec2] + delta_tec

                total = sum(col_widths)
                diff = total - usable_w
                if abs(diff) > 0.1:
                    preferred = 2
                    min_allowed = 0.06 * usable_w
                    new_val = col_widths[preferred] - diff
                    if new_val < min_allowed:
                        remaining = diff - (col_widths[preferred] - min_allowed)
                        col_widths[preferred] = min_allowed
                        col_widths[0] = max(0.06 * usable_w, col_widths[0] - remaining)
                    else:
                        col_widths[preferred] = new_val

                # cabeçalhos: manter 7 colunas (última vazia) e aplicar SPAN entre (5,0) e (6,0) para "TÉCNICOS"
                header_cells = [
                    Paragraph("DATA", styles['label_center']),
                    Paragraph("HORA", styles['label_center']),
                    Paragraph("TIPO", styles['label_center']),
                    Paragraph("DESCRIÇÃO", styles['label_center']),
                    Paragraph("KM", styles['label_center']),
                    Paragraph("TÉCNICOS", styles['label_center']),
                    Paragraph("", styles['label_center'])  # célula vazia para o span
                ]
                data = [header_cells]

                for at in atividades_list:
                    hi = (at.get('HORA_INICIO') or '') or ''
                    hf = (at.get('HORA_FIM') or '') or ''
                    legacy = (at.get('HORA') or '') or ''
                    if hi and hf:
                        hora_comb = f"{str(hi)} às {str(hf)}"
                    elif hi:
                        hora_comb = str(hi)
                    elif legacy:
                        hora_comb = str(legacy)
                    else:
                        hora_comb = ''

                    data_br = format_date_br(at.get('DATA') or '')

                    tipo = str(at.get('TIPO') or '').strip()
                    origem = (at.get('ORIGEM') or '')
                    destino = (at.get('DESTINO') or '')
                    motivo = (at.get('MOTIVO') or '')
                    descricao_final = (at.get('DESCRICAO') or '')
                    km_final = str(at.get('KM') or '')

                    if tipo.lower() == "viagem terrestre":
                        descricao_final = f"{origem} x {destino}" if origem or destino else ""
                    elif tipo.lower() == "viagem aérea":
                        descricao_final = f"{origem} x {destino}" if origem or destino else ""
                        km_final = ""
                    elif tipo.lower() == "translado":
                        descricao_final = f"{origem} x {destino}" if origem or destino else ""
                        km_final = ""
                    elif tipo.lower() == "período de espera":
                        descricao_final = motivo
                        km_final = ""
                    elif tipo.lower() == "mão-de-obra-técnica":
                        descricao_final = "Mão-de-Obra-Técnica"
                        km_final = ""

                    # Mantemos 7 colunas: as duas últimas são TECNICO1 e TECNICO2
                    # **Respostas NA TABELA: left-aligned (styles['response'])**, vertical center via TableStyle
                    data.append([
                        Paragraph(str(data_br or ''), styles['response']),
                        Paragraph(hora_comb, styles['response']),
                        Paragraph(tipo, styles['response']),
                        Paragraph(descricao_final, styles['response']),
                        Paragraph(km_final, styles['response']),
                        Paragraph(str(at.get('TECNICO1') or ''), styles['response']),
                        Paragraph(str(at.get('TECNICO2') or ''), styles['response']),
                    ])

                activities_table = Table(data, colWidths=col_widths, repeatRows=1)
                # estilos: GRID para todas as linhas; alinhamento do cabeçalho centralizado; respostas left; VALIGN middle
                activities_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), self.GRAY),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),     # header center
                    ('ALIGN', (0,1), (-1,-1), 'LEFT'),       # data left
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),    # vertical center ALL
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('GRID', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), 4),
                    ('RIGHTPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    # Span the TÉCNICOS header across the last two columns (5 and 6)
                    ('SPAN', (5,0), (6,0)),
                    # Remove vertical grid line only for the header split between column 5 and 6:
                    ('LINEAFTER', (5,0), (5,0), 0, colors.white),
                    ('LINEBEFORE', (6,0), (6,0), 0, colors.white),
                ]))
                story_local.append(activities_table)

            return story_local

        def estimate_height(flowables, avail_width, avail_height):
            """
            Estima a altura total (em pontos) ocupada pela lista de flowables,
            usando avail_width e avail_height (frame height) para cálculos de wrap.
            """
            h = 0.0
            for f in flowables:
                try:
                    from reportlab.platypus import Spacer as _Spacer
                    if isinstance(f, _Spacer):
                        h += f.height
                        continue
                    # Use avail_height (altura do frame), não PAGE_H
                    w, fh = f.wrap(avail_width, avail_height)
                    h += fh
                except Exception:
                    # fallback conservador
                    h += 12
            return h


        # find best scale + margins
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

            lo = MIN_SCALE
            hi = MAX_SCALE
            found_scale = None
            found_story = None
            found_styles = None
            found_pad_small = None
            found_pad_med = None

            styles_test, ps, pm = make_styles(scale=MAX_SCALE)
            story_test = build_story(styles_test, ps, pm, usable_w)
            req = estimate_height(story_test, usable_w, frame_height)
            if req <= frame_height:
                found_scale = MAX_SCALE
                found_story = story_test
                found_styles = styles_test
                found_pad_small = ps
                found_pad_med = pm
            else:
                for _ in range(12):
                    mid = (lo + hi) / 2.0
                    styles_mid, ps_mid, pm_mid = make_styles(scale=mid)
                    story_mid = build_story(styles_mid, ps_mid, pm_mid, usable_w)
                    req_mid = estimate_height(story_mid, usable_w, frame_height)
                    if req_mid <= frame_height:
                        found_scale = mid
                        found_story = story_mid
                        found_styles = styles_mid
                        found_pad_small = ps_mid
                        found_pad_med = pm_mid
                        lo = mid
                    else:
                        hi = mid
                    if (hi - lo) < 0.005:
                        break

            if found_scale is not None:
                if not best_found['fit'] or found_scale > best_found['scale']:
                    best_found.update({
                        'fit': True,
                        'scale': found_scale,
                        'top_margin': preserved_top_margin,
                        'bottom_margin': preserved_bottom_margin,
                        'usable_w': usable_w,
                        'frame_height': frame_height,
                        'story': found_story,
                        'styles': found_styles,
                        'pad_small': found_pad_small,
                        'pad_med': found_pad_med
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
            story_min = build_story(styles_min, ps_min, pm_min, usable_w)
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

        chosen_top_margin = best_found['top_margin']
        chosen_bottom_margin = best_found['bottom_margin']
        chosen_styles = best_found['styles']
        chosen_pad_small = best_found['pad_small']
        chosen_pad_med = best_found['pad_med']
        story = best_found['story']
        usable_w = best_found['usable_w']
        frame_top = PAGE_H - chosen_top_margin - header_height_base
        frame_bottom = chosen_bottom_margin + footer_total_height_base
        frame_height = max(1.0 * inch, frame_top - frame_bottom)

        doc = BaseDocTemplate(pdf_buffer, pagesize=PAGE_SIZE,
                             leftMargin=MARG, rightMargin=MARG,
                             topMargin=chosen_top_margin, bottomMargin=chosen_bottom_margin)

        content_frame = Frame(MARG, frame_bottom, usable_w, frame_height,
                              leftPadding=6, rightPadding=6, topPadding=6, bottomPadding=6, id='content_frame')

        # logo path resolution
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        default_logo = os.path.normpath(os.path.join(BASE_DIR, '..', 'static', 'images', 'logo.png'))
        lp = getattr(self.config, 'LOGO_PATH', None) or default_logo
        if lp and not os.path.isabs(lp):
            lp = os.path.normpath(os.path.join(BASE_DIR, lp))
        if isinstance(lp, bytes):
            lp = lp.decode('utf-8')
        lp = os.path.normpath(lp) if lp else lp

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
                contact_font_size = max(5, int(5 * best_found['scale']) + 2)
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

            # logo image
            try:
                if lp and os.path.exists(lp):
                    img_reader = ImageReader(lp)
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
            except Exception:
                pass

            # labels & values (canvas drawn)
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

            for i in range(3):
                top = rows_y[i]
                bottom = rows_y[i + 1]
                center_y = (top + bottom) / 2.0 - 3

                canvas.setFont(self.FONT_BOLD, max(6, int(self.BASE_LABEL_FONT_SIZE * best_found['scale'])))
                canvas.setFillColor(colors.black)
                canvas.drawString(col_x0 + left_label_padding, center_y, labels_left[i])
                val_font = max(6, int(self.BASE_VALUE_FONT_SIZE * best_found['scale']))
                if labels_left[i].startswith("LOCAL"):
                    val_font = max(7, val_font - 1)
                canvas.setFont(self.FONT_REGULAR, val_font)
                canvas.drawString(col_x1 + left_value_padding, center_y, values_left[i])

                canvas.setFont(self.FONT_BOLD, max(6, int(self.BASE_LABEL_FONT_SIZE * best_found['scale'])))
                canvas.drawString(col_x2 + right_label_padding, center_y, labels_right[i])
                canvas.setFont(self.FONT_REGULAR, val_font)

                value_text = values_right[i] or ''
                if canvas.stringWidth(value_text, self.FONT_REGULAR, val_font) > max_width:
                    while value_text and canvas.stringWidth(value_text + '…', self.FONT_REGULAR, val_font) > max_width:
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
            canvas.setFont(self.FONT_BOLD, max(6, int(self.BASE_VALUE_FONT_SIZE * best_found['scale'])))
            canvas.drawCentredString(left + usable_w / 2.0, footer_y + footer_h_local / 2.0 - 2, "O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE")

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
                canvas.setFont(self.FONT_REGULAR, max(5, int(6 * best_found['scale'])))
                canvas.setFillColor(colors.HexColor('#666666'))
                y_page = doc_local.bottomMargin - (0.10 * inch)
                canvas.drawCentredString(PAGE_W / 2.0, y_page, f"PÁGINA {doc_local.page}")
                canvas.restoreState()
            except Exception:
                pass

        page_template = PageTemplate(id='default', frames=[content_frame], onPage=on_page_template)
        doc.addPageTemplates([page_template])

        # Build PDF
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
