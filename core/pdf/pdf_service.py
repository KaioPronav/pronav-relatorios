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

        # --- visual defaults (all overridable via config.py) ---
        self.LINE_WIDTH = float(getattr(self.config, 'LINE_WIDTH', 0.6))
        # color: accept hex string from config or fallback
        gray_hex = getattr(self.config, 'LINE_GRAY_HEX', '#D9D9D9')
        try:
            self.GRAY = colors.HexColor(str(gray_hex))
        except Exception:
            self.GRAY = colors.HexColor('#D9D9D9')

        # paddings (pts)
        self.SMALL_PAD = int(getattr(self.config, 'SMALL_PAD', 2))
        self.MED_PAD = int(getattr(self.config, 'MED_PAD', 3))

        # base font sizes (points) - read from config (VALUE_FONT_SIZE is the canonical name here)
        self.BASE_TITLE_FONT_SIZE = float(getattr(self.config, 'TITLE_FONT_SIZE', getattr(self.config, 'BASE_TITLE_FONT_SIZE', 8.2)))
        self.BASE_LABEL_FONT_SIZE = float(getattr(self.config, 'LABEL_FONT_SIZE', getattr(self.config, 'BASE_LABEL_FONT_SIZE', 8.2)))
        # support older name or new: VALUE_FONT_SIZE / BASE_VALUE_FONT_SIZE
        self.BASE_VALUE_FONT_SIZE = float(getattr(self.config, 'VALUE_FONT_SIZE', getattr(self.config, 'BASE_VALUE_FONT_SIZE', 8.2)))

        # unify fonts option: if true, label/value follow title size
        if getattr(self.config, 'UNIFY_FONTS_WITH_HEADER', False):
            self.BASE_LABEL_FONT_SIZE = float(self.BASE_TITLE_FONT_SIZE)
            self.BASE_VALUE_FONT_SIZE = float(self.BASE_TITLE_FONT_SIZE)

        # --- Font manager: register/load fonts according to config (FontManager will handle fallbacks) ---
        fm = FontManager(base_dir=Path(__file__).resolve().parent, config=self.config)
        self.FONT_REGULAR = fm.FONT_REGULAR
        self.FONT_BOLD = fm.FONT_BOLD

        # --- page / header / footer dimensions (configurable) ---
        # margins (in points) - values expressed as inches in config are converted when user sets in inches
        def _inch_or_val(name, default_inch):
            v = getattr(self.config, name, None)
            if v is None:
                return default_inch * inch
            try:
                # if user provided a number assume it's inches; if already in pts, they can pass float<1 and be multiplied: keep convention simple
                return float(v) * inch
            except Exception:
                try:
                    return float(v)
                except Exception:
                    return default_inch * inch

        # main margin
        self.MARGIN = _inch_or_val('PAGE_MARGIN_INCH', 0.35)

        # header rows & heights (defaults preserved)
        self.header_row0 = _inch_or_val('HEADER_ROW0_INCH', 0.22)
        self.header_row = _inch_or_val('HEADER_ROW_INCH', 0.26)
        self.header_height_base = float(getattr(self.config, 'HEADER_HEIGHT_BASE', (self.header_row0 + self.header_row * 3)))

        # square (logo/signature) dimension used in story builder
        self.square_side = _inch_or_val('SQUARE_SIDE_INCH', 1.18)

        # signature/footer sizes
        self.sig_header_h_base = _inch_or_val('SIG_HEADER_H_INCH', 0.24)
        self.sig_area_h_base = _inch_or_val('SIG_AREA_H_INCH', 0.6)
        self.footer_h_base = _inch_or_val('FOOTER_H_INCH', 0.24)
        self.footer_total_height_base = float(getattr(self.config, 'FOOTER_TOTAL_HEIGHT_BASE',
                                                      (self.footer_h_base + self.sig_header_h_base + self.sig_area_h_base)))

        # optional top/bottom preserved margins (inches)
        self.preserved_top_margin_base = _inch_or_val('PRESERVED_TOP_MARGIN_INCH', 0.25)
        self.preserved_bottom_margin_base = _inch_or_val('PRESERVED_BOTTOM_MARGIN_INCH', 0.12)

        # top padding inside frame (pts)
        self.TOP_PADDING = int(getattr(self.config, 'TOP_PADDING', 4))

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

        # margins (use MARGIN from config)
        MARG = float(getattr(self, 'MARGIN', 0.35 * inch))
        preserved_top_margin = float(getattr(self, 'preserved_top_margin_base', self.preserved_top_margin_base))
        preserved_bottom_margin = float(getattr(self, 'preserved_bottom_margin_base', self.preserved_bottom_margin_base))

        # frame calculations
        original_usable_w = PAGE_W - 2 * MARG
        usable_w = original_usable_w

        frame_top = PAGE_H - preserved_top_margin - self.header_height_base
        frame_bottom = preserved_bottom_margin + self.footer_total_height_base
        frame_height = max(1.0 * inch, frame_top - frame_bottom)

        # styles (pass config sizes and fonts)
        styles, ps, pm = make_styles(
            self.config,
            self.FONT_REGULAR,
            self.FONT_BOLD,
            self.SMALL_PAD,
            self.MED_PAD,
            self.BASE_TITLE_FONT_SIZE,
            self.BASE_LABEL_FONT_SIZE,
            self.BASE_VALUE_FONT_SIZE
        )

        # utils + logo
        logo_bytes = find_logo_bytes(self.config)

        # builders / drawers: pass config-driven sizes & visual params
        header = HeaderDrawer(
            self.config,
            self.FONT_REGULAR,
            self.FONT_BOLD,
            self.BASE_TITLE_FONT_SIZE,
            self.LINE_WIDTH,
            self.GRAY,
            MARG,
            usable_w,
            PAGE_W,
            self.header_height_base,
            self.header_row0,
            self.header_row,
            self.square_side
        )

        footer = FooterDrawer(
            self.BASE_VALUE_FONT_SIZE,
            self.BASE_LABEL_FONT_SIZE,
            self.LINE_WIDTH,
            self.GRAY,
            self.sig_header_h_base,
            self.sig_area_h_base,
            self.footer_h_base
        )

        # story builder
        story_builder = StoryBuilder(
            self.config,
            styles,
            ps,
            pm,
            usable_w,
            self.square_side,
            self.LINE_WIDTH,
            self.GRAY,
            None,
            None,
            format_date_br,
            ensure_upper_safe
        )

        story = story_builder.build_story(report_request, atividades_list, equipments_list, frame_height=frame_height)

        # document setup
        doc = BaseDocTemplate(
            pdf_buffer,
            pagesize=PAGE_SIZE,
            leftMargin=MARG,
            rightMargin=MARG,
            topMargin=preserved_top_margin,
            bottomMargin=preserved_bottom_margin
        )

        topPadding_val = max(1, int(getattr(self, 'TOP_PADDING', 4)))
        content_frame = Frame(
            MARG,
            frame_bottom,
            usable_w,
            frame_height,
            leftPadding=max(0, int(getattr(self.config, 'FRAME_LEFT_PADDING', 4))),
            rightPadding=max(0, int(getattr(self.config, 'FRAME_RIGHT_PADDING', 4))),
            topPadding=topPadding_val,
            bottomPadding=max(0, int(getattr(self.config, 'FRAME_BOTTOM_PADDING', 4))),
            id='content_frame'
        )

        def on_page_template(canvas, doc_local):
            footer.on_page_template(
                canvas,
                doc_local,
                lambda c, d, lb, eu: header.draw_header(c, d, lb, report_request, eu),
                logo_bytes,
                ensure_upper_safe,
                usable_w,
                MARG
            )

        template = PageTemplate(id='normal', frames=[content_frame], onPage=on_page_template)
        doc.addPageTemplates([template])

        # build PDF
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
                # support attribute or dict-like request
                equip_name_for_file = getattr(report_request, 'EQUIPAMENTO', '') or (report_request.get('EQUIPAMENTO') if isinstance(report_request, dict) else '')
            equip_name_for_file = str(equip_name_for_file).strip().replace(' ', '_').replace('/', '-')
        except Exception:
            equip_name_for_file = ''

        safe_ship = ''
        try:
            safe_ship = (getattr(report_request, 'NAVIO', None) or (report_request.get('NAVIO') if isinstance(report_request, dict) else None) or 'Geral').replace(' ', '_')
        except Exception:
            safe_ship = 'Geral'

        date_str = datetime.utcnow().strftime('%Y%m%d')
        filename = f"RS_{date_str}_{safe_ship}"
        if equip_name_for_file:
            filename = f"{filename}_{equip_name_for_file}"
        filename = f"{filename}.pdf"

        return filename
