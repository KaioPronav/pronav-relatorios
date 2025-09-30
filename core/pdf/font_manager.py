# core/pdf/font_manager.py
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class FontManager:
    """
    FontManager registra fontes TTF se os caminhos forem fornecidos no config.
    Uso:
        fm = FontManager(base_dir=..., config=Config)
        # então use fm.FONT_REGULAR e fm.FONT_BOLD nos styles
    """
    def __init__(self, base_dir=None, config=None):
        self.BASE_DIR = base_dir or os.path.dirname(os.path.abspath(__file__))

        # Defaults (nomes usados no styles_builder)
        self.FONT_REGULAR = 'Helvetica'
        self.FONT_BOLD = 'Helvetica-Bold'

        # Tenta carregar as configurações do Config (se fornecido)
        self._setup_fonts(config)

    def _setup_fonts(self, config=None):
        try:
            # Valores vindos do config (se existir)
            if config is not None:
                # Se config fornecer nomes/paths, usa-os
                font_reg_path = getattr(config, 'FONT_REGULAR_PATH', None)
                font_bold_path = getattr(config, 'FONT_BOLD_PATH', None)
                font_reg_name = getattr(config, 'FONT_REGULAR_NAME', 'Arial')
                font_bold_name = getattr(config, 'FONT_BOLD_NAME', 'Arial-Bold')
            else:
                # caminhos padrão (relativos ao BASE_DIR)
                font_reg_path = os.path.join(self.BASE_DIR, 'arial.ttf')
                font_bold_path = os.path.join(self.BASE_DIR, 'arialbd.ttf')
                font_reg_name = 'Arial'
                font_bold_name = 'Arial-Bold'

            # registra fonte regular
            if font_reg_path and os.path.exists(font_reg_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_reg_name, font_reg_path))
                    self.FONT_REGULAR = font_reg_name
                except Exception:
                    # se registrar falhar, mantém default
                    pass
            else:
                # tenta procurar em pasta padrão relative a este arquivo
                fallback = os.path.join(self.BASE_DIR, 'arial.ttf')
                if os.path.exists(fallback):
                    try:
                        pdfmetrics.registerFont(TTFont('Arial', fallback))
                        self.FONT_REGULAR = 'Arial'
                    except Exception:
                        pass

            # registra fonte bold
            if font_bold_path and os.path.exists(font_bold_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_bold_name, font_bold_path))
                    self.FONT_BOLD = font_bold_name
                except Exception:
                    # fallback para mesmo arquivo regular se existia
                    if font_reg_path and os.path.exists(font_reg_path):
                        try:
                            pdfmetrics.registerFont(TTFont(f"{font_reg_name}-Bold", font_reg_path))
                            self.FONT_BOLD = f"{font_reg_name}-Bold"
                        except Exception:
                            pass
            else:
                fallback_b = os.path.join(self.BASE_DIR, 'arialbd.ttf')
                if os.path.exists(fallback_b):
                    try:
                        pdfmetrics.registerFont(TTFont('Arial-Bold', fallback_b))
                        self.FONT_BOLD = 'Arial-Bold'
                    except Exception:
                        pass

        except Exception:
            # não interrompe; mantemos defaults (Helvetica)
            pass
