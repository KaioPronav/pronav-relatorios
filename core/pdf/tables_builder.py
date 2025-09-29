from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from xml.sax.saxutils import escape as xml_escape
from core.normalizers import ensure_upper_safe


def sanitize_for_paragraph(text):
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


def shrink_paragraph_to_fit(text, base_style, max_w, max_h, min_font=6):
    """
    Tenta reduzir o tamanho da fonte até que o Paragraph caiba em max_w x max_h.
    Retorna o Paragraph ajustado.
    """
    txt = sanitize_for_paragraph(str(text or ''))
    # tentativa com estilo original
    try:
        para = Paragraph(txt, base_style)
        w, h = para.wrap(max_w, max_h)
        if h <= max_h:
            return para
    except Exception:
        pass

    orig_size = getattr(base_style, "fontSize", 8.2)
    size = orig_size

    while size >= min_font:
        tmp_style = ParagraphStyle(name="tmp_shrink", parent=base_style)
        tmp_style.fontSize = size
        try:
            para_try = Paragraph(txt, tmp_style)
            w, h = para_try.wrap(max_w, max_h)
            if h <= max_h:
                return para_try
        except Exception:
            pass
        size -= 0.5

    tmp_style = ParagraphStyle(name="tmp_shrink_min", parent=base_style)
    tmp_style.fontSize = min_font
    return Paragraph(txt, tmp_style)


class EquipmentTableBuilder:
    def __init__(self, styles, gray, line_width, pad_small):
        self.styles = styles
        self.GRAY = gray
        self.LINE_WIDTH = line_width
        self.pad_small = pad_small

    def build(self, report_request, equipments_list, usable_w):
        # Equipamentos (compacto)
        equipments = []
        if equipments_list and len(equipments_list) > 0:
            equipments = equipments_list
        else:
            equipments = [{
                'equipamento': getattr(report_request, 'EQUIPAMENTO', '') or '',
                'fabricante': getattr(report_request, 'FABRICANTE', '') or '',
                'modelo': getattr(report_request, 'MODELO', '') or '',
                # tenta ambas as variantes de serial
                'numero_serie': getattr(report_request, 'NUMERO_SERIE', '') or getattr(report_request, 'NUMERO_DE_SERIE', '') or ''
            }]

        equip_data = [[
            Paragraph("EQUIPAMENTO", self.styles['label_center']),
            Paragraph("FABRICANTE", self.styles['label_center']),
            Paragraph("MODELO", self.styles['label_center']),
            Paragraph("Nº DE SÉRIE", self.styles['label_center'])
        ]]

        equip_col = usable_w / 4.0
        equip_cols = [equip_col] * 4
        header_h = 0.16 * inch
        value_h = 0.14 * inch
        inner_max_h = value_h - 1

        equip_left_pad = max(1, self.pad_small)
        equip_right_pad = max(1, self.pad_small)

        def _get(e, *keys):
            if not isinstance(e, dict):
                return str(e or '')
            for k in keys:
                if k in e and e[k] not in (None, ''):
                    return e[k]
                lk = k.lower()
                if lk in e and e[lk] not in (None, ''):
                    return e[lk]
            # tenta variações comuns
            for alt in ('numero_serie', 'NUMERO_SERIE', 'numero_de_serie', 'NUMERO_DE_SERIE'):
                if alt in e and e[alt] not in (None, ''):
                    return e[alt]
                if alt.lower() in e and e[alt.lower()] not in (None, ''):
                    return e[alt.lower()]
            return ''

        for eq in equipments:
            c0 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'equipamento', 'EQUIPAMENTO') or '')),
                                         self.styles['response'], equip_cols[0] - 2 * equip_left_pad, inner_max_h)
            c1 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'fabricante', 'FABRICANTE') or '')),
                                         self.styles['response'], equip_cols[1] - 2 * equip_left_pad, inner_max_h)
            c2 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'modelo', 'MODELO') or '')),
                                         self.styles['response'], equip_cols[2] - 2 * equip_left_pad, inner_max_h)
            c3 = shrink_paragraph_to_fit(ensure_upper_safe(str(_get(eq, 'numero_serie', 'NUMERO_DE_SERIE') or '')),
                                         self.styles['response'], equip_cols[3] - 2 * equip_left_pad, inner_max_h)
            equip_data.append([c0, c1, c2, c3])

        row_heights = [header_h] + [value_h] * (len(equip_data) - 1)
        equip_table = Table(equip_data, colWidths=equip_cols, rowHeights=row_heights, repeatRows=1)
        equip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.GRAY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), self.LINE_WIDTH, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), self.LINE_WIDTH / 2.0, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), equip_left_pad),
            ('RIGHTPADDING', (0, 0), (-1, -1), equip_right_pad),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        return equip_table


