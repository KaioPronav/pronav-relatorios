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

    # PDF style multipliers (floats)
    # - SERVICE_VALUE_MULTIPLIER: estilo especial para "SERVIÇO REALIZADO" (mantido)
    # - RESPONSE_VALUE_MULTIPLIER: multiplicador aplicado ao tamanho base dos campos de resposta (default = 1.0)
    # - LABEL_VALUE_MULTIPLIER: multiplicador relativo para rótulos/cabeçalhos (padrão ~1.08)
    SERVICE_VALUE_MULTIPLIER = _env_float('SERVICE_VALUE_MULTIPLIER', 1.25, minv=0.5, maxv=3.0)
    RESPONSE_VALUE_MULTIPLIER = _env_float('RESPONSE_VALUE_MULTIPLIER', 1.02, minv=0.5, maxv=2.0)
    LABEL_VALUE_MULTIPLIER = _env_float('LABEL_VALUE_MULTIPLIER', 1.08, minv=1.0, maxv=2.0)

    # Scaling mínimo aceito pelo algoritmo de auto-fit (entre 0.2 e 1.0)
    MIN_SCALE = _env_float('MIN_SCALE', 0.40, minv=0.20, maxv=1.0)

    # Debug
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
