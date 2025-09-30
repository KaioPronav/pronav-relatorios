from dateutil import parser as date_parser
from reportlab.lib.utils import simpleSplit
from typing import Tuple

def format_date_br(raw: str) -> str:
    if not raw:
        return ''
    raw = str(raw).strip()
    try:
        d = date_parser.parse(raw, dayfirst=True, fuzzy=True)
        return d.strftime('%d/%m/%Y')
    except Exception:
        try:
            if len(raw) >= 10 and raw[4] == '-' and raw[7] == '-':
                y, m, day = raw[:10].split('-')
                return f"{int(day):02d}/{int(m):02d}/{int(y):04d}"
        except Exception:
            pass
    return raw

def draw_text_no_abbrev(canvas, text: str, font_name: str, font_size: float,
                       x: float, y: float, max_width: float,
                       min_font_size: float = 6.0,
                       leading_mult: float = 1.06,
                       align: str = 'left'):
    """
    Desenha `text` no canvas garantindo NUNCA abreviar:
    - tenta desenhar no font_size dado
    - se não couber, reduz gradualmente até min_font_size
    - se ainda não couber, faz wrap por palavras e desenha em múltiplas linhas
    - align: 'left'|'center'|'right'
    Retorna (used_font_size, lines_drawn)
    """
    if text is None:
        text = ''

    text = str(text)

    # função para medir largura
    def _width(s, fn, fs):
        try:
            return canvas.stringWidth(s, fn, fs)
        except Exception:
            return len(s) * (fs * 0.5)

    fs = float(font_size)
    # tentativa de reduzir fonte até caber em uma linha
    while fs >= float(min_font_size):
        if _width(text, font_name, fs) <= max_width:
            # coube inteiro em 1 linha
            canvas.setFont(font_name, fs)
            if align == 'center':
                canvas.drawCentredString(x, y, text)
            elif align == 'right':
                canvas.drawRightString(x, y, text)
            else:
                canvas.drawString(x, y, text)
            return fs, [text]
        fs -= 0.5  # decremento pequeno e suave

    # se chegamos aqui, texto não cabe numa linha mesmo no menor tamanho
    # vamos quebrar em linhas usando simpleSplit (mantém palavras inteiras)
    # ajustamos font ao min_font_size
    fs = float(min_font_size)
    lines = simpleSplit(text, font_name, fs, max_width)
    canvas.setFont(font_name, fs)
    leading = max( (fs * leading_mult),  (fs + 1) )
    # desenha linhas de cima para baixo (y assume baseline para a primeira linha)
    cur_y = y
    for ln in lines:
        if align == 'center':
            canvas.drawCentredString(x, cur_y, ln)
        elif align == 'right':
            canvas.drawRightString(x, cur_y, ln)
        else:
            canvas.drawString(x, cur_y, ln)
        cur_y -= leading
    return fs, lines