class ActivitiesTableBuilder:
    def __init__(self, styles, gray, line_width, pad_small, ensure_upper_safe, format_date_br):
        self.styles = styles
        self.GRAY = gray
        self.LINE_WIDTH = line_width
        self.pad_small = pad_small
        self.ensure_upper_safe = ensure_upper_safe
        self.format_date_br = format_date_br

    def build(self, atividades_list, usable_w, square_side):
        proportions = [0.09, 0.12, 0.24, 0.43, 0.03, 0.065, 0.065]

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

        # larguras em pontos (float inicialmente)
        col_widths = [p * usable_w for p in proportions]

        # --- Ajuste crucial: arredondar para inteiros e garantir soma == usable_w ---
        # converte para inteiros (pontos) para evitar subpixel/gaps e aplica resto na última coluna
        rounded = [int(round(w)) for w in col_widths]
        diff = int(round(usable_w)) - sum(rounded)
        if rounded:
            rounded[-1] += diff
        # garantir nenhuma largura negativa
        col_widths = [max(1, w) for w in rounded]

        delta_desc_pts = 18.0
        delta_tec_pts = 8.0
        delta_desc = (delta_desc_pts / 72.0) * inch
        delta_tec = (delta_tec_pts / 72.0) * inch

        # re-aplica delta (em pontos) sem quebrar a soma total
        # Aqui ajustamos as colunas por diferença relativa, mas mantemos todas como inteiros
        # (somente pequenos ajustes)
        col_widths[idx_desc] = max(int(0.08 * usable_w), int(col_widths[idx_desc] - delta_desc))
        col_widths[idx_tec1] = int(col_widths[idx_tec1] + delta_tec)
        col_widths[idx_tec2] = int(col_widths[idx_tec2] + delta_tec)

        # Se houver pequena diferença por conta dos casts, corrige na última coluna
        diff2 = int(round(usable_w)) - sum(col_widths)
        if col_widths:
            col_widths[-1] += diff2

        header_cells = [
            Paragraph("DATA", self.styles['label_center']),
            Paragraph("HORA", self.styles['label_center']),
            Paragraph("TIPO", self.styles['label_center']),
            Paragraph("DESCRIÇÃO", self.styles['label_center']),
            Paragraph("KM", self.styles['label_center']),
            Paragraph("TÉCNICOS", self.styles['label_center']),
            Paragraph("", self.styles['label_center'])
        ]

        data = [header_cells]

        for at in atividades_list:
            data_br = self.format_date_br(at.get('DATA')) if at.get('DATA') else ''
            hora_comb = at.get('HORA') or ''
            tipo = at.get('TIPO') or ''
            descricao_raw = (at.get('DESCRICAO') or '').strip()
            if descricao_raw.upper() in ('', 'X', '-', '—'):
                descricao_raw = ''

            km_final = at.get('KM') or ''

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

            if origem and destino:
                od = f"{(str(origem))} x {(str(destino))}"
                if descricao_raw:
                    descricao_final = f"{(descricao_raw)} — {od}"
                else:
                    descricao_final = od
            else:
                descricao_final = (descricao_raw)

            if str(tipo).lower() == "mão-de-obra-técnica":
                descricao_final = "Mão-de-Obra-Técnica"
                km_final = ""

            max_h_cell = 0.7 * inch
            c0 = shrink_paragraph_to_fit(str(data_br or ''), self.styles['response'], col_widths[0] - 6, max_h_cell)
            c1 = shrink_paragraph_to_fit(hora_comb, self.styles['response'], col_widths[1] - 6, max_h_cell)
            c2 = shrink_paragraph_to_fit(tipo, self.styles['response'], col_widths[2] - 6, max_h_cell)
            c3 = shrink_paragraph_to_fit(descricao_final, self.styles['response'], col_widths[3] - 6, max_h_cell)
            c4 = shrink_paragraph_to_fit(km_final, self.styles['response'], col_widths[4] - 6, max_h_cell)

            def make_tech_name(raw):
                s = str(raw or '').strip()
                if not s:
                    return ''
                parts = s.split()
                if len(parts) == 1:
                    return s
                return ' '.join(parts[:-1]) + '\u00A0' + parts[-1]

            nome_tec1 = make_tech_name(at.get('TECNICO1'))
            nome_tec2 = make_tech_name(at.get('TECNICO2'))

            c5 = shrink_paragraph_to_fit(nome_tec1, self.styles['response'], col_widths[5] - 6, max_h_cell)
            c6 = shrink_paragraph_to_fit(nome_tec2, self.styles['response'], col_widths[6] - 6, max_h_cell)

            data.append([c0, c1, c2, c3, c4, c5, c6])

        activities_table = Table(data, colWidths=col_widths, repeatRows=1)

        # usa INNERGRID para desenhar linhas internas com largura consistente
        activities_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.GRAY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), self.LINE_WIDTH, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), max(self.LINE_WIDTH / 2.0, 0.25), colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('SPAN', (5, 0), (6, 0)),
        ]))
        return activities_table


