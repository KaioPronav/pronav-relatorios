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
from normalizers import ensure_upper_safe
from utils import format_date_br

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
        self.BASE_VALUE_FONT_SIZE = 7.5

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

        # We will attempt to find the largest scale in [min_scale, 1.0] that fits into the page content area.
        MIN_SCALE = 0.40
        MAX_SCALE = 1.0
        # Allow reducing margins progressively (50% to 100% of base)
        margin_reduction_factors = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]

        def make_styles(scale=1.0):
            title_sz = max(6.0, self.BASE_TITLE_FONT_SIZE * scale)
            label_sz = max(6.0, self.BASE_LABEL_FONT_SIZE * scale)
            value_sz = max(6.0, self.BASE_VALUE_FONT_SIZE * scale)
            pad_small = max(1, int(max(1, self.SMALL_PAD * scale)))
            pad_med = max(1, int(max(1, self.MED_PAD * scale)))
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='TitleCenter', fontName=self.FONT_BOLD, fontSize=title_sz, alignment=1, leading=max(8, title_sz*1.15)))
            styles.add(ParagraphStyle(name='HeaderLabelPrefill', fontName=self.FONT_BOLD, fontSize=label_sz, leading=max(7, label_sz*1.15)))
            styles.add(ParagraphStyle(name='HeaderValueFill', fontName=self.FONT_REGULAR, fontSize=max(5, value_sz-1), leading=max(7, value_sz*1.15)))
            styles.add(ParagraphStyle(name='BodyLabelPrefill', fontName=self.FONT_BOLD, fontSize=label_sz, leading=max(8, label_sz*1.15)))
            styles.add(ParagraphStyle(name='BodyValueFill', fontName=self.FONT_REGULAR, fontSize=value_sz, leading=max(9, value_sz*1.15)))
            styles.add(ParagraphStyle(name='td', fontName=self.FONT_REGULAR, fontSize=value_sz, leading=max(9, value_sz*1.15)))
            styles.add(ParagraphStyle(name='td_left', fontName=self.FONT_REGULAR, fontSize=value_sz, alignment=0, leading=max(9, value_sz*1.15)))
            styles.add(ParagraphStyle(name='td_right', fontName=self.FONT_REGULAR, fontSize=value_sz, alignment=2, leading=max(9, value_sz*1.15)))
            styles.add(ParagraphStyle(name='sec_title', fontName=self.FONT_BOLD, fontSize=label_sz, alignment=0, leading=max(8, label_sz*1.15)))

            # New: style specifically for the "SERVIÇO REALIZADO" section.
            # It uses SERVICE_VALUE_MULTIPLIER to increase font size for this field.
            try:
                mult = float(self.config.SERVICE_VALUE_MULTIPLIER)
            except Exception:
                mult = 1.25
            larger_value_sz = max(value_sz, int(value_sz * mult))
            # enforce a minimum readable font for this special field
            larger_value_sz = max(6.0, larger_value_sz)
            styles.add(ParagraphStyle(name='section_value_large', fontName=self.FONT_REGULAR, fontSize=larger_value_sz, leading=max(9, larger_value_sz*1.15)))

            return styles, pad_small, pad_med

        def build_story(styles, pad_small, pad_med, usable_w):
            story_local = []
            story_local.append(Spacer(1, 0.01 * inch))

            # Equipamento
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
                [Paragraph("EQUIPAMENTO", ParagraphStyle(name='eh', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                 Paragraph("FABRICANTE", ParagraphStyle(name='eh', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                 Paragraph("MODELO", ParagraphStyle(name='eh', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                 Paragraph("Nº DE SÉRIE", ParagraphStyle(name='eh', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1))],
                [Paragraph(ensure_upper_safe(first_eq.get('equipamento') or ''), ParagraphStyle(name='ev', fontName=self.FONT_REGULAR, fontSize=styles['td'].fontSize)),
                 Paragraph(ensure_upper_safe(first_eq.get('fabricante') or ''), ParagraphStyle(name='ev', fontName=self.FONT_REGULAR, fontSize=styles['td'].fontSize)),
                 Paragraph(ensure_upper_safe(first_eq.get('modelo') or ''), ParagraphStyle(name='ev', fontName=self.FONT_REGULAR, fontSize=styles['td'].fontSize)),
                 Paragraph(ensure_upper_safe(first_eq.get('numero_serie') or ''), ParagraphStyle(name='ev', fontName=self.FONT_REGULAR, fontSize=styles['td'].fontSize))],
            ]
            equip_table = Table(equip_data, colWidths=equip_cols, rowHeights=[0.28*inch, 0.2*inch])
            equip_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.GRAY),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
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

            # Sections
            sections = [
                ("PROBLEMA RELATADO/ENCONTRADO", report_request.PROBLEMA_RELATADO),
                ("SERVIÇO REALIZADO", report_request.SERVICO_REALIZADO),
                ("RESULTADO", report_request.RESULTADO),
                ("PENDÊNCIAS", report_request.PENDENCIAS),
                ("MATERIAL FORNECIDO PELO CLIENTE", report_request.MATERIAL_CLIENTE),
                ("MATERIAL FORNECIDO PELA PRONAV", report_request.MATERIAL_PRONAV),
            ]
            for idx, (title, content) in enumerate(sections, start=1):
                title_tbl = Table([[Paragraph(f"{idx}. {title}", styles['sec_title'])]], colWidths=[usable_w])
                title_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), self.GRAY),
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), pad_small),
                    ('RIGHTPADDING', (0,0), (-1,-1), pad_small),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                ]))

                safe_content = (str(content or '')).replace('\r\n', '\n').replace('\r', '\n')
                safe_content = safe_content.replace('\n', '<br/>')

                # Use larger style only for "SERVIÇO REALIZADO"
                if title.strip().upper().startswith("SERVIÇO REALIZADO"):
                    # ensure style exists
                    style_for_content = styles.get('section_value_large', styles['td'])
                    content_par = Paragraph(safe_content, style_for_content)
                else:
                    content_par = Paragraph(safe_content, styles['td'])

                content_tbl = Table([[content_par]], colWidths=[usable_w])
                content_tbl.setStyle(TableStyle([
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), pad_med),
                    ('RIGHTPADDING', (0,0), (-1,-1), pad_med),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                ]))

                story_local.append(KeepTogether([title_tbl, content_tbl]))
                story_local.append(Spacer(1, 0.12 * inch))

            # Activities table
            if atividades_list:
                proportions = [0.12, 0.12, 0.14, 0.34, 0.06, 0.11, 0.11]
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

                header_cells = [
                    Paragraph("DATA", ParagraphStyle(name='th', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                    Paragraph("HORA", ParagraphStyle(name='th', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                    Paragraph("TIPO", ParagraphStyle(name='th', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                    Paragraph("DESCRIÇÃO", ParagraphStyle(name='th', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                    Paragraph("KM", ParagraphStyle(name='th', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                    Paragraph("TÉCNICOS", ParagraphStyle(name='th', fontName=self.FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                    ''
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

                    safe_desc = ensure_upper_safe(at.get('DESCRICAO') or '')

                    data.append([
                        Paragraph(str(data_br or ''), styles['td']),
                        Paragraph(hora_comb, styles['td']),
                        Paragraph(str(at.get('TIPO') or ''), styles['td']),
                        Paragraph(safe_desc, styles['td']),
                        Paragraph(str(at.get('KM') or ''), styles['td']),
                        Paragraph(str(at.get('TECNICO1') or ''), styles['td_left']),
                        Paragraph(str(at.get('TECNICO2') or ''), styles['td_left']),
                    ])

                activities_table = Table(data, colWidths=col_widths, repeatRows=1)
                activities_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), self.GRAY),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('BOX', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('GRID', (0,0), (-1,-1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), 4),
                    ('RIGHTPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ('ALIGN', (5,1), (6,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
                    ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
                ]))
                story_local.append(activities_table)

            return story_local

        def estimate_height(flowables, avail_width):
            h = 0.0
            for f in flowables:
                try:
                    from reportlab.platypus import Spacer as _Spacer
                    if isinstance(f, _Spacer):
                        h += f.height
                        continue
                    w, fh = f.wrap(avail_width, PAGE_H)
                    h += fh
                except Exception:
                    h += 12
            return h

        # --- Attempt to find best scale and margin reduction to fit in first page ---
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

            # compute available content rectangle
            usable_w = original_usable_w  # left/right margins fixed
            frame_top = PAGE_H - preserved_top_margin - header_height_base
            frame_bottom = preserved_bottom_margin + footer_total_height_base
            frame_height = frame_top - frame_bottom
            if frame_height <= 0:
                continue

            # Binary search for largest scale in [MIN_SCALE, MAX_SCALE] that fits
            lo = MIN_SCALE
            hi = MAX_SCALE
            found_scale = None
            found_story = None
            found_styles = None
            found_pad_small = None
            found_pad_med = None

            # Quick check: with scale=MAX_SCALE
            styles_test, ps, pm = make_styles(scale=MAX_SCALE)
            story_test = build_story(styles_test, ps, pm, usable_w)
            req = estimate_height(story_test, usable_w)
            if req <= frame_height:
                found_scale = MAX_SCALE
                found_story = story_test
                found_styles = styles_test
                found_pad_small = ps
                found_pad_med = pm
            else:
                # binary search iterations
                for _ in range(12):
                    mid = (lo + hi) / 2.0
                    styles_mid, ps_mid, pm_mid = make_styles(scale=mid)
                    story_mid = build_story(styles_mid, ps_mid, pm_mid, usable_w)
                    req_mid = estimate_height(story_mid, usable_w)
                    if req_mid <= frame_height:
                        found_scale = mid
                        found_story = story_mid
                        found_styles = styles_mid
                        found_pad_small = ps_mid
                        found_pad_med = pm_mid
                        # try larger
                        lo = mid
                    else:
                        # too big, try smaller
                        hi = mid
                    # stop early if hi-lo small
                    if (hi - lo) < 0.005:
                        break

            if found_scale is not None:
                # store best if larger scale than previous found
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
                # we prefer larger margin factor (less reduction) if same scale: break
                break

        # If nothing fit with min scale even after margin reductions, pick the minimal scale & last margin attempt to allow multi-page
        if not best_found['fit']:
            # pick the smallest scale and last attempted margins
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
        else:
            pass

        # Now build actual doc with chosen margins and story/styles
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

        # Prepare drawing functions that capture chosen_top_margin etc.
        lp = self.config.LOGO_PATH

        def draw_header(canvas, doc_local):
            canvas.saveState()
            canvas.setLineJoin(1)
            canvas.setLineWidth(self.LINE_WIDTH)
            canvas.setStrokeColor(colors.black)

            left_x = MARG
            right_x = MARG + usable_w
            top_y = PAGE_H - doc_local.topMargin
            bottom_y = top_y - header_height_base

            sep_x1 = left_x + square_side
            sep_x2 = left_x + square_side + (usable_w - 2 * square_side if usable_w > 2 * square_side else usable_w - square_side)

            canvas.setFillColor(self.GRAY)
            canvas.rect(sep_x1, top_y - header_row0, (sep_x2 - sep_x1), header_row0, stroke=0, fill=1)
            canvas.setFillColor(colors.black)

            eps = 0.4
            canvas.line(left_x - eps, top_y + eps, right_x + eps, top_y + eps)
            canvas.line(left_x - eps, bottom_y - eps, right_x + eps, bottom_y - eps)
            canvas.line(left_x - eps, bottom_y - eps, left_x - eps, top_y + eps)
            canvas.line(right_x + eps, bottom_y - eps, right_x + eps, top_y + eps)

            canvas.line(sep_x1, bottom_y - eps, sep_x1, top_y + eps)
            canvas.line(sep_x2, bottom_y - eps, sep_x2, top_y + eps)

            y_top = top_y
            y_row0 = y_top - header_row0
            y_row1 = y_row0 - header_row
            y_row2 = y_row1 - header_row
            y_row3 = y_row2 - header_row

            canvas.line(sep_x1, y_row0, sep_x2, y_row0)
            canvas.line(sep_x1, y_row1, sep_x2, y_row1)
            canvas.line(sep_x1, y_row2, sep_x2, y_row2)
            canvas.line(sep_x1, y_row3, sep_x2, y_row3)

            inner_label_w = 0.7 * inch
            inner_val_w_left = 1.6 * inch * 1.25
            inner_label_w2 = 0.6 * inch
            total_center = sep_x2 - sep_x1

            delta_pts = 75.0
            delta_inch = (delta_pts / 72.0) * inch
            inner_val_w_left = inner_val_w_left + delta_inch

            right_available = total_center - (inner_label_w + inner_val_w_left + inner_label_w2)
            min_right = 0.6 * inch
            if right_available < min_right:
                shortage = min_right - right_available
                inner_val_w_left = max(0.9 * inch, inner_val_w_left - shortage)
                right_available = min_right
            inner_val_w_right = right_available

            col0_w, col1_w, col2_w, col3_w = inner_label_w, inner_val_w_left, inner_label_w2, inner_val_w_right
            col_x0 = sep_x1
            col_x1 = col_x0 + col0_w
            col_x2 = col_x1 + col1_w
            col_x3 = col_x2 + col2_w
            col_x4 = col_x3 + col3_w

            canvas.line(col_x1, y_row3, col_x1, y_row0)
            canvas.line(col_x2, y_row3, col_x2, y_row0)
            canvas.line(col_x3, y_row3, col_x3, y_row0)

            canvas.setFont(self.FONT_BOLD, self.BASE_TITLE_FONT_SIZE * best_found['scale'])
            canvas.drawCentredString((sep_x1 + sep_x2) / 2.0, y_top - header_row0 / 2.0 - 3, "RELATÓRIO DE SERVIÇO")

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
                    logo_w = logo_w + 3.0
                    logo_h = max(1.0, logo_h - 3.0)
                    if logo_w > max_w:
                        factor = max_w / logo_w
                        logo_w = logo_w * factor
                        logo_h = logo_h * factor
                    if logo_h > max_h:
                        factor = max_h / logo_h
                        logo_w = logo_w * factor
                        logo_h = logo_h * factor
                    logo_x = left_x + (square_side - logo_w) / 2.0
                    logo_y = bottom_y + (header_height_base - logo_h) / 2.0
                    canvas.drawImage(img_reader, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

            contact_x_center = sep_x2 + (square_side / 2.0)
            title_text = "PRONAV MARINE"
            title_font_size = max(7, int(9 * best_found['scale']))
            detail_font_size = max(5, int(6 * best_found['scale']))
            detail_lines = ["Tel.: (22) 2141-2458", "Cel.: (22) 99221-1893", "service@pronav.com.br", "www.pronav.com.br"]
            detail_leading = detail_font_size * 1.2
            total_height = title_font_size + 4 + (len(detail_lines) * detail_leading)
            square_top = top_y
            square_bottom = bottom_y
            mid_y = (square_top + square_bottom) / 2.0
            y = mid_y + total_height / 2.0

            canvas.setFont(self.FONT_BOLD, title_font_size)
            canvas.setFillColor(colors.HexColor('#005BD0'))
            canvas.drawCentredString(contact_x_center, y - (title_font_size * 0.3), title_text)

            canvas.setFillColor(colors.black)
            canvas.setFont(self.FONT_REGULAR, detail_font_size)
            y = y - (title_font_size * 0.7) - 4
            for i, ln in enumerate(detail_lines):
                canvas.drawCentredString(contact_x_center, y - i * detail_leading, ln)

            labels_left = ["NAVIO:", "CONTATO:", "LOCAL:"]
            values_left = [
                ensure_upper_safe(report_request.NAVIO or ''),
                ensure_upper_safe(report_request.CONTATO or ''),
                ' - '.join(filter(None, [ensure_upper_safe(report_request.LOCAL or ''), ensure_upper_safe(report_request.CIDADE or ''), ensure_upper_safe(report_request.ESTADO or '')]))
            ]
            labels_right = ["CLIENTE:", "OBRA:", "OS:"]
            values_right = [ensure_upper_safe(report_request.CLIENTE or ''), ensure_upper_safe(report_request.OBRA or ''), ensure_upper_safe(report_request.OS or '')]

            rows_y = [y_row0, y_row1, y_row2, y_row3]
            for i in range(3):
                top = rows_y[i]
                bottom = rows_y[i + 1]
                center_y = (top + bottom) / 2.0 - 4
                canvas.setFont(self.FONT_BOLD, max(6, int(self.BASE_LABEL_FONT_SIZE * best_found['scale'])))
                canvas.setFillColor(colors.black)
                canvas.drawString(col_x0 + 4, center_y, labels_left[i])
                val_font = max(6, int(self.BASE_VALUE_FONT_SIZE * best_found['scale']))
                if labels_left[i].startswith("LOCAL"):
                    val_font = max(5, val_font - 1)
                canvas.setFont(self.FONT_REGULAR, val_font)
                canvas.drawString(col_x1 + 4, center_y, values_left[i])
                canvas.setFont(self.FONT_BOLD, max(6, int(self.BASE_LABEL_FONT_SIZE * best_found['scale'])))
                canvas.drawString(col_x2 + 4, center_y, labels_right[i])
                canvas.setFont(self.FONT_REGULAR, val_font)
                canvas.drawString(col_x3 + 4, center_y, values_right[i])

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
                canvas.setFont(self.FONT_REGULAR, max(6, int(7 * best_found['scale'])))
                canvas.setFillColor(colors.HexColor('#666666'))
                y_page = frame_bottom + (0.06 * inch)
                canvas.drawCentredString(PAGE_W / 2.0, y_page, f"PÁGINA {doc_local.page}")
                canvas.restoreState()
            except Exception:
                pass

        page_template = PageTemplate(id='default', frames=[content_frame], onPage=on_page_template)
        doc.addPageTemplates([page_template])

        # Build PDF (story already tailored to scale and will fit first page if possible)
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