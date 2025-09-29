# core/pdf/header_drawer.py
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from pathlib import Path
import io

class HeaderDrawer:
    """
    HeaderDrawer preserva a lógica original do draw_header.
    Instancie passando as constantes de página que o código original
    usava (MARG, usable_w, PAGE_W, header_height_base, header_row0, header_row, square_side).
    """

    def __init__(self, config, font_regular, font_bold,
                 base_title_font_size, line_width, gray_color,
                 margin, usable_w, page_w,
                 header_height_base, header_row0, header_row,
                 square_side):
        self.config = config
        self.FONT_REGULAR = font_regular
        self.FONT_BOLD = font_bold
        self.BASE_TITLE_FONT_SIZE = base_title_font_size
        self.LINE_WIDTH = line_width
        self.GRAY = gray_color

        # estes são os valores iguais aos usados no draw_header original
        self.MARG = margin
        self.usable_w = usable_w
        self.PAGE_W = page_w
        self.header_height_base = header_height_base
        self.header_row0 = header_row0
        self.header_row = header_row
        self.square_side = square_side

    def draw_header(self, canvas, doc_local, logo_bytes, report_request, ensure_upper_safe):
        """
        Reimplementa fielmente o draw_header original.
        Chame: header.draw_header(canvas, doc_local, logo_bytes, report_request, ensure_upper_safe)
        """

        MARG = self.MARG
        usable_w = self.usable_w
        PAGE_W = self.PAGE_W
        header_height_base = self.header_height_base
        header_row0 = self.header_row0
        header_row = self.header_row
        square_side = self.square_side

        canvas.saveState()
        canvas.setLineJoin(1)
        canvas.setLineWidth(self.LINE_WIDTH)
        canvas.setStrokeColor(colors.black)

        left_x = MARG
        right_x = MARG + usable_w
        top_y = PAGE_W and (doc_local.pagesize[1] - doc_local.topMargin) or (doc_local.pagesize[1] - doc_local.topMargin)
        # (mantive a expressão acima para garantir compatibilidade; usamos doc_local.topMargin)
        top_y = doc_local.pagesize[1] - doc_local.topMargin
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
        y_row3 = y_row2 - header_row  # == bottom_y

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

        # baseline inferior do header (igual ao y_row3)
        canvas.line(left_x, y_row3, right_x, y_row3)

        # contact line (linha de contato/rodapé pequeno acima do cabeçalho)
        try:
            contact_line = "PRONAV COMÉRCIO E SERVIÇOS LTDA.   |   CNPJ: 54.284.063/0001-46   |   Tel.: (22) 2141-2458   |   Cel.: (22) 99221-1893   |   service@pronav.com.br   |   www.pronav.com.br"
            contact_font_size = max(7, int(self.BASE_TITLE_FONT_SIZE))
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

        title_font_size = max(9, int(self.BASE_TITLE_FONT_SIZE))
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
                    logo_y = y_row3 + (header_height_base - logo_h) / 2.0
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
                            logo_y = y_row3 + (header_height_base - logo_h) / 2.0
                            canvas.drawImage(img_reader, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
                            logo_drawn = True
                    except Exception:
                        logo_drawn = False
        except Exception:
            logo_drawn = False

        if not logo_drawn:
            try:
                fsize = max(12, int(10))
                canvas.setFont(self.FONT_BOLD, fsize)
                canvas.setFillColor(colors.HexColor('#333333'))
                canvas.drawCentredString(logo_x0 + square_side/2.0, y_row3 + header_height_base/2.0 - (fsize/4.0), "PRONAV")
                canvas.setFillColor(colors.black)
            except Exception:
                pass

        # labels & values (font sizes made equal para labels/values conforme config)
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

        # compute unified font sizes (sem scaling)
        label_font = max(7, int(self.BASE_TITLE_FONT_SIZE))
        value_font = label_font  # mantém MESMO tamanho entre labels e values

        # --- calcula a posição comum do divisor vertical alinhada ao rótulo "CONTATO:" ---
        contact_label = labels_left[1]  # "CONTATO:"
        label_left_padding = 2
        contact_label_w = canvas.stringWidth(contact_label, self.FONT_BOLD, label_font)
        divider_gap_after_label = 2.0
        divider_x_common = col_x0 + label_left_padding + contact_label_w + divider_gap_after_label

        # desenha o divisor vertical do bloco esquerdo EXATAMENTE de y_row0 até y_row3
        canvas.setLineWidth(0.6)
        canvas.setStrokeColor(colors.black)
        canvas.line(divider_x_common, y_row3, divider_x_common, y_row0)

        # restaura/divisores do lado direito (CLIENTE / OBRA / OS)
        offset_left_line = 2.0
        offset_right_line = 4.0

        def clamp_x(x):
            return max(left_x, min(right_x, x))

        x_vert_1 = clamp_x(col_x2 + offset_left_line)
        x_vert_2 = clamp_x(col_x3 + offset_right_line)
        # desenha as linhas verticais dentro dos limites da página
        canvas.line(x_vert_1, y_row3, x_vert_1, y_row0)
        canvas.line(x_vert_2, y_row3, x_vert_2, y_row0)

        # desenha a linha divisória central (que você usava para separar label/value)
        divider_x_common = clamp_x(divider_x_common)
        canvas.line(divider_x_common, y_row3, divider_x_common, y_row0)

        # start x where left-value text should begin (a partir do divisor comum)
        value_gap_after_divider = 2  # texto começa logo após a linha (pequeno gap)
        value_start_base = divider_x_common + value_gap_after_divider

        for i in range(3):
            top = rows_y[i]
            bottom = rows_y[i + 1]
            center_y = (top + bottom) / 2.0 - 3

            # --- LABEL (começa próximo da borda esquerda) ---
            canvas.setFont(self.FONT_BOLD, label_font)
            canvas.setFillColor(colors.black)
            _label_text = (labels_left[i] or '').strip()

            label_left_padding = 2
            label_x = col_x0 + label_left_padding
            _label_max_w = max(8, (col_x2) - label_x - 6)
            if canvas.stringWidth(_label_text, self.FONT_BOLD, label_font) > _label_max_w:
                while _label_text and canvas.stringWidth(_label_text + '…', self.FONT_BOLD, label_font) > _label_max_w:
                    _label_text = _label_text[:-1]
                _label_text = (_label_text + '…') if _label_text else ''
            canvas.drawString(label_x, center_y, _label_text)

            # --- VALOR ESQUERDO: começa logo após o divisor comum ---
            canvas.setFont(self.FONT_REGULAR, value_font)
            _left_value_text = (values_left[i] or '').strip()

            value_start_x = value_start_base
            _left_available = max(10, (col_x2) - value_start_x - 2)

            # sem shrink-to-fit via fonte: truncamos com reticências se não couber
            text_to_draw = _left_value_text or ''
            if canvas.stringWidth(text_to_draw, self.FONT_REGULAR, value_font) > _left_available:
                while text_to_draw and canvas.stringWidth(text_to_draw + '…', self.FONT_REGULAR, value_font) > _left_available:
                    text_to_draw = text_to_draw[:-1]
                text_to_draw = (text_to_draw + '…') if text_to_draw else ''

            canvas.drawString(value_start_x, center_y, text_to_draw)

            # --- coluna direita (mantém comportamento anterior mas sem shrink de fonte) ---
            canvas.setFont(self.FONT_BOLD, label_font)
            canvas.drawString(col_x2 + right_label_padding, center_y, labels_right[i])
            canvas.setFont(self.FONT_REGULAR, value_font)

            value_text = (values_right[i] or '')
            _right_available = max(10, max_width)

            text_to_draw_r = value_text or ''
            if canvas.stringWidth(text_to_draw_r, self.FONT_REGULAR, value_font) > _right_available:
                while text_to_draw_r and canvas.stringWidth(text_to_draw_r + '…', self.FONT_REGULAR, value_font) > _right_available:
                    text_to_draw_r = text_to_draw_r[:-1]
                text_to_draw_r = (text_to_draw_r + '…') if text_to_draw_r else ''

            value_x = col_x3 + right_value_padding
            canvas.drawString(value_x, center_y, text_to_draw_r)
            # restaura fonte padrão
            canvas.setFont(self.FONT_REGULAR, value_font)

        canvas.restoreState()