class SectionsTableBuilder:
    def __init__(self, styles, gray, line_width, pad_small):
        self.styles = styles
        self.GRAY = gray
        self.LINE_WIDTH = line_width
        self.pad_small = pad_small

    def build(self, sections, usable_w, frame_height=None, estimate_height_fn=None, page_top_offset=0):
        """
        Versão compacta:
        - Nunca força pular página desnecessariamente.
        - Evita título órfão: caso não haja espaço útil para o primeiro parágrafo da seção,
          move título+conteúdo juntos para a próxima página (exceto se estivermos no começo do documento).
        - O primeiro chunk (título + conteúdo inicial) é anexado diretamente quando possível,
          garantindo que o próximo conteúdo comece imediatamente após o anterior.
        - Quando houver overflow do conteúdo para páginas seguintes, cada página seguinte começa com
          "N. TÍTULO - Continuação" e esse título é mantido junto com o bloco de conteúdo excedente (KeepTogether).
        """
        flowables = []
        left_pad = max(0, self.pad_small)
        right_pad = max(0, self.pad_small)
        safety_gap = 1.0
        cont_margin = 2.0

        def make_title_table(text, minimal=False):
            """
            minimal=True -> título de CONTINUAÇÃO. Aumentamos um pouco o padding interno aqui
            para que o texto não fique colado nas bordas do campo.
            """
            tpar = Paragraph(text, self.styles['label'])
            tt = Table([[tpar]], colWidths=[usable_w])

            if minimal:
                # pequeno aumento: garante espaço interno extra nas continuação
                top_pad = 2
                bot_pad = 2
                lr_pad = max(2, self.pad_small) + 1  # leve incremento no left/right padding
            else:
                top_pad = 1
                bot_pad = 1
                lr_pad = max(1, self.pad_small - 1)

            tt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.GRAY),
                ('BOX', (0, 0), (-1, -1), self.LINE_WIDTH, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), lr_pad),
                ('RIGHTPADDING', (0, 0), (-1, -1), lr_pad),
                ('TOPPADDING', (0, 0), (-1, -1), top_pad),
                ('BOTTOMPADDING', (0, 0), (-1, -1), bot_pad),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            return tt

        def estimate_row_height(paragraph_obj, w):
            eff_w = max(10, w - (left_pad + right_pad))
            try:
                ph = paragraph_obj.wrap(eff_w, 10000)[1]
            except Exception:
                ph = 0.0
            return ph + 2 + (self.LINE_WIDTH or 0.0)

        def estimate_title_h(tbl):
            try:
                return tbl.wrap(usable_w, 10000)[1]
            except Exception:
                return 0.0

        if estimate_height_fn is None:
            def est_fn(items, w, fh):
                total = 0.0
                for f in items:
                    try:
                        total += f.wrap(w, fh)[1]
                    except Exception:
                        total += 0.0
                return total
        else:
            est_fn = estimate_height_fn

        for idx, (title, content) in enumerate(sections, start=1):
            title_text = f"{idx}. {title}"
            title_tbl = make_title_table(title_text, minimal=False)
            cont_title_tbl = make_title_table(f"{idx}. {title} - CONTINUAÇÃO", minimal=True)

            raw = str(content or '').strip()
            if '\r\n\r\n' in raw or '\n\n' in raw:
                paragraphs = [p.strip() for p in raw.replace('\r\n', '\n').split('\n\n') if p.strip()]
            else:
                paragraphs = [p.strip() for p in raw.replace('\r\n', '\n').split('\n') if p.strip()]

            # garantir que sempre exista ao menos um "parágrafo" (simplifica o fluxo e evita títulos órfãos)
            if not paragraphs:
                paragraphs = ['']

            style_content = (self.styles.get('section_value_large', self.styles['response'])
                             if title.strip().upper().startswith("SERVIÇO REALIZADO")
                             else self.styles['response'])

            paras = [Paragraph(p, style_content) for p in paragraphs]

            if frame_height is None:
                rows = [[p] for p in paras]
                content_tbl = Table(rows, colWidths=[usable_w], splitByRow=0)
                content_tbl.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), left_pad),
                    ('RIGHTPADDING', (0, 0), (-1, -1), right_pad),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                # Anexa diretamente — compactação máxima
                flowables.append(title_tbl)
                flowables.append(content_tbl)
                continue

            # Se temos frame_height, quebramos em chunks que caibam por página.
            i = 0
            first_chunk = True
            row_heights = [estimate_row_height(p, usable_w) for p in paras]
            title_h_first = estimate_title_h(title_tbl)
            title_h_cont = estimate_title_h(cont_title_tbl)

            while i < len(paras):
                curr_title = title_tbl if first_chunk else cont_title_tbl
                title_h = title_h_first if first_chunk else title_h_cont

                if first_chunk:
                    # agora levamos em conta o espaço já consumido na página (page_top_offset)
                    available_h = max(0.0, frame_height - title_h - page_top_offset - safety_gap)
                else:
                    # mantém o comportamento anterior para continuações
                    available_h = max(0.0, frame_height - title_h - page_top_offset - safety_gap - cont_margin)

                chunk_rows = []
                used_h = 0.0
                # empacotar o máximo possível (garantindo pelo menos um parágrafo)
                while i < len(paras):
                    h = row_heights[i]
                    if (used_h + h <= available_h) or (not chunk_rows):
                        chunk_rows.append([paras[i]])
                        used_h += h
                        i += 1
                    else:
                        break

                content_tbl = Table(chunk_rows, colWidths=[usable_w], splitByRow=0)
                content_tbl.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), self.LINE_WIDTH, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), left_pad),
                    ('RIGHTPADDING', (0, 0), (-1, -1), right_pad),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))

                # --------- comportamento seguro: evita título órfão e mantém compactação ----------
                if first_chunk:
                    # se o conteúdo do chunk cabe na área disponível, coloca título + conteúdo na página atual
                    if used_h <= available_h:
                        flowables.append(curr_title)
                        flowables.append(content_tbl)
                    else:
                        # não cabe: se estamos no início do documento (nenhum flowable ainda),
                        # anexa mesmo assim para evitar página em branco; caso contrário,
                        # mover título+conteúdo juntos para a próxima página com KeepTogether.
                        if not flowables:
                            flowables.append(curr_title)
                            flowables.append(content_tbl)
                        else:
                            flowables.append(KeepTogether([curr_title, content_tbl]))
                else:
                    # continuações: título "- Continuação" deve vir como primeiro conteúdo da nova página.
                    flowables.append(KeepTogether([curr_title, content_tbl]))

                first_chunk = False

        return flowables
