import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE = os.environ.get('DATABASE_PATH', 'reports.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
    LOGO_PATH = os.environ.get('LOGO_PATH', 'logo.png')
    SERVICE_VALUE_MULTIPLIER = float(os.environ.get('SERVICE_VALUE_MULTIPLIER', '1.25'))
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'