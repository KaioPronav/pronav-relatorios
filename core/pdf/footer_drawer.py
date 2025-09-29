# core/pdf/footer_drawer.py
from reportlab.lib import colors

class FooterDrawer:
    def __init__(self, base_value_font_size, base_label_font_size, line_width, gray_color, sig_header_h_base, sig_area_h_base, footer_h_base):
        self.BASE_VALUE_FONT_SIZE = base_value_font_size
        self.BASE_LABEL_FONT_SIZE = base_label_font_size
        self.LINE_WIDTH = line_width
        self.GRAY = gray_color
        self.sig_header_h_base = sig_header_h_base
        self.sig_area_h_base = sig_area_h_base
        self.footer_h_base = footer_h_base

    def draw_signatures_and_footer(self, canvas, doc_local, usable_w, left_margin):
        canvas.saveState()
        canvas.setLineWidth(self.LINE_WIDTH)
        canvas.setStrokeColor(colors.black)

        left = left_margin
        right = left_margin + usable_w
        mid = left + usable_w / 2.0

        bottom_margin = doc_local.bottomMargin
        sig_header_h_local = self.sig_header_h_base
        sig_area_h_local = self.sig_area_h_base
        footer_h_local = self.footer_h_base
        footer_y = bottom_margin

        canvas.setFillColor(self.GRAY)
        canvas.rect(left, footer_y, usable_w, footer_h_local, stroke=0, fill=1)
        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica-Bold", max(7, int(self.BASE_VALUE_FONT_SIZE)))
        canvas.drawCentredString(left + usable_w / 2.0, footer_y + footer_h_local / 2.0 - 3, "O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE")

        sig_bottom = footer_y + footer_h_local
        sig_total_h_local = sig_area_h_local + sig_header_h_local
        canvas.setFillColor(self.GRAY)
        canvas.rect(left, sig_bottom + sig_area_h_local, usable_w / 2.0, sig_header_h_local, stroke=0, fill=1)
        canvas.rect(mid, sig_bottom + sig_area_h_local, usable_w / 2.0, sig_header_h_local, stroke=0, fill=1)
        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica-Bold", max(7, int(self.BASE_LABEL_FONT_SIZE)))
        canvas.drawCentredString(left + (usable_w / 4.0), sig_bottom + sig_area_h_local + sig_header_h_local / 2.0 - 2, "ASSINATURA DO COMANDANTE")
        canvas.drawCentredString(mid + (usable_w / 4.0), sig_bottom + sig_area_h_local + sig_header_h_local / 2.0 - 2, "ASSINATURA DO TÉCNICO")

        canvas.setLineWidth(self.LINE_WIDTH)
        canvas.rect(left, sig_bottom, usable_w / 2.0, sig_total_h_local, stroke=1, fill=0)
        canvas.rect(mid, sig_bottom, usable_w / 2.0, sig_total_h_local, stroke=1, fill=0)
        eps = 0.4
        canvas.line(mid, sig_bottom - eps, mid, sig_bottom + sig_total_h_local + eps)

        canvas.restoreState()

    def on_page_template(self, canvas, doc_local, draw_header_fn, logo_bytes, ensure_upper_safe, usable_w, left_margin):
        # helper para PageTemplate.onPage — combina header + footer + pagina
        draw_header_fn(canvas, doc_local, logo_bytes, ensure_upper_safe)
        self.draw_signatures_and_footer(canvas, doc_local, usable_w, left_margin)
        try:
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor('#666666'))
            y_page = doc_local.bottomMargin - (0.04 * 1.0)
            if y_page < 6:
                y_page = 6
            canvas.drawCentredString(left_margin + usable_w / 2.0, y_page, f"Página {canvas.getPageNumber()}")
            canvas.restoreState()
        except Exception:
            pass
