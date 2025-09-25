from flask import Flask
from core.config import Config
from core.database import DatabaseManager
from core.routes import init_routes
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        BASE_DIR = os.getcwd()

    LOG_PATH = os.path.join(BASE_DIR, "app.log")
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=10_000_000, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Evita adicionar handlers duplicados em múltiplas chamadas
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger

class MyFlask(Flask):
    # declara o atributo para o verificador estático
    db_manager: DatabaseManager

def create_app():
    # template_folder: mantemos relativo ao arquivo app.py (raiz do projeto)
    templates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    app = MyFlask(__name__, template_folder=templates_path)

    # Carrega configuração
    app.config.from_object(Config)

    # Setup logging
    logger = setup_logging()

    # Initialize database manager
    db_manager = DatabaseManager(app)
    app.db_manager = db_manager

    # Initialize routes
    init_routes(app, db_manager, logger)

    # Initialize database (tolerante a erros: loga em caso de falha mas não impede a criação do app)
    with app.app_context():
        try:
            db_manager.init_db()
        except Exception as e:
            # Log completo para garantir que o provedor capture o traceback
            logger.exception("Falha ao inicializar o banco de dados: %s", e)

    # Log completo das exceções não tratadas por requisição (ajuda a debugar no provedor)
    from flask import got_request_exception, request
    import sys, traceback

    def _log_request_exception(sender, exception, **extra):
        try:
            rid = request.headers.get('X-Request-ID', '') or ''
        except Exception:
            rid = ''
        logger.error("Unhandled exception (rid=%s): %s", rid, traceback.format_exc())
        sys.stderr.flush()

    got_request_exception.connect(_log_request_exception, app)

    return app

if __name__ == '__main__':
    # Apenas para execução local (Windows): tenta usar Waitress; se não estiver disponível
    # cai para o servidor de desenvolvimento do Flask (apenas para debug).
    app = create_app()

    # porta padrão (env var PORT se presente)
    port = int(os.environ.get('PORT', 5000))
    try:
        import platform
        system = platform.system().lower()
        # Em Windows, Gunicorn não roda nativamente — recomenda-se Waitress localmente.
        if system.startswith('win'):
            try:
                # usa waitress quando disponível
                from waitress import serve
                serve(app, host='0.0.0.0', port=port)
            except Exception:
                # fallback: servidor dev do Flask (somente para debug local)
                app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
        else:
            # Em Linux/mac, para desenvolvimento local, usamos Flask; em produção o Procfile/gunicorn será usado.
            app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
    except Exception as e:
        # caso algo dê errado já logamos
        logger = setup_logging()
        logger.exception("Erro ao iniciar a app localmente: %s", e)
        raise
