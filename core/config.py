import os
from dotenv import load_dotenv

load_dotenv()

def _env_float(name, default, minv=None, maxv=None):
    """Lê uma variável de ambiente como float com fallback e limites opcionais."""
    val = os.environ.get(name)
    try:
        f = float(val) if val is not None else float(default)
    except Exception:
        f = float(default)
    if minv is not None:
        f = max(f, minv)
    if maxv is not None:
        f = min(f, maxv)
    return f

class Config:
    DEBUG = False
    TESTING = False
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Banco / App
    DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'reports.db'))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))

    # Logo (procura em ../static/images/logo.png por padrão)
    default_logo = os.path.normpath(os.path.join(BASE_DIR, '..', 'static', 'images', 'logo.png'))
    LOGO_PATH = os.environ.get('LOGO_PATH', default_logo)

    # ---------- Fontes e tamanhos (totalmente configuráveis aqui) ----------
    # Tamanhos base (pode ajustar por variável de ambiente)
    # Use unidades em pontos (pt). Valores padrão mantêm o visual anterior.
    TITLE_FONT_SIZE = _env_float('TITLE_FONT_SIZE', 7.5, minv=6, maxv=72)
    LABEL_FONT_SIZE = _env_float('LABEL_FONT_SIZE', 7.0, minv=6, maxv=72)
    VALUE_FONT_SIZE = _env_float('VALUE_FONT_SIZE', 6.5, minv=6, maxv=72)

    # Se True, força LABEL_FONT_SIZE e VALUE_FONT_SIZE a usarem o valor de TITLE_FONT_SIZE
    # (ou seja: "tamanho das fontes igual do cabeçalho")
    UNIFY_FONTS_WITH_HEADER = os.environ.get('UNIFY_FONTS_WITH_HEADER', 'True').lower() == 'true'

    # Multiplicadores opcionais (mantidos para flexibilidade):
    # - SERVICE_VALUE_MULTIPLIER: aumenta o tamanho da seção "SERVIÇO REALIZADO"
    SERVICE_VALUE_MULTIPLIER = _env_float('SERVICE_VALUE_MULTIPLIER', 1.20, minv=0.5, maxv=3.0)

    # Padding / ajustes mínimos
    SMALL_PAD = int(_env_float('SMALL_PAD', 2, minv=0, maxv=20))
    MED_PAD = int(_env_float('MED_PAD', 3, minv=0, maxv=40))

    # Debug
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
