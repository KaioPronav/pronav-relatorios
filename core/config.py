import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    DATABASE = os.environ.get('DATABASE_PATH', 'reports.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))

    # Default robusto para a logo: procura em ../static/images/logo.png relativo a core/config.py
    default_logo = os.path.normpath(os.path.join(BASE_DIR, '..', 'static', 'images', 'logo.png'))
    LOGO_PATH = os.environ.get('LOGO_PATH', default_logo)

    SERVICE_VALUE_MULTIPLIER = float(os.environ.get('SERVICE_VALUE_MULTIPLIER', '1.25'))
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
