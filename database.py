import sqlite3
import json
from datetime import datetime
from flask import g
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, app):
        self.app = app

    def get_db(self):
        if 'db' not in g:
            db_path = self.app.config['DATABASE']
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute('PRAGMA journal_mode = WAL')
                conn.execute('PRAGMA synchronous = NORMAL')
                conn.execute('PRAGMA foreign_keys = ON')
            except Exception:
                pass
            g.db = conn
        return g.db

    @contextmanager
    def db_connection(self):
        db = self.get_db()
        try:
            yield db
        except sqlite3.Error as e:
            db.rollback()
            raise
        finally:
            pass

    def ensure_table_columns(self, db):
        cur = db.execute("PRAGMA table_info(reports)")
        cols = [r['name'] for r in cur.fetchall()]

        if 'status' not in cols:
            try:
                db.execute("ALTER TABLE reports ADD COLUMN status TEXT DEFAULT 'final'")
            except sqlite3.Error:
                pass

        if 'updated_at' not in cols:
            try:
                db.execute("ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP")
                try:
                    db.execute("UPDATE reports SET updated_at = created_at WHERE updated_at IS NULL")
                except sqlite3.Error:
                    pass
            except sqlite3.Error:
                pass

        if 'equipments' not in cols:
            try:
                db.execute("ALTER TABLE reports ADD COLUMN equipments TEXT")
            except sqlite3.Error:
                pass

        if 'city' not in cols:
            try:
                db.execute("ALTER TABLE reports ADD COLUMN city TEXT")
            except sqlite3.Error:
                pass
        if 'state' not in cols:
            try:
                db.execute("ALTER TABLE reports ADD COLUMN state TEXT")
            except sqlite3.Error:
                pass

    def init_db(self):
        with self.app.app_context(), self.db_connection() as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    client TEXT NOT NULL,
                    ship TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    work TEXT NOT NULL,
                    location TEXT NOT NULL,
                    os_number TEXT NOT NULL,
                    equipment TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    serial_number TEXT,
                    reported_problem TEXT,
                    service_performed TEXT,
                    result TEXT,
                    pending_issues TEXT,
                    client_material TEXT,
                    pronav_material TEXT,
                    activities TEXT,
                    equipments TEXT,
                    city TEXT,
                    state TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.commit()
            self.ensure_table_columns(db)
            db.commit()

    def close_db(self, error=None):
        db = g.pop('db', None)
        if db is not None:
            try:
                db.close()
            except Exception:
                pass

    def map_db_row_to_api(self, row):
        d = dict(row)
        if 'id' in d:
            d['report_id'] = d['id']

        if 'activities' in d and d.get('activities') is not None:
            raw_val = d.get('activities')
            parsed = []
            if isinstance(raw_val, str):
                try:
                    parsed = json.loads(raw_val)
                except Exception:
                    parsed = []
            elif isinstance(raw_val, list):
                parsed = raw_val
            else:
                try:
                    if isinstance(raw_val, (bytes, bytearray)):
                        parsed = json.loads(raw_val.decode('utf-8'))
                    else:
                        parsed = []
                except Exception:
                    parsed = []
            d['activities'] = parsed

        if 'equipments' in d and d.get('equipments') is not None:
            raw_val = d.get('equipments')
            parsed = []
            if isinstance(raw_val, str):
                try:
                    parsed = json.loads(raw_val)
                except Exception:
                    parsed = []
            elif isinstance(raw_val, list):
                parsed = raw_val
            else:
                try:
                    if isinstance(raw_val, (bytes, bytearray)):
                        parsed = json.loads(raw_val.decode('utf-8'))
                    else:
                        parsed = []
                except Exception:
                    parsed = []
            d['EQUIPAMENTOS'] = parsed

        alias_map = {
            'client': 'CLIENTE',
            'ship': 'NAVIO',
            'contact': 'CONTATO',
            'work': 'OBRA',
            'location': 'LOCAL',
            'os_number': 'OS',
            'equipment': 'EQUIPAMENTO',
            'manufacturer': 'FABRICANTE',
            'model': 'MODELO',
            'serial_number': 'NUMERO_SERIE',
            'reported_problem': 'PROBLEMA_RELATADO',
            'service_performed': 'SERVICO_REALIZADO',
            'result': 'RESULTADO',
            'pending_issues': 'PENDENCIAS',
            'client_material': 'MATERIAL_CLIENTE',
            'pronav_material': 'MATERIAL_PRONAV',
            'city': 'CIDADE',
            'state': 'ESTADO'
        }
        for low, up in alias_map.items():
            if low in d and (up not in d or d.get(up) is None):
                d[up] = d.get(low)

        loc = d.get('LOCAL', '') or ''
        city = d.get('CIDADE', '') or ''
        state = d.get('ESTADO', '') or ''
        composed = ' - '.join([p for p in [loc.strip(), city.strip(), state.strip()] if p])
        if composed:
            d['LOCAL'] = composed

        return d