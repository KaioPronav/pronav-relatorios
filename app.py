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

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger

class MyFlask(Flask):
    # declara o atributo para o verificador estático
    db_manager: DatabaseManager

def create_app():
    app = MyFlask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))

    app.config.from_object(Config)
    
    # Setup logging
    logger = setup_logging()
    
    # Initialize database manager
    db_manager = DatabaseManager(app)
    app.db_manager = db_manager
    
    # Initialize routes
    init_routes(app, db_manager, logger)
    
    # Initialize database
    with app.app_context():
        db_manager.init_db()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=Config.DEBUG)
