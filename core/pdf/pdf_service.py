import io
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, cast
from math import ceil

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Image as RLImage, Paragraph, Spacer, Table, TableStyle, PageBreak, NextPageTemplate
)
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER

from core.normalizers import ensure_upper_safe
from core.utils import format_date_br

from .font_manager import FontManager
from .styles_builder import make_styles
from .utils import find_logo_bytes, _norm_text
from .header_drawer import HeaderDrawer
from .footer_drawer import FooterDrawer
from .story_builder import StoryBuilder

# Try to import helpers from image_manager. If missing, provide safe fallbacks
try:
    from .image_manager import compress_image_bytes  # type: ignore
    from .image_manager import is_landscape_image_bytes  # type: ignore
except Exception:
    # fallback compress_image_bytes(b: bytes, ...) -> bytes
    def compress_image_bytes(b: bytes, max_bytes: int = 400000, max_width_px: int = 1800, max_height_px: int = 1800, initial_quality: int = 85) -> bytes:
        return bytes(b or b'')

    # fallback is_landscape_image_bytes(b: bytes) -> bool
    def is_landscape_image_bytes(b: bytes) -> bool:
        return False


class PDFService:
    def __init__(self, config):
        self.config = config

        # --- visual defaults (all overridable via config.py) ---
        self.LINE_WIDTH = float(getattr(self.config, 'LINE_WIDTH', 0.6))
        gray_hex = getattr(self.config, 'LINE_GRAY_HEX', '#D9D9D9')
        try:
            self.GRAY = colors.HexColor(str(gray_hex))
        except Exception:
            self.GRAY = colors.HexColor('#D9D9D9')

        # paddings (pts)
        self.SMALL_PAD = int(getattr(self.config, 'SMALL_PAD', 2))
        self.MED_PAD = int(getattr(self.config, 'MED_PAD', 3))

        # base font sizes (points)
        self.BASE_TITLE_FONT_SIZE = float(getattr(self.config, 'TITLE_FONT_SIZE', getattr(self.config, 'BASE_TITLE_FONT_SIZE', 8.2)))
        self.BASE_LABEL_FONT_SIZE = float(getattr(self.config, 'LABEL_FONT_SIZE', getattr(self.config, 'BASE_LABEL_FONT_SIZE', 8.2)))
        self.BASE_VALUE_FONT_SIZE = float(getattr(self.config, 'VALUE_FONT_SIZE', getattr(self.config, 'BASE_VALUE_FONT_SIZE', 8.2)))

        if getattr(self.config, 'UNIFY_FONTS_WITH_HEADER', False):
            self.BASE_LABEL_FONT_SIZE = float(self.BASE_TITLE_FONT_SIZE)
            self.BASE_VALUE_FONT_SIZE = float(self.BASE_TITLE_FONT_SIZE)

        fm = FontManager(base_dir=Path(__file__).resolve().parent, config=self.config)
        self.FONT_REGULAR = fm.FONT_REGULAR
        self.FONT_BOLD = fm.FONT_BOLD

        def _inch_or_val(name, default_inch):
            v = getattr(self.config, name, None)
            if v is None:
                return default_inch * inch
            try:
                return float(v) * inch
            except Exception:
                try:
                    return float(v)
                except Exception:
                    return default_inch * inch

        self.MARGIN = _inch_or_val('PAGE_MARGIN_INCH', 0.35)

        self.header_row0 = _inch_or_val('HEADER_ROW0_INCH', 0.22)
        self.header_row = _inch_or_val('HEADER_ROW_INCH', 0.26)
        self.header_height_base = float(getattr(self.config, 'HEADER_HEIGHT_BASE', (self.header_row0 + self.header_row * 3)))

        self.square_side = _inch_or_val('SQUARE_SIDE_INCH', 1.18)

        self.sig_header_h_base = _inch_or_val('SIG_HEADER_H_INCH', 0.24)
        self.sig_area_h_base = _inch_or_val('SIG_AREA_H_INCH', 0.6)
        self.footer_h_base = _inch_or_val('FOOTER_H_INCH', 0.24)
        self.footer_total_height_base = float(getattr(self.config, 'FOOTER_TOTAL_HEIGHT_BASE',
                                                      (self.footer_h_base + self.sig_header_h_base + self.sig_area_h_base)))

        self.preserved_top_margin_base = _inch_or_val('PRESERVED_TOP_MARGIN_INCH', 0.25)
        self.preserved_bottom_margin_base = _inch_or_val('PRESERVED_BOTTOM_MARGIN_INCH', 0.12)

        # default top padding inside frames (pts)
        self.TOP_PADDING = int(getattr(self.config, 'TOP_PADDING', 4))

        # image tuning
        self.IMAGE_TOP_PADDING = float(getattr(self.config, 'IMAGE_TOP_PADDING', 18.0))  # distance from header to images
        self.IMAGE_PRINT_MAX_CELL_HEIGHT = float(getattr(self.config, 'IMAGE_PRINT_MAX_CELL_HEIGHT', 140.0))  # unify height

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

    def _extract_captions_from_request(self, report_request: Any, image_count: int) -> List[str]:
        """
        Extrai legendas do request de forma DIRETA e EFETIVA.
        """
        captions: List[str] = []
        try:
            print(f"🔍 DEBUG: Iniciando extração de legendas para {image_count} imagens")

            # Método 1: Se request for um dicionário (caso mais comum com FormData)
            if isinstance(report_request, dict):
                print("📝 DEBUG: Request é dicionário")

                # Tenta obter 'captions' como lista
                cand = report_request.get('captions') if isinstance(report_request, dict) else None
                if isinstance(cand, list):
                    captions = [str(x) for x in cand]
                    print(f"✅ DEBUG: Encontradas {len(captions)} legendas via dict['captions']: {captions}")
                elif cand is not None:
                    captions = [str(cand)]
                    print(f"✅ DEBUG: Legenda única via dict['captions']: '{cand}'")

                # Tenta 'captions[]'
                if not captions:
                    cand2 = report_request.get('captions[]')
                    if isinstance(cand2, list):
                        captions = [str(x) for x in cand2]
                        print(f"✅ DEBUG: Encontradas {len(captions)} legendas via dict['captions[]']: {captions}")
                    elif cand2 is not None:
                        captions = [str(cand2)]
                        print(f"✅ DEBUG: Legenda única via dict['captions[]']: '{cand2}'")

                # Campos individuais caption_0 ...
                if not captions:
                    temp_captions = []
                    for i in range(image_count):
                        key = f'caption_{i}'
                        if key in report_request:
                            caption_val = report_request[key]
                            temp_captions.append(str(caption_val) if caption_val is not None else '')
                    if temp_captions:
                        captions = temp_captions
                        print(f"✅ DEBUG: Encontradas {len(captions)} legendas via campos individuais: {captions}")

            # Método 2: Se report_request é objeto com __dict__ (Pydantic model, etc.)
            elif hasattr(report_request, '__dict__'):
                print("🔧 DEBUG: Request é objeto com __dict__")
                try:
                    # Prefer attribute 'captions'
                    if hasattr(report_request, 'captions'):
                        cand = getattr(report_request, 'captions')
                        if isinstance(cand, list):
                            captions = [str(x) for x in cand]
                            print(f"✅ DEBUG: Encontradas {len(captions)} legendas via attr 'captions': {captions}")
                        elif cand is not None:
                            captions = [str(cand)]
                            print(f"✅ DEBUG: Legenda única via attr 'captions': '{cand}'")

                    # Some objects might expose a dict mapping
                    request_dict = getattr(report_request, '__dict__', None)
                    if not captions and isinstance(request_dict, dict):
                        if 'captions' in request_dict:
                            cand = request_dict.get('captions')
                            if isinstance(cand, list):
                                captions = [str(x) for x in cand]
                                print(f"✅ DEBUG: Encontradas {len(captions)} legendas via __dict__['captions']: {captions}")
                            elif cand is not None:
                                captions = [str(cand)]
                                print(f"✅ DEBUG: Legenda única via __dict__['captions']: '{cand}'")
                        elif 'captions[]' in request_dict:
                            cand = request_dict.get('captions[]')
                            if isinstance(cand, list):
                                captions = [str(x) for x in cand]
                                print(f"✅ DEBUG: Encontradas {len(captions)} legendas via __dict__['captions[]']: {captions}")
                            elif cand is not None:
                                captions = [str(cand)]
                                print(f"✅ DEBUG: Legenda única via __dict__['captions[]']: '{cand}'")
                except Exception as e:
                    print(f"⚠️ DEBUG (obj __dict__): {e}")

            # Método 3: Se for um request-like (Flask request.form) com getlist
            if not captions and not isinstance(report_request, dict) and hasattr(report_request, 'getlist') and callable(getattr(report_request, 'getlist')):
                try:
                    cand_list = report_request.getlist('captions') or []
                    if cand_list:
                        captions = [str(x) for x in cand_list]
                        print(f"✅ DEBUG: Encontradas {len(captions)} legendas via getlist('captions'): {captions}")
                    else:
                        cand_list2 = report_request.getlist('captions[]') or []
                        if cand_list2:
                            captions = [str(x) for x in cand_list2]
                            print(f"✅ DEBUG: Encontradas {len(captions)} legendas via getlist('captions[]'): {captions}")
                except Exception as e:
                    print(f"⚠️ DEBUG: Erro em getlist: {e}")

            # fallback: no captions found
            if captions:
                print(f"🎉 DEBUG: LEGENDAS EXTRAÍDAS COM SUCESSO: {captions}")
            else:
                print("❌ DEBUG: NENHUMA LEGENDA ENCONTRADA!")

        except Exception as e:
            print(f"💥 ERRO CRÍTICO ao extrair legendas: {e}")
            captions = []

        # Guarantee the list length equals image_count
        while len(captions) < image_count:
            captions.append('')

        print(f"📊 DEBUG: Retornando {len(captions)} legendas: {captions}")
        return captions[:image_count]

    def _make_images_grid_table(
        self,
        images: List[Dict[str, Any]],
        usable_w: float,
        cols: int = 3,
        gap_pt: float = 12.0,
        target_ratio: float = (3.0 / 4.0),
        caption_font_size: int = 8,
        caption_leading: int = 9
    ) -> Table:
        """
        Cria uma Table (flowable) que preenche exatamente usable_w de largura,
        FORÇANDO que cada imagem ocupe exatamente a largura/altura da célula (ESTICADA).
        """
        styles = getSampleStyleSheet()
        caption_style = ParagraphStyle(
            name="img_caption",
            parent=styles['Normal'],
            fontName=getattr(self, 'FONT_REGULAR', 'Helvetica'),
            fontSize=caption_font_size,
            leading=caption_leading,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=0,
            textColor=colors.black,
        )

        if not images:
            return Table([[]], colWidths=[usable_w])

        # assegurar cols e calcular dimensões das células
        cols = max(1, int(cols))
        total_gaps = gap_pt * (cols - 1) if cols > 1 else 0.0
        available_for_cells = max(1.0, usable_w - total_gaps)
        cell_w = available_for_cells / cols
        # calcular altura da célula baseada na razão desejada (ou usar config)
        # target_ratio = width/height -> height = width / target_ratio
        cell_h = cell_w / float(target_ratio) if target_ratio and target_ratio > 0 else cell_w

        # montar col_widths intercalando gap columns para garantir soma == usable_w
        col_widths = []
        for i in range(cols):
            col_widths.append(cell_w)
            if i < cols - 1:
                col_widths.append(gap_pt)

        # helper: criar RLImage FORÇADA com largura=cell_w, altura=cell_h (esticamento intencional)
        def _create_forced_rl_image(image_bytes: bytes, forced_w: float, forced_h: float) -> Optional[RLImage]:
            try:
                buf = io.BytesIO(image_bytes)
                buf.seek(0)
                # Criar RLImage com width/height forçados -> isso estica a imagem
                rl = RLImage(buf, width=float(forced_w), height=float(forced_h))
                return rl
            except Exception:
                try:
                    # fallback via ImageReader (também forçando)
                    buf = io.BytesIO(image_bytes)
                    buf.seek(0)
                    reader = ImageReader(buf)
                    # mesmo que getSize falhe, forçamos as dimensões
                    return RLImage(buf, width=float(forced_w), height=float(forced_h))
                except Exception:
                    return None

        # montar linhas: duas linhas por linha lógica (imagem + legenda)
        rows = []
        for r in range(0, ceil(len(images) / cols)):
            img_row = []
            cap_row = []
            for c in range(cols):
                idx = r * cols + c
                if idx < len(images):
                    it = images[idx]
                    img_bytes = None
                    for k in ('bytes', 'content', 'data'):
                        if it.get(k):
                            img_bytes = it.get(k)
                            break
                    # decodificar base64 se necessário
                    if isinstance(img_bytes, str):
                        try:
                            img_bytes = base64.b64decode(img_bytes)
                        except Exception:
                            img_bytes = None

                    if isinstance(img_bytes, (bytes, bytearray)) and len(img_bytes) > 10:
                        rl_img = _create_forced_rl_image(img_bytes, forced_w=cell_w, forced_h=cell_h)
                        if rl_img:
                            # inner table para manter alinhamento e restrição exata
                            inner = Table([[rl_img]], colWidths=[cell_w], rowHeights=[cell_h])
                            inner.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                ('TOPPADDING', (0, 0), (-1, -1), 0),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            ]))
                            cell_img = inner
                        else:
                            # se falhar, deixar espaço na mesma dimensão
                            cell_img = Spacer(cell_w, cell_h)
                    else:
                        cell_img = Spacer(cell_w, cell_h)

                    caption_text = it.get('caption') or ''
                    caption_para = Paragraph(self.sanitize_for_paragraph(caption_text), caption_style)
                else:
                    cell_img = Spacer(cell_w, cell_h)
                    caption_para = Paragraph('', caption_style)

                # append image cell and (if not last column) a gap placeholder
                img_row.append(cell_img)
                if c < cols - 1:
                    img_row.append('')  # gap slot (width = gap_pt)

                cap_row.append(caption_para)
                if c < cols - 1:
                    cap_row.append('')  # gap slot

            rows.append(img_row)
            rows.append(cap_row)

        # montar tabela externa com col_widths calculadas
        table = Table(rows, colWidths=col_widths, hAlign='LEFT')
        tbl_style = TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        table.setStyle(tbl_style)
        return table


    def generate_pdf(
        self,
        report_request: Any,
        atividades_list: List[Dict[str, Any]],
        equipments_list: List[Dict[str, Any]],
        saved_report_id: Optional[str] = None,
        images_list: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Gera PDF incluindo galeria de imagens.

        IMPORTANT:
        - The caption shown below each image is ALWAYS the 'captions[]' array from the request (or 'captions').
          We NEVER use the filename as a caption nor any other image property as a caption.
        - Images are constrained to a uniform row height so they appear equal.
        - Images are pushed down from header by IMAGE_TOP_PADDING.
        """

        pdf_buffer = io.BytesIO()
        PAGE_SIZE = letter
        PAGE_W, PAGE_H = PAGE_SIZE

        MARG = float(getattr(self, 'MARGIN', 0.35 * inch))
        preserved_top_margin = float(getattr(self, 'preserved_top_margin_base', self.preserved_top_margin_base))
        preserved_bottom_margin = float(getattr(self, 'preserved_bottom_margin_base', self.preserved_bottom_margin_base))

        original_usable_w = PAGE_W - 2 * MARG
        usable_w = original_usable_w

        frame_top = PAGE_H - preserved_top_margin - self.header_height_base
        frame_bottom = preserved_bottom_margin + self.footer_total_height_base
        frame_height = max(1.0 * inch, frame_top - frame_bottom)

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

        logo_bytes = find_logo_bytes(self.config)

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

        # DOCUMENT AND FRAMES (portrait and landscape)
        doc = BaseDocTemplate(
            pdf_buffer,
            pagesize=PAGE_SIZE,
            leftMargin=MARG,
            rightMargin=MARG,
            topMargin=preserved_top_margin,
            bottomMargin=preserved_bottom_margin
        )

        topPadding_val = max(1, int(getattr(self, 'TOP_PADDING', 4)))
        # portrait frame
        content_frame_portrait = Frame(
            MARG,
            frame_bottom,
            usable_w,
            frame_height,
            leftPadding=max(0, int(getattr(self.config, 'FRAME_LEFT_PADDING', 4))),
            rightPadding=max(0, int(getattr(self.config, 'FRAME_RIGHT_PADDING', 4))),
            topPadding=topPadding_val,
            bottomPadding=max(0, int(getattr(self.config, 'FRAME_BOTTOM_PADDING', 4))),
            id='content_frame_portrait'
        )

        # landscape sizes and frame
        L_W, L_H = landscape(letter)
        usable_w_land = L_W - 2 * MARG
        frame_top_land = L_H - preserved_top_margin - self.header_height_base
        frame_bottom_land = preserved_bottom_margin + self.footer_total_height_base
        frame_height_land = max(1.0 * inch, frame_top_land - frame_bottom_land)
        content_frame_landscape = Frame(
            MARG,
            frame_bottom_land,
            usable_w_land,
            frame_height_land,
            leftPadding=max(0, int(getattr(self.config, 'FRAME_LEFT_PADDING', 4))),
            rightPadding=max(0, int(getattr(self.config, 'FRAME_RIGHT_PADDING', 4))),
            topPadding=topPadding_val,
            bottomPadding=max(0, int(getattr(self.config, 'FRAME_BOTTOM_PADDING', 4))),
            id='content_frame_landscape'
        )

        def on_page_template_canvas(canvas, doc_local):
            # choose usable width according to template id
            used_usable = usable_w if getattr(doc_local, 'pageTemplate', None) and getattr(doc_local.pageTemplate, 'id', '') == 'normal' else usable_w_land
            footer.on_page_template(
                canvas,
                doc_local,
                lambda c, d, lb, eu: header.draw_header(c, d, lb, report_request, eu),
                logo_bytes,
                ensure_upper_safe,
                used_usable,
                MARG
            )

        # two templates: normal (portrait) and landscape
        template_portrait = PageTemplate(id='normal', frames=[content_frame_portrait], onPage=on_page_template_canvas)
        template_land = PageTemplate(id='landscape', frames=[content_frame_landscape], onPage=on_page_template_canvas, pagesize=landscape(letter))

        doc.addPageTemplates([template_portrait, template_land])

        # ------------------------
        # IMAGES NORMALIZATION
        # ------------------------
        max_cols = int(getattr(self.config, 'IMAGE_MAX_COLUMNS', 3))
        max_per_page = int(getattr(self.config, 'IMAGE_MAX_PER_PAGE', 9))
        img_max_bytes = int(getattr(self.config, 'IMAGE_MAX_BYTES', 400000))  # 400k default
        img_max_w_px = int(getattr(self.config, 'IMAGE_MAX_WIDTH_PX', 1800))
        img_max_h_px = int(getattr(self.config, 'IMAGE_MAX_HEIGHT_PX', 1800))
        jpeg_q = int(getattr(self.config, 'IMAGE_JPEG_QUALITY', 85))
        upload_limit = int(getattr(self.config, 'IMAGE_UPLOAD_LIMIT', 50))
        img_cell_max_h = float(getattr(self.config, 'IMAGE_PRINT_MAX_CELL_HEIGHT', self.IMAGE_PRINT_MAX_CELL_HEIGHT))  # in pts

        def _normalize_image_item(it: Any) -> Optional[Dict[str, Any]]:
            """
            Normalize input item into {'bytes': Optional[bytes], 'caption': str, 'filename': str}
            IMPORTANT: caption is NOT extracted from the image object itself here.
            Captions MUST come exclusively from the captions[] array extracted separately.
            """
            if it is None:
                return None

            # raw bytes
            if isinstance(it, (bytes, bytearray)):
                return {'bytes': bytes(it), 'caption': '', 'filename': ''}

            if isinstance(it, dict):
                b: Optional[bytes] = None
                val = it.get('bytes') if 'bytes' in it else it.get('content')
                if isinstance(val, (bytes, bytearray)):
                    b = bytes(val)
                else:
                    file_obj = it.get('file')
                    if file_obj is not None and hasattr(file_obj, 'read') and callable(getattr(file_obj, 'read')):
                        try:
                            maybe = file_obj.read()
                            if isinstance(maybe, (bytes, bytearray)):
                                b = bytes(maybe)
                        except Exception:
                            b = None

                    if b is None:
                        b64cand = None
                        v1 = it.get('b64')
                        if isinstance(v1, str) and v1.strip():
                            b64cand = v1
                        else:
                            v2 = it.get('base64')
                            if isinstance(v2, str) and v2.strip():
                                b64cand = v2
                            else:
                                v3 = it.get('b64_data')
                                if isinstance(v3, str) and v3.strip():
                                    b64cand = v3
                        if isinstance(b64cand, str):
                            try:
                                b = base64.b64decode(b64cand)
                            except Exception:
                                b = None

                filename = it.get('filename') or it.get('name') or it.get('originalFileName') or ''

                # DO NOT extract caption from the image dict — set empty and rely on captions[] from request
                caption = ''

                return {'bytes': b, 'caption': caption or '', 'filename': filename or ''}

            # file-like objects
            if hasattr(it, 'read') and callable(getattr(it, 'read')):
                try:
                    maybe = it.read()
                    b = maybe if isinstance(maybe, (bytes, bytearray)) else None
                except Exception:
                    b = None
                fn = getattr(it, 'filename', '') or getattr(it, 'name', '') or ''
                # caption left blank intentionally
                return {'bytes': b, 'caption': '', 'filename': fn or ''}

            # string (base64)
            if isinstance(it, str) and it.strip():
                try:
                    b = base64.b64decode(it)
                    return {'bytes': b, 'caption': '', 'filename': ''}
                except Exception:
                    return None

            return None

        imgs = images_list
        if imgs is None:
            imgs = []
            maybe_imgs = None
            try:
                maybe_imgs = getattr(report_request, 'IMAGES', None)
            except Exception:
                maybe_imgs = None
            if not maybe_imgs:
                maybe_imgs = getattr(report_request, 'images', None)
            if maybe_imgs:
                imgs = maybe_imgs

        normalized_images: List[Dict[str, Any]] = []
        try:
            if imgs is None:
                imgs = []
            if isinstance(imgs, (list, tuple)):
                for it in imgs:
                    ni = _normalize_image_item(it)
                    if ni:
                        normalized_images.append(ni)
            elif isinstance(imgs, str):
                try:
                    parsed = json.loads(imgs)
                    if isinstance(parsed, list):
                        for it in parsed:
                            ni = _normalize_image_item(it)
                            if ni:
                                normalized_images.append(ni)
                except Exception:
                    try:
                        b = base64.b64decode(imgs)
                        normalized_images.append({'bytes': b, 'caption': '', 'filename': ''})
                    except Exception:
                        pass
        except Exception:
            normalized_images = []

        if len(normalized_images) > upload_limit:
            normalized_images = normalized_images[:upload_limit]

        # 🚨 DEBUG COMPLETO DAS LEGENDAS
        if normalized_images:
            print("=" * 80)
            print("🚀 INICIANDO DEBUG DE LEGENDAS")
            print("=" * 80)

            # Debug do request
            print(f"📨 TIPO do report_request: {type(report_request)}")
            if isinstance(report_request, dict):
                print(f"📊 CHAVES no report_request: {list(report_request.keys())}")
                # Mostrar valores das chaves relacionadas a legendas
                for key in ['captions', 'captions[]', 'caption_0', 'caption_1', 'caption_2']:
                    if key in report_request:
                        print(f"   {key} = {report_request[key]} (tipo: {type(report_request[key])})")
            else:
                try:
                    attrs = [a for a in dir(report_request) if not a.startswith('_')]
                    print(f"🔍 Atributos do objeto: {attrs[:50]}")
                except Exception:
                    pass

            # Extrair legendas
            extracted_captions = self._extract_captions_from_request(report_request, len(normalized_images))

            print(f"🎯 LEGENDAS EXTRAÍDAS: {extracted_captions}")
            print(f"📷 TOTAL DE IMAGENS: {len(normalized_images)}")

            # Aplicar legendas às imagens
            for i, cap in enumerate(extracted_captions):
                if i < len(normalized_images):
                    normalized_images[i]['caption'] = cap or ''
                    print(f"   🖼️ Imagem {i+1}: '{cap}'")

            print("=" * 80)
            print("✅ DEBUG DE LEGENDAS CONCLUÍDO")
            print("=" * 80)

        # ------------------------
        # BUILD IMAGE PAGES
        # ------------------------
        def build_image_pages(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """
            Gera páginas com grade 3x3 (9 imagens por página).
            Ajustes:
             - mais espaço entre imagens (gap_x/gap_y maiores por padrão),
             - imagens ligeiramente menores proporcionalmente (IMAGE_CELL_SCALE),
             - grade ainda preenche 100% da largura útil (usable_w),
             - imagens forçadas (esticadas) à dimensão interna (image_w x image_h) e centralizadas na célula.
            """
            pages: List[Dict[str, Any]] = []
            try:
                if not images:
                    return pages

                # FIX: 3x3
                cols = 3
                rows = 3
                per_page = cols * rows  # 9 imagens por página

                # gaps e escala (configuráveis)
                gap_x = float(getattr(self.config, 'IMAGE_HORIZONTAL_GAP_PT', 18.0))  # maior gap horizontal padrão
                gap_y = float(getattr(self.config, 'IMAGE_VERTICAL_GAP_PT', 12.0))    # maior gap vertical padrão
                cell_scale = float(getattr(self.config, 'IMAGE_CELL_SCALE', 0.90))    # escala interna da imagem (0.9 => 90%)

                # caption style / altura de legenda (aprox.)
                caption_font = int(getattr(self.config, 'IMAGE_CAPTION_FONT_SIZE', 8))
                caption_leading = int(getattr(self.config, 'IMAGE_CAPTION_LEADING', 9))
                caption_height = float(getattr(self.config, 'IMAGE_CAPTION_HEIGHT_PT', max(12.0, caption_leading + 2)))

                # espaço vertical disponível (reservar top padding e uma margem de segurança)
                top_pad = float(getattr(self.config, 'IMAGE_TOP_PADDING', self.IMAGE_TOP_PADDING))
                safety_margin = float(getattr(self.config, 'IMAGE_PAGE_SAFETY_MARGIN_PT', 8.0))
                available_vert = max(1.0, frame_height - top_pad - safety_margin)

                # calcular altura disponível para as 3 linhas de imagens (tirando legendas e gaps verticais)
                total_captions_h = rows * caption_height
                total_vertical_gaps = (rows - 1) * gap_y
                available_for_image_rows = available_vert - total_captions_h - total_vertical_gaps
                if available_for_image_rows <= 10:
                    cell_h = max(20.0, (frame_height - top_pad - total_captions_h - total_vertical_gaps) / rows)
                else:
                    cell_h = available_for_image_rows / rows

                # largura das células de forma que a soma colunas + gaps == usable_w
                total_horizontal_gaps = (cols - 1) * gap_x
                available_for_cells = max(1.0, usable_w - total_horizontal_gaps)
                cell_w = available_for_cells / cols

                # dimensões efetivas da imagem dentro da célula (reduzida proporcionalmente)
                image_w = float(cell_w) * float(cell_scale)
                image_h = float(cell_h) * float(cell_scale)

                # preparar estilo de legenda
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib.enums import TA_CENTER
                caption_style = ParagraphStyle(
                    name='image_caption',
                    fontName=getattr(self, 'FONT_REGULAR', 'Helvetica'),
                    fontSize=caption_font,
                    leading=caption_leading,
                    alignment=TA_CENTER,
                    spaceBefore=4,
                    spaceAfter=0
                )

                # chunk em páginas de 9
                chunks = [images[i:i + per_page] for i in range(0, len(images), per_page)]

                for chunk in chunks:
                    table_rows = []
                    row_heights = []

                    for r in range(0, rows):
                        img_cells = []
                        cap_cells = []
                        for c in range(0, cols):
                            idx = r * cols + c
                            if idx < len(chunk):
                                it = chunk[idx]
                                raw = it.get('bytes')
                                caption_text = (it.get('caption') or '').strip()

                                used_flowable = None
                                if isinstance(raw, (bytes, bytearray)) and len(raw) > 20:
                                    try:
                                        buf = io.BytesIO(raw)
                                        buf.seek(0)
                                        # FORÇAR imagem para image_w x image_h (esticada proporcionalmente pela scale interna)
                                        used_flowable = RLImage(buf, width=image_w, height=image_h)
                                    except Exception:
                                        try:
                                            buf = io.BytesIO(raw)
                                            buf.seek(0)
                                            reader = ImageReader(buf)
                                            used_flowable = RLImage(buf, width=image_w, height=image_h)
                                        except Exception:
                                            used_flowable = None

                                if used_flowable is None:
                                    # placeholder do mesmo tamanho visual (image_w x image_h)
                                    used_flowable = Spacer(image_w, image_h)

                                # inner table ocupa a célula inteira (cell_w x cell_h) e centraliza o conteúdo menor (image_w x image_h)
                                inner = Table([[used_flowable]], colWidths=[cell_w], rowHeights=[cell_h])
                                inner.setStyle(TableStyle([
                                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                                    ('TOPPADDING', (0,0), (-1,-1), 0),
                                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                ]))

                                img_cells.append(inner)
                                cap_cells.append(Paragraph(self.sanitize_for_paragraph(caption_text), caption_style))
                            else:
                                img_cells.append(Spacer(cell_w, cell_h))
                                cap_cells.append(Paragraph('', caption_style))

                            # inserir placeholder de gap entre colunas (será interpretado no col_widths)
                            if c < cols - 1:
                                img_cells.append('')  # gap placeholder
                                cap_cells.append('')

                        table_rows.append(img_cells)
                        row_heights.append(cell_h)
                        table_rows.append(cap_cells)
                        row_heights.append(caption_height)

                    # col_widths intercalando gaps
                    col_widths = []
                    for i in range(cols):
                        col_widths.append(cell_w)
                        if i < cols - 1:
                            col_widths.append(gap_x)

                    page_table = Table(table_rows, colWidths=col_widths, rowHeights=row_heights, hAlign='LEFT')
                    tbl_style = TableStyle([
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ])
                    page_table.setStyle(tbl_style)

                    pages.append({'table': page_table, 'orientation': 'normal'})

            except Exception as e:
                print(f"💥 ERRO CRÍTICO em build_image_pages (3x3 scaled/gapped): {e}")
                import traceback
                traceback.print_exc()

            return pages

        # ---------- END: BUILD IMAGE PAGES ----------

        image_pages = build_image_pages(normalized_images)

        # append image pages to story (ensures template is set before PageBreak and avoids blank pages)
        if image_pages:
            for idx, pg in enumerate(image_pages):
                orient = pg.get('orientation', 'normal')
                tbl = pg.get('table')

                # set template BEFORE starting the page
                if orient == 'landscape':
                    story.append(NextPageTemplate('landscape'))
                else:
                    story.append(NextPageTemplate('normal'))

                # start a new page
                story.append(PageBreak())

                # add a spacer to push images down a bit (further from header)
                top_pad = float(getattr(self.config, 'IMAGE_TOP_PADDING', self.IMAGE_TOP_PADDING))
                if top_pad and top_pad > 0:
                    story.append(Spacer(1, top_pad))

                # insert table content immediately (header/footer will be drawn by the template)
                story.append(tbl)

        # Build final PDF
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
                try:
                    equip_name_for_file = getattr(report_request, 'EQUIPAMENTO', '') or (report_request.get('EQUIPAMENTO') if isinstance(report_request, dict) else '')
                except Exception:
                    equip_name_for_file = ''
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
