# wsgi.py
import os
from app import create_app  # ajuste se seu create_app estiver em outro módulo (ex: from pronav import create_app)

# Opcional: garante que FLASK_ENV/DEBUG não injetem debug em prod
os.environ.setdefault('FLASK_ENV', 'production')

app = create_app()

# exposed for gunicorn: wsgi:app
