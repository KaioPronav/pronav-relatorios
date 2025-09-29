# core/pdf/pdf_service.py
import io
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.lib.units import inch
from reportlab.lib import colors

from core.normalizers import ensure_upper_safe
from core.utils import format_date_br

from .font_manager import FontManager
from .styles_builder import make_styles
from .utils import find_logo_bytes, _norm_text
from .header_drawer import HeaderDrawer
from .footer_drawer import FooterDrawer
from .story_builder import StoryBuilder

class PDFService:
    def __init__(self, config):
        self.config = config

        # layout constants (preservamos os mesmos valores)
        self.LINE_WIDTH = 0.6
        self.GRAY = colors.HexColor('#D9D9D9')
        self.SMALL_PAD = getattr(self.config, 'SMALL_PAD', 2)
        self.MED_PAD = getattr(self.config, 'MED_PAD', 3)

        self.BASE_TITLE_FONT_SIZE = float(getattr(self.config, 'TITLE_FONT_SIZE', 8.2))
        self.BASE_LABEL_FONT_SIZE = float(getattr(self.config, 'LABEL_FONT_SIZE', 8.2))
        self.BASE_VALUE_FONT_SIZE = float(getattr(self.config, 'VALUE_FONT_SIZE', 8.2))

        if getattr(self.config, 'UNIFY_FONTS_WITH_HEADER', True):
            self.BASE_LABEL_FONT_SIZE = float(self.BASE_TITLE_FONT_SIZE)
            self.BASE_VALUE_FONT_SIZE = float(self.BASE_TITLE_FONT_SIZE)

        # font manager
        fm = FontManager(base_dir=Path(__file__).resolve().parent)
        self.FONT_REGULAR = fm.FONT_REGULAR
        self.FONT_BOLD = fm.FONT_BOLD

        # dimension constants
        self.square_side = 1.18 * inch
        self.header_row0 = 0.22 * inch
        self.header_row = 0.26 * inch
        self.header_height_base = self.header_row0 + self.header_row * 3

        self.sig_header_h_base = 0.24 * inch
        self.sig_area_h_base = 0.6 * inch
        self.footer_h_base = 0.24 * inch
        self.footer_total_height_base = self.footer_h_base + self.sig_header_h_base + self.sig_area_h_base

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

    def sanitize_for_paragraph(self, text):
        try:
            if text is None:
                return ''
            txt = str(text)
            txt = txt.replace('\r\n', '\n').replace('\r', '\n')
            from xml.sax.saxutils import escape as xml_escape
            escaped = xml_escape(txt)
            safe = escaped.replace('\n', '<br/>')
            return safe
        except Exception:
            try:
                from xml.sax.saxutils import escape as xml_escape
                return xml_escape(str(text or '')).replace('\n', '<br/>')
            except Exception:
                return ''

    def generate_pdf(self, report_request, atividades_list, equipments_list, saved_report_id):
        pdf_buffer = io.BytesIO()
        PAGE_SIZE = letter
        PAGE_W, PAGE_H = PAGE_SIZE

        # margins
        MARG = 0.35 * inch
        preserved_top_margin_base = 0.25 * inch
        preserved_bottom_margin_base = 0.12 * inch

        # frame calculations
        original_usable_w = PAGE_W - 2 * MARG
        usable_w = original_usable_w

        preserved_top_margin = preserved_top_margin_base
        preserved_bottom_margin = preserved_bottom_margin_base
        frame_top = PAGE_H - preserved_top_margin - self.header_height_base
        frame_bottom = preserved_bottom_margin + self.footer_total_height_base
        frame_height = max(1.0 * inch, frame_top - frame_bottom)

        # styles
        styles, ps, pm = make_styles(self.config, self.FONT_REGULAR, self.FONT_BOLD, self.SMALL_PAD, self.MED_PAD, self.BASE_TITLE_FONT_SIZE, self.BASE_LABEL_FONT_SIZE, self.BASE_VALUE_FONT_SIZE)

        # utils + logo
        logo_bytes = find_logo_bytes(self.config)

        # builders / drawers
        header = HeaderDrawer(self.config, self.FONT_REGULAR, self.FONT_BOLD, self.BASE_TITLE_FONT_SIZE, self.LINE_WIDTH, self.GRAY, MARG, usable_w, PAGE_W, self.header_height_base, self.header_row0, self.header_row, self.square_side)
        footer = FooterDrawer(self.BASE_VALUE_FONT_SIZE, self.BASE_LABEL_FONT_SIZE, self.LINE_WIDTH, self.GRAY, self.sig_header_h_base, self.sig_area_h_base, self.footer_h_base)

        # story builder
        story_builder = StoryBuilder(self.config, styles, ps, pm, usable_w, self.square_side, self.LINE_WIDTH, self.GRAY, None, None, format_date_br, ensure_upper_safe)
        story = story_builder.build_story(report_request, atividades_list, equipments_list, frame_height=frame_height)

        # document setup
        doc = BaseDocTemplate(pdf_buffer, pagesize=PAGE_SIZE,
                             leftMargin=MARG, rightMargin=MARG,
                             topMargin=preserved_top_margin, bottomMargin=preserved_bottom_margin)

        topPadding_val = max(4, int(4))
        content_frame = Frame(MARG, frame_bottom, usable_w, frame_height,
                              leftPadding=4, rightPadding=4, topPadding=topPadding_val, bottomPadding=4, id='content_frame')

        def on_page_template(canvas, doc_local):
            footer.on_page_template(canvas, doc_local, lambda c, d, lb, eu: header.draw_header(c, d, lb, report_request, eu), logo_bytes, ensure_upper_safe, usable_w, MARG)
        template = PageTemplate(id='normal', frames=[content_frame], onPage=on_page_template)
        doc.addPageTemplates([template])

        # build
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
