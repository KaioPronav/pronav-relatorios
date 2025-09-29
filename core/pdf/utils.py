# core/pdf/utils.py
import pkgutil
import os
from pathlib import Path
import unicodedata
import re
import string

def _norm_text(cell):
    try:
        if hasattr(cell, 'getPlainText'):
            s = cell.getPlainText()
        else:
            s = str(cell or '')
    except Exception:
        s = str(cell or '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.category(ch).startswith('M'))
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.strip(" " + string.punctuation)
    return s.lower()

def find_logo_bytes(config_obj):
    logo_val = getattr(config_obj, 'LOGO_PATH', None)
    if isinstance(logo_val, (bytes, bytearray)):
        try:
            return bytes(logo_val)
        except Exception:
            pass
    if logo_val and isinstance(logo_val, str):
        p = Path(logo_val)
        if not p.is_absolute():
            base = Path(__file__).resolve().parent
            p_try = (base / p).resolve()
            if p_try.exists():
                try:
                    return p_try.read_bytes()
                except Exception:
                    pass
        try:
            if p.exists():
                return p.read_bytes()
        except Exception:
            pass
    base = Path(__file__).resolve().parent.parent
    candidates = [
        base / 'static' / 'images' / 'logo.png',
        base / 'static' / 'logo.png',
        Path.cwd() / 'static' / 'images' / 'logo.png',
        Path.cwd() / 'static' / 'logo.png',
        Path(__file__).resolve().parent / 'static' / 'images' / 'logo.png'
    ]
    for c in candidates:
        try:
            if c.exists():
                return c.read_bytes()
        except Exception:
            pass
    try:
        for pkg_name in (None,):
            try:
                if pkg_name:
                    b = pkgutil.get_data(pkg_name, 'static/images/logo.png')
                    if b:
                        return b
            except Exception:
                continue
    except Exception:
        pass
    return None
