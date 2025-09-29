# core/pdf/font_manager.py
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class FontManager:
    def __init__(self, base_dir=None):
        self.BASE_DIR = base_dir
        self.FONT_REGULAR = 'Helvetica'
        self.FONT_BOLD = 'Helvetica-Bold'
        self._setup_fonts()

    def _setup_fonts(self):
        try:
            base = self.BASE_DIR or os.path.dirname(os.path.abspath(__file__))
            arial = os.path.join(base, 'arial.ttf')
            arialbd = os.path.join(base, 'arialbd.ttf')
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
            # não interrompe; mantemos defaults
            pass
