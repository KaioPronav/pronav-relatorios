# app_reportlab_layout_final.py
import io
import os
import json
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from contextlib import contextmanager
from dotenv import load_dotenv
import requests
from flask import Flask, request, send_file, render_template, jsonify, g, Response
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import List, Optional, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from dateutil import parser as date_parser

# ---------------- Config & Logging ----------------
load_dotenv()

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    BASE_DIR = os.getcwd()

LOG_PATH = os.path.join(BASE_DIR, "app.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=10_000_000, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# ---------------- Flask app ----------------
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.config['DATABASE'] = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'reports.db'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
app.config['MAX_WORKERS'] = int(os.environ.get('MAX_WORKERS', 4))
app.config['REQUEST_TIMEOUT'] = int(os.environ.get('REQUEST_TIMEOUT', 30))
DEFAULT_LOGO = os.path.join(BASE_DIR, 'logo.png')
app.config['LOGO_PATH'] = os.environ.get('LOGO_PATH', DEFAULT_LOGO)

executor = ThreadPoolExecutor(max_workers=app.config['MAX_WORKERS'])

# ---------------- Fonts ----------------
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
try:
    arial = os.path.join(BASE_DIR, 'arial.ttf')
    arialbd = os.path.join(BASE_DIR, 'arialbd.ttf')
    if os.path.exists(arial):
        pdfmetrics.registerFont(TTFont('Arial', arial))
        FONT_REGULAR = 'Arial'
        if os.path.exists(arialbd):
            pdfmetrics.registerFont(TTFont('Arial-Bold', arialbd))
            FONT_BOLD = 'Arial-Bold'
        else:
            pdfmetrics.registerFont(TTFont('Arial-Bold', arial))
            FONT_BOLD = 'Arial-Bold'
except Exception as e:
    logger.info("Arial não registrado; usando Helvetica: %s", e)

# ---------------- Layout constants ----------------
LINE_WIDTH = 0.6
GRAY = colors.HexColor('#D9D9D9')
SMALL_PAD = 4
MED_PAD = 4
BASE_TITLE_FONT_SIZE = 9.0
BASE_LABEL_FONT_SIZE = 8.0
BASE_VALUE_FONT_SIZE = 7.5

# ---------------- Service-specific configuration ----------------
# Multiplicador aplicado apenas ao campo "SERVIÇO REALIZADO"
SERVICE_VALUE_MULTIPLIER = float(os.environ.get('SERVICE_VALUE_MULTIPLIER', '1.25'))

# ---------------- Models (Pydantic) ----------------
class Activity(BaseModel):
    DATA: str
    HORA: Optional[str] = None
    HORA_INICIO: Optional[str] = None
    HORA_FIM: Optional[str] = None
    TIPO: str
    KM: Optional[str] = None
    DESCRICAO: Optional[str] = ''
    TECNICO1: str
    TECNICO2: Optional[str] = None
    MOTIVO: Optional[str] = None
    ORIGEM: Optional[str] = None
    DESTINO: Optional[str] = None

    @field_validator('DATA', 'TIPO', 'TECNICO1', mode='before')
    @classmethod
    def validate_required(cls, v):
        if v is None:
            raise ValueError('Campo obrigatório não preenchido')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Campo obrigatório não preenchido')
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode='after')
    def check_hours_present_and_km(self):
        if self.HORA and isinstance(self.HORA, str) and self.HORA.strip():
            pass
        elif (self.HORA_INICIO and isinstance(self.HORA_INICIO, str) and self.HORA_INICIO.strip()
              and self.HORA_FIM and isinstance(self.HORA_FIM, str) and self.HORA_FIM.strip()):
            pass
        else:
            raise ValueError('Informe HORA (formato antigo) ou HORA_INICIO e HORA_FIM')

        types_block_km = {"Mão-de-obra Técnica", "Período de Espera"}
        tipo_norm = (self.TIPO or '').strip()
        if tipo_norm not in types_block_km:
            if self.KM is None or (isinstance(self.KM, str) and not self.KM.strip()):
                raise ValueError('Campo KM obrigatório para este tipo de atividade')
        return self

class ReportRequest(BaseModel):
    user_id: str
    CLIENTE: str
    NAVIO: str
    CONTATO: str
    OBRA: str
    LOCAL: str
    OS: str
    EQUIPAMENTO: Optional[str] = ''
    FABRICANTE: Optional[str] = ''
    MODELO: Optional[str] = ''
    NUMERO_SERIE: Optional[str] = ''
    PROBLEMA_RELATADO: str
    SERVICO_REALIZADO: str
    RESULTADO: str
    PENDENCIAS: str
    MATERIAL_CLIENTE: str
    MATERIAL_PRONAV: str
    activities: List[Activity]
    EQUIPAMENTOS: Optional[List[Dict[str, Any]]] = None
    CIDADE: Optional[str] = None
    ESTADO: Optional[str] = None

    @field_validator('user_id', 'CLIENTE', 'NAVIO', 'CONTATO', 'OBRA', 'LOCAL', 'OS',
                     'PROBLEMA_RELATADO', 'SERVICO_REALIZADO', 'RESULTADO',
                     'PENDENCIAS', 'MATERIAL_CLIENTE', 'MATERIAL_PRONAV')
    @classmethod
    def validate_required_fields(cls, v):
        if v is None:
            raise ValueError('Campo obrigatório não preenchido')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Campo obrigatório não preenchido')
        return v.strip() if isinstance(v, str) else v

# ---------------- DB helpers ----------------
def get_db():
    if 'db' not in g:
        db_path = app.config['DATABASE']
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
def db_connection():
    db = get_db()
    try:
        yield db
    except sqlite3.Error as e:
        db.rollback()
        logger.error("DB error: %s", e)
        raise
    finally:
        pass

def ensure_table_columns(db):
    cur = db.execute("PRAGMA table_info(reports)")
    cols = [r['name'] for r in cur.fetchall()]

    if 'status' not in cols:
        try:
            db.execute("ALTER TABLE reports ADD COLUMN status TEXT DEFAULT 'final'")
            logger.info("Adicionado coluna 'status' em reports")
        except sqlite3.Error as e:
            logger.info("Não foi possível adicionar 'status' (talvez já exista): %s", e)

    if 'updated_at' not in cols:
        try:
            db.execute("ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP")
            logger.info("Adicionado coluna 'updated_at' (sem default)")
            try:
                db.execute("UPDATE reports SET updated_at = created_at WHERE updated_at IS NULL")
                logger.info("Populei 'updated_at' a partir de 'created_at' para linhas existentes")
            except sqlite3.Error as e2:
                logger.info("Não foi possível popular 'updated_at': %s", e2)
        except sqlite3.Error as e:
            logger.info("Não foi possível adicionar 'updated_at' (talvez já exista): %s", e)

    if 'equipments' not in cols:
        try:
            db.execute("ALTER TABLE reports ADD COLUMN equipments TEXT")
            logger.info("Adicionado coluna 'equipments' (JSON) em reports")
        except sqlite3.Error as e:
            logger.info("Não foi possível adicionar 'equipments' (talvez já exista): %s", e)

    if 'city' not in cols:
        try:
            db.execute("ALTER TABLE reports ADD COLUMN city TEXT")
            logger.info("Adicionado coluna 'city' em reports")
        except sqlite3.Error as e:
            logger.info("Não foi possível adicionar 'city' (talvez já exista): %s", e)
    if 'state' not in cols:
        try:
            db.execute("ALTER TABLE reports ADD COLUMN state TEXT")
            logger.info("Adicionado coluna 'state' em reports")
        except sqlite3.Error as e:
            logger.info("Não foi possível adicionar 'state' (talvez já exista): %s", e)

def init_db():
    with app.app_context(), db_connection() as db:
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
        ensure_table_columns(db)
        db.commit()

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

# ---------------- utilitários de normalização ----------------
def _pick_first(d: Dict[str, Any], keys: List[str], default=''):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def _sanitize_description(descricao: str, origem: str, destino: str, motivo: str, tipo: str) -> str:
    if not descricao:
        descricao = ''
    s = descricao.strip()
    for piece in [origem, destino, motivo]:
        if piece:
            try:
                s = s.replace(piece, '')
            except Exception:
                pass
    s = ' '.join(s.split())
    return s

def normalize_activity(raw: Dict[str, Any]) -> Dict[str, Any]:
    a = {}
    a['DATA'] = _pick_first(raw, ['DATA', 'data', 'Data']) or ''
    hora_legacy = _pick_first(raw, ['HORA', 'hora', 'Hora']) or ''
    a['HORA'] = hora_legacy or ''
    h_inicio = _pick_first(raw, ['HORA_INICIO', 'hora_inicio', 'horaInicio', 'HORAINICIO']) or ''
    h_fim = _pick_first(raw, ['HORA_FIM', 'hora_fim', 'horaFim']) or ''
    a['HORA_INICIO'] = h_inicio or ''
    a['HORA_FIM'] = h_fim or ''

    if (not a['HORA_INICIO'] or not a['HORA_FIM']) and isinstance(hora_legacy, str) and hora_legacy.strip():
        s = hora_legacy.strip()
        if 'às' in s:
            parts = [p.strip() for p in s.split('às', 1)]
            if not a['HORA_INICIO'] and parts[0]:
                a['HORA_INICIO'] = parts[0]
            if not a['HORA_FIM'] and len(parts) > 1 and parts[1]:
                a['HORA_FIM'] = parts[1]
        else:
            if not a['HORA_INICIO']:
                a['HORA_INICIO'] = s

    a['TIPO'] = _pick_first(raw, ['TIPO', 'tipo']) or ''
    a['KM'] = str(_pick_first(raw, ['KM', 'km']) or '')
    a['DESCRICAO'] = _pick_first(raw, ['DESCRICAO', 'descricao', 'Descricao', 'description']) or ''
    a['TECNICO1'] = _pick_first(raw, ['TECNICO1', 'tecnico1', 'tecnico_1']) or ''
    a['TECNICO2'] = _pick_first(raw, ['TECNICO2', 'tecnico2', 'tecnico_2']) or ''
    a['MOTIVO'] = _pick_first(raw, ['MOTIVO', 'motivo']) or ''
    a['ORIGEM'] = _pick_first(raw, ['ORIGEM', 'origem']) or ''
    a['DESTINO'] = _pick_first(raw, ['DESTINO', 'destino']) or ''

    a['DESCRICAO'] = _sanitize_description(a['DESCRICAO'], a['ORIGEM'], a['DESTINO'], a['MOTIVO'], a['TIPO'])

    km_blocked_raw = _pick_first(raw, ['KM_BLOQUEADO', 'km_bloqueado', 'KM_BLOCKED', 'kmBlocked', 'blocked_km', 'KMBLOCKED']) or False
    if isinstance(km_blocked_raw, str):
        km_blocked = km_blocked_raw.strip().lower() in ('1', 'true', 't', 'yes', 'on')
    elif isinstance(km_blocked_raw, (int, float)):
        km_blocked = bool(km_blocked_raw)
    elif isinstance(km_blocked_raw, bool):
        km_blocked = km_blocked_raw
    else:
        km_blocked = False
    a['KM_BLOQUEADO'] = km_blocked

    return a

def normalize_equipments(raw_e) -> List[Dict[str, Any]]:
    if raw_e is None:
        return []
    parsed = []
    if isinstance(raw_e, str):
        try:
            parsed = json.loads(raw_e)
        except Exception:
            parsed = []
    elif isinstance(raw_e, (list, tuple)):
        parsed = list(raw_e)
    else:
        parsed = []

    out = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        eq = {}
        eq['equipamento'] = _pick_first(item, ['equipamento', 'EQUIPAMENTO', 'equipment', 'name']) or ''
        eq['fabricante'] = _pick_first(item, ['fabricante', 'FABRICANTE', 'manufacturer']) or ''
        eq['modelo'] = _pick_first(item, ['modelo', 'MODELO', 'model']) or ''
        eq['numero_serie'] = _pick_first(item, ['numero_serie', 'NUMERO_SERIE', 'serial_number', 'sn']) or ''
        out.append(eq)
    return out

def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    normalized: Dict[str, Any] = {}
    mapping = {
        'user_id': 'user_id',
        'user': 'user_id',
        'client': 'CLIENTE',
        'ship': 'NAVIO',
        'contact': 'CONTATO',
        'work': 'OBRA',
        'location': 'LOCAL',
        'os_number': 'OS',
        'os': 'OS',
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
        'cidade': 'CIDADE',
        'estado': 'ESTADO'
    }

    normalized['user_id'] = payload.get('user_id') or payload.get('user') or payload.get('USER_ID') or 'anonymous_user'

    for src, dst in mapping.items():
        if dst == 'user_id':
            continue
        if src in payload and payload.get(src) is not None:
            normalized[dst] = payload[src]
        elif dst in payload and payload.get(dst) is not None:
            normalized[dst] = payload[dst]

    top_keys = ['CLIENTE','NAVIO','CONTATO','OBRA','LOCAL','OS','EQUIPAMENTO','FABRICANTE','MODELO','NUMERO_SERIE','PROBLEMA_RELATADO','SERVICO_REALIZADO','RESULTADO','PENDENCIAS','MATERIAL_CLIENTE','MATERIAL_PRONAV','CIDADE','ESTADO']
    for k in top_keys:
        if k not in normalized:
            normalized[k] = payload.get(k.lower(), payload.get(k.capitalize(), '')) or ''

    acts_raw = payload.get('activities') or payload.get('Activities') or payload.get('ativities') or payload.get('atividades')
    activities_list = []
    if acts_raw is None:
        activities_list = []
    else:
        parsed = []
        if isinstance(acts_raw, str):
            try:
                parsed = json.loads(acts_raw)
            except Exception:
                parsed = []
        elif isinstance(acts_raw, (list, tuple)):
            parsed = acts_raw
        else:
            if isinstance(acts_raw, (bytes, bytearray)):
                try:
                    parsed = json.loads(acts_raw.decode('utf-8'))
                except Exception:
                    parsed = []
            else:
                parsed = []

        if isinstance(parsed, list):
            for a in parsed:
                if isinstance(a, dict):
                    activities_list.append(normalize_activity(a))
                else:
                    activities_list.append({})
        else:
            activities_list = []

    normalized['activities'] = activities_list

    eqs_raw = payload.get('EQUIPAMENTOS') or payload.get('equipamentos') or payload.get('EQUIPMENTS')
    normalized['EQUIPAMENTOS'] = normalize_equipments(eqs_raw)

    if not normalized['EQUIPAMENTOS']:
        first_eq = {
            'equipamento': normalized.get('EQUIPAMENTO') or payload.get('equipment') or '',
            'fabricante': normalized.get('FABRICANTE') or payload.get('fabricante') or '',
            'modelo': normalized.get('MODELO') or payload.get('model') or '',
            'numero_serie': normalized.get('NUMERO_SERIE') or payload.get('serial_number') or ''
        }
        if any(first_eq.values()):
            normalized['EQUIPAMENTOS'] = [first_eq]

    if 'report_id' in payload:
        normalized['report_id'] = payload['report_id']
    elif 'id' in payload:
        normalized['report_id'] = payload['id']

    for k, v in payload.items():
        if k not in normalized and k not in mapping:
            normalized[k] = v

    return normalized

def map_db_row_to_api(row: sqlite3.Row) -> Dict[str, Any]:
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

# ---------------- Error handler decorator ----------------
def handle_errors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning("Validation error: %s", e)
            try:
                details = e.errors()
            except Exception:
                details = str(e)
            try:
                return jsonify({'error': 'Dados inválidos', 'details': details}), 400
            except TypeError:
                return jsonify({'error': 'Dados inválidos', 'details': str(details)}), 400
        except FileNotFoundError as e:
            logger.error("Arquivo não encontrado: %s", e)
            return jsonify({'error': 'Arquivo necessário não encontrado', 'msg': str(e)}), 404
        except sqlite3.Error as e:
            logger.error("DB error: %s", e)
            return jsonify({'error': 'Erro interno do banco de dados', 'msg': str(e)}), 500
        except requests.RequestException as e:
            logger.error("Request error: %s", e)
            return jsonify({'error': 'Erro ao acessar recursos externos', 'msg': str(e)}), 502
        except Exception as e:
            logger.exception("Unexpected error")
            return jsonify({'error': 'Erro interno do servidor', 'msg': str(e)}), 500
    return decorated

# ---------------- Helpers for PDF formatting ----------------
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

def ensure_upper_safe(s):
    try:
        return str(s or '').upper()
    except Exception:
        return str(s or '')

# ---------------- Endpoints ----------------
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception:
        return "PRONAV Report Service"

@app.route('/salvar-rascunho', methods=['POST'])
@handle_errors
def salvar_rascunho():
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

    norm = normalize_payload(payload)
    report_request = ReportRequest(**norm)
    atividades_list = [a.model_dump() for a in report_request.activities]
    equipments_list = report_request.EQUIPAMENTOS or []

    now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    with db_connection() as db:
        cur = db.execute('''
            INSERT INTO reports (
                user_id, client, ship, contact, work, location, os_number,
                equipment, manufacturer, model, serial_number, reported_problem,
                service_performed, result, pending_issues, client_material,
                pronav_material, activities, equipments, city, state, created_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            report_request.user_id,
            report_request.CLIENTE,
            report_request.NAVIO,
            report_request.CONTATO,
            report_request.OBRA,
            report_request.LOCAL,
            report_request.OS,
            report_request.EQUIPAMENTO,
            report_request.FABRICANTE,
            report_request.MODELO,
            report_request.NUMERO_SERIE,
            report_request.PROBLEMA_RELATADO,
            report_request.SERVICO_REALIZADO,
            report_request.RESULTADO,
            report_request.PENDENCIAS,
            report_request.MATERIAL_CLIENTE,
            report_request.MATERIAL_PRONAV,
            json.dumps(atividades_list, ensure_ascii=False),
            json.dumps(equipments_list, ensure_ascii=False),
            report_request.CIDADE or '',
            report_request.ESTADO or '',
            now_iso,
            now_iso,
            'draft'
        ])
        db.commit()
        report_id = cur.lastrowid
    return jsonify({'message': 'Rascunho salvo', 'report_id': report_id}), 201

@app.route('/relatorios-salvos', methods=['GET'])
@handle_errors
def relatorios_salvos():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id é obrigatório na query string'}), 400
    with db_connection() as db:
        rows = db.execute('SELECT id, client, ship, status, created_at, updated_at FROM reports WHERE user_id = ? ORDER BY COALESCE(updated_at, created_at) DESC', [user_id]).fetchall()
        result = []
        for r in rows:
            mapped = dict(r)
            mapped['CLIENTE'] = mapped.get('client')
            mapped['NAVIO'] = mapped.get('ship')
            result.append(mapped)
    return jsonify(result)

@app.route('/relatorio/<int:report_id>', methods=['GET'])
@handle_errors
def get_report(report_id):
    with db_connection() as db:
        row = db.execute('SELECT * FROM reports WHERE id = ?', [report_id]).fetchone()
        if not row:
            return jsonify({'error': 'Relatório não encontrado'}), 404
        data = map_db_row_to_api(row)
    return jsonify(data)

@app.route('/atualizar-relatorio/<int:report_id>', methods=['PUT'])
@handle_errors
def atualizar_relatorio(report_id):
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

    norm = normalize_payload(payload)
    report_request = ReportRequest(**norm)
    atividades_list = [a.model_dump() for a in report_request.activities]
    equipments_list = report_request.EQUIPAMENTOS or []

    now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    with db_connection() as db:
        cur = db.execute('''
            UPDATE reports SET
                client=?, ship=?, contact=?, work=?, location=?, os_number=?,
                equipment=?, manufacturer=?, model=?, serial_number=?,
                reported_problem=?, service_performed=?, result=?, pending_issues=?,
                client_material=?, pronav_material=?, activities=?, equipments=?, city=?, state=?, updated_at=?, status='draft'
            WHERE id=?
        ''', [
            report_request.CLIENTE,
            report_request.NAVIO,
            report_request.CONTATO,
            report_request.OBRA,
            report_request.LOCAL,
            report_request.OS,
            report_request.EQUIPAMENTO,
            report_request.FABRICANTE,
            report_request.MODELO,
            report_request.NUMERO_SERIE,
            report_request.PROBLEMA_RELATADO,
            report_request.SERVICO_REALIZADO,
            report_request.RESULTADO,
            report_request.PENDENCIAS,
            report_request.MATERIAL_CLIENTE,
            report_request.MATERIAL_PRONAV,
            json.dumps(atividades_list, ensure_ascii=False),
            json.dumps(equipments_list, ensure_ascii=False),
            report_request.CIDADE or '',
            report_request.ESTADO or '',
            now_iso,
            report_id
        ])
        db.commit()
        if cur.rowcount == 0:
            return jsonify({'error': 'Relatório não encontrado'}), 404
    return jsonify({'message': 'Relatório atualizado'}), 200

@app.route('/relatorio/<int:report_id>', methods=['DELETE'])
@handle_errors
def delete_report(report_id):
    with db_connection() as db:
        cur = db.execute('DELETE FROM reports WHERE id = ?', [report_id])
        db.commit()
        if cur.rowcount == 0:
            return jsonify({'error': 'Relatório não encontrado'}), 404
    return jsonify({'message': 'Relatório removido'}), 200

@app.route('/gerar-relatorio', methods=['POST'])
@handle_errors
def gerar_relatorio():
    form_data = request.get_json()
    if not form_data:
        return jsonify({'error': 'Payload JSON inválido ou ausente'}), 400

    norm = normalize_payload(form_data)
    report_id = norm.get('report_id') or form_data.get('report_id')

    report_request = ReportRequest(**norm)
    atividades_list = [a.model_dump() for a in report_request.activities]
    equipments_list = report_request.EQUIPAMENTOS or []

    now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    with db_connection() as db:
        if report_id:
            cur = db.execute('''
                UPDATE reports SET
                    client=?, ship=?, contact=?, work=?, location=?, os_number=?,
                    equipment=?, manufacturer=?, model=?, serial_number=?,
                    reported_problem=?, service_performed=?, result=?, pending_issues=?,
                    client_material=?, pronav_material=?, activities=?, equipments=?, city=?, state=?, updated_at=?, status='final'
                WHERE id=?
            ''', [
                report_request.CLIENTE,
                report_request.NAVIO,
                report_request.CONTATO,
                report_request.OBRA,
                report_request.LOCAL,
                report_request.OS,
                report_request.EQUIPAMENTO,
                report_request.FABRICANTE,
                report_request.MODELO,
                report_request.NUMERO_SERIE,
                report_request.PROBLEMA_RELATADO,
                report_request.SERVICO_REALIZADO,
                report_request.RESULTADO,
                report_request.PENDENCIAS,
                report_request.MATERIAL_CLIENTE,
                report_request.MATERIAL_PRONAV,
                json.dumps(atividades_list, ensure_ascii=False),
                json.dumps(equipments_list, ensure_ascii=False),
                report_request.CIDADE or '',
                report_request.ESTADO or '',
                now_iso,
                report_id
            ])
            if cur.rowcount == 0:
                return jsonify({'error': 'Relatório para atualizar não encontrado'}), 404
            db.commit()
            saved_report_id = report_id
        else:
            cur = db.execute('''
                INSERT INTO reports (
                    user_id, client, ship, contact, work, location, os_number,
                    equipment, manufacturer, model, serial_number, reported_problem,
                    service_performed, result, pending_issues, client_material,
                    pronav_material, activities, equipments, city, state, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                report_request.user_id,
                report_request.CLIENTE,
                report_request.NAVIO,
                report_request.CONTATO,
                report_request.OBRA,
                report_request.LOCAL,
                report_request.OS,
                report_request.EQUIPAMENTO,
                report_request.FABRICANTE,
                report_request.MODELO,
                report_request.NUMERO_SERIE,
                report_request.PROBLEMA_RELATADO,
                report_request.SERVICO_REALIZADO,
                report_request.RESULTADO,
                report_request.PENDENCIAS,
                report_request.MATERIAL_CLIENTE,
                report_request.MATERIAL_PRONAV,
                json.dumps(atividades_list, ensure_ascii=False),
                json.dumps(equipments_list, ensure_ascii=False),
                report_request.CIDADE or '',
                report_request.ESTADO or '',
                'final',
                now_iso,
                now_iso
            ])
            db.commit()
            saved_report_id = cur.lastrowid

    # --- PDF parameters (base values) ---
    pdf_buffer = io.BytesIO()
    PAGE_SIZE = letter
    PAGE_W, PAGE_H = PAGE_SIZE

    # margins - we'll allow reduction if necessary
    MARG = 0.35 * inch  # left/right fixed
    preserved_top_margin_base = 0.25 * inch
    preserved_bottom_margin_base = 0.12 * inch

    square_side = 1.18 * inch
    header_row0 = 0.22 * inch
    header_row = 0.26 * inch
    header_height_base = header_row0 + header_row * 3

    sig_header_h_base = 0.24 * inch
    sig_area_h_base = 0.6 * inch
    footer_h_base = 0.28 * inch
    footer_total_height_base = footer_h_base + sig_header_h_base + sig_area_h_base

    # We will attempt to find the largest scale in [min_scale, 1.0] that fits into the page content area.
    MIN_SCALE = 0.40
    MAX_SCALE = 1.0
    # Allow reducing margins progressively (50% to 100% of base)
    margin_reduction_factors = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]

    # helper: style & story builders (must be deterministic and not depend on doc)
    def make_styles(scale=1.0):
        title_sz = max(6.0, BASE_TITLE_FONT_SIZE * scale)
        label_sz = max(6.0, BASE_LABEL_FONT_SIZE * scale)
        value_sz = max(6.0, BASE_VALUE_FONT_SIZE * scale)
        pad_small = max(1, int(max(1, SMALL_PAD * scale)))
        pad_med = max(1, int(max(1, MED_PAD * scale)))
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='TitleCenter', fontName=FONT_BOLD, fontSize=title_sz, alignment=1, leading=max(8, title_sz*1.15)))
        styles.add(ParagraphStyle(name='HeaderLabelPrefill', fontName=FONT_BOLD, fontSize=label_sz, leading=max(7, label_sz*1.15)))
        styles.add(ParagraphStyle(name='HeaderValueFill', fontName=FONT_REGULAR, fontSize=max(5, value_sz-1), leading=max(7, value_sz*1.15)))
        styles.add(ParagraphStyle(name='BodyLabelPrefill', fontName=FONT_BOLD, fontSize=label_sz, leading=max(8, label_sz*1.15)))
        styles.add(ParagraphStyle(name='BodyValueFill', fontName=FONT_REGULAR, fontSize=value_sz, leading=max(9, value_sz*1.15)))
        styles.add(ParagraphStyle(name='td', fontName=FONT_REGULAR, fontSize=value_sz, leading=max(9, value_sz*1.15)))
        styles.add(ParagraphStyle(name='td_left', fontName=FONT_REGULAR, fontSize=value_sz, alignment=0, leading=max(9, value_sz*1.15)))
        styles.add(ParagraphStyle(name='td_right', fontName=FONT_REGULAR, fontSize=value_sz, alignment=2, leading=max(9, value_sz*1.15)))
        styles.add(ParagraphStyle(name='sec_title', fontName=FONT_BOLD, fontSize=label_sz, alignment=0, leading=max(8, label_sz*1.15)))

        # New: style specifically for the "SERVIÇO REALIZADO" section.
        # It uses SERVICE_VALUE_MULTIPLIER to increase font size for this field.
        try:
            mult = float(SERVICE_VALUE_MULTIPLIER)
        except Exception:
            mult = 1.25
        larger_value_sz = max(value_sz, int(value_sz * mult))
        # enforce a minimum readable font for this special field
        larger_value_sz = max(6.0, larger_value_sz)
        styles.add(ParagraphStyle(name='section_value_large', fontName=FONT_REGULAR, fontSize=larger_value_sz, leading=max(9, larger_value_sz*1.15)))

        return styles, pad_small, pad_med

    def build_story(styles, pad_small, pad_med, usable_w):
        story_local = []
        story_local.append(Spacer(1, 0.01 * inch))

        # Equipamento
        first_eq = None
        if equipments_list and len(equipments_list) > 0:
            first_eq = equipments_list[0]
        if not first_eq:
            first_eq = {
                'equipamento': report_request.EQUIPAMENTO or '',
                'fabricante': report_request.FABRICANTE or '',
                'modelo': report_request.MODELO or '',
                'numero_serie': report_request.NUMERO_SERIE or ''
            }

        equip_col = usable_w / 4.0
        equip_cols = [equip_col] * 4
        equip_data = [
            [Paragraph("EQUIPAMENTO", ParagraphStyle(name='eh', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
             Paragraph("FABRICANTE", ParagraphStyle(name='eh', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
             Paragraph("MODELO", ParagraphStyle(name='eh', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
             Paragraph("Nº DE SÉRIE", ParagraphStyle(name='eh', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1))],
            [Paragraph(ensure_upper_safe(first_eq.get('equipamento') or ''), ParagraphStyle(name='ev', fontName=FONT_REGULAR, fontSize=styles['td'].fontSize)),
             Paragraph(ensure_upper_safe(first_eq.get('fabricante') or ''), ParagraphStyle(name='ev', fontName=FONT_REGULAR, fontSize=styles['td'].fontSize)),
             Paragraph(ensure_upper_safe(first_eq.get('modelo') or ''), ParagraphStyle(name='ev', fontName=FONT_REGULAR, fontSize=styles['td'].fontSize)),
             Paragraph(ensure_upper_safe(first_eq.get('numero_serie') or ''), ParagraphStyle(name='ev', fontName=FONT_REGULAR, fontSize=styles['td'].fontSize))],
        ]
        equip_table = Table(equip_data, colWidths=equip_cols, rowHeights=[0.28*inch, 0.2*inch])
        equip_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), GRAY),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('BOX', (0,0), (-1,-1), LINE_WIDTH, colors.black),
            ('INNERGRID', (0,0), (-1,-1), LINE_WIDTH, colors.black),
            ('LEFTPADDING', (0,0), (-1,0), pad_small),
            ('RIGHTPADDING', (0,0), (-1,0), pad_small),
            ('TOPPADDING', (0,0), (-1,0), 0.5),
            ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
            ('LEFTPADDING', (0,1), (-1,1), pad_med),
            ('RIGHTPADDING', (0,1), (-1,1), pad_med),
            ('TOPPADDING', (0,1), (-1,1), 0.5),
            ('BOTTOMPADDING', (0,1), (-1,1), 0.5),
        ]))
        story_local.append(KeepTogether([equip_table]))
        story_local.append(Spacer(1, 0.12 * inch))

        # Sections
        sections = [
            ("PROBLEMA RELATADO/ENCONTRADO", report_request.PROBLEMA_RELATADO),
            ("SERVIÇO REALIZADO", report_request.SERVICO_REALIZADO),
            ("RESULTADO", report_request.RESULTADO),
            ("PENDÊNCIAS", report_request.PENDENCIAS),
            ("MATERIAL FORNECIDO PELO CLIENTE", report_request.MATERIAL_CLIENTE),
            ("MATERIAL FORNECIDO PELA PRONAV", report_request.MATERIAL_PRONAV),
        ]
        for idx, (title, content) in enumerate(sections, start=1):
            title_tbl = Table([[Paragraph(f"{idx}. {title}", styles['sec_title'])]], colWidths=[usable_w])
            title_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), GRAY),
                ('BOX', (0,0), (-1,-1), LINE_WIDTH, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), pad_small),
                ('RIGHTPADDING', (0,0), (-1,-1), pad_small),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ]))

            safe_content = (str(content or '')).replace('\r\n', '\n').replace('\r', '\n')
            safe_content = safe_content.replace('\n', '<br/>')

            # Use larger style only for "SERVIÇO REALIZADO"
            if title.strip().upper().startswith("SERVIÇO REALIZADO"):
                # ensure style exists
                style_for_content = styles.get('section_value_large', styles['td'])
                content_par = Paragraph(safe_content, style_for_content)
            else:
                content_par = Paragraph(safe_content, styles['td'])

            content_tbl = Table([[content_par]], colWidths=[usable_w])
            content_tbl.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), LINE_WIDTH, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), pad_med),
                ('RIGHTPADDING', (0,0), (-1,-1), pad_med),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ]))

            story_local.append(KeepTogether([title_tbl, content_tbl]))
            story_local.append(Spacer(1, 0.12 * inch))

        # Activities table
        if atividades_list:
            proportions = [0.12, 0.12, 0.14, 0.34, 0.06, 0.11, 0.11]
            col_widths = [p * usable_w for p in proportions]

            delta_desc_pts = 20.0
            delta_tec_pts = 10.0
            delta_desc = (delta_desc_pts / 72.0) * inch
            delta_tec = (delta_tec_pts / 72.0) * inch

            idx_desc = 3
            idx_tec1 = 5
            idx_tec2 = 6

            col_widths[idx_desc] = max(0.08 * usable_w, col_widths[idx_desc] - delta_desc)
            col_widths[idx_tec1] = col_widths[idx_tec1] + delta_tec
            col_widths[idx_tec2] = col_widths[idx_tec2] + delta_tec

            total = sum(col_widths)
            diff = total - usable_w
            if abs(diff) > 0.1:
                preferred = 2
                min_allowed = 0.06 * usable_w
                new_val = col_widths[preferred] - diff
                if new_val < min_allowed:
                    remaining = diff - (col_widths[preferred] - min_allowed)
                    col_widths[preferred] = min_allowed
                    col_widths[0] = max(0.06 * usable_w, col_widths[0] - remaining)
                else:
                    col_widths[preferred] = new_val

            header_cells = [
                Paragraph("DATA", ParagraphStyle(name='th', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                Paragraph("HORA", ParagraphStyle(name='th', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                Paragraph("TIPO", ParagraphStyle(name='th', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                Paragraph("DESCRIÇÃO", ParagraphStyle(name='th', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                Paragraph("KM", ParagraphStyle(name='th', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                Paragraph("TÉCNICOS", ParagraphStyle(name='th', fontName=FONT_BOLD, fontSize=styles['sec_title'].fontSize, alignment=1)),
                ''
            ]
            data = [header_cells]

            for at in atividades_list:
                hi = (at.get('HORA_INICIO') or '') or ''
                hf = (at.get('HORA_FIM') or '') or ''
                legacy = (at.get('HORA') or '') or ''
                if hi and hf:
                    hora_comb = f"{str(hi)} às {str(hf)}"
                elif hi:
                    hora_comb = str(hi)
                elif legacy:
                    hora_comb = str(legacy)
                else:
                    hora_comb = ''

                data_br = format_date_br(at.get('DATA') or '')

                safe_desc = ensure_upper_safe(at.get('DESCRICAO') or '')

                data.append([
                    Paragraph(str(data_br or ''), styles['td']),
                    Paragraph(hora_comb, styles['td']),
                    Paragraph(str(at.get('TIPO') or ''), styles['td']),
                    Paragraph(safe_desc, styles['td']),
                    Paragraph(str(at.get('KM') or ''), styles['td']),
                    Paragraph(str(at.get('TECNICO1') or ''), styles['td_left']),
                    Paragraph(str(at.get('TECNICO2') or ''), styles['td_left']),
                ])

            activities_table = Table(data, colWidths=col_widths, repeatRows=1)
            activities_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), GRAY),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
                ('BOX', (0,0), (-1,-1), LINE_WIDTH, colors.black),
                ('GRID', (0,0), (-1,-1), LINE_WIDTH, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('ALIGN', (5,1), (6,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
                ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ]))
            story_local.append(activities_table)

        return story_local

    def estimate_height(flowables, avail_width):
        h = 0.0
        for f in flowables:
            try:
                from reportlab.platypus import Spacer as _Spacer
                if isinstance(f, _Spacer):
                    h += f.height
                    continue
                w, fh = f.wrap(avail_width, PAGE_H)
                h += fh
            except Exception:
                h += 12
        return h

    # --- Attempt to find best scale and margin reduction to fit in first page ---
    best_found = {
        'fit': False,
        'scale': 1.0,
        'top_margin': preserved_top_margin_base,
        'bottom_margin': preserved_bottom_margin_base,
        'usable_w': PAGE_W - 2 * MARG,
        'frame_height': 0.0,
        'story': None,
        'styles': None,
        'pad_small': None,
        'pad_med': None
    }

    original_usable_w = PAGE_W - 2 * MARG

    for m_factor in margin_reduction_factors:
        preserved_top_margin = preserved_top_margin_base * m_factor
        preserved_bottom_margin = preserved_bottom_margin_base * m_factor

        # compute available content rectangle
        usable_w = original_usable_w  # left/right margins fixed
        frame_top = PAGE_H - preserved_top_margin - header_height_base
        frame_bottom = preserved_bottom_margin + footer_total_height_base
        frame_height = frame_top - frame_bottom
        if frame_height <= 0:
            continue

        # Binary search for largest scale in [MIN_SCALE, MAX_SCALE] that fits
        lo = MIN_SCALE
        hi = MAX_SCALE
        found_scale = None
        found_story = None
        found_styles = None
        found_pad_small = None
        found_pad_med = None

        # Quick check: with scale=MAX_SCALE
        styles_test, ps, pm = make_styles(scale=MAX_SCALE)
        story_test = build_story(styles_test, ps, pm, usable_w)
        req = estimate_height(story_test, usable_w)
        if req <= frame_height:
            found_scale = MAX_SCALE
            found_story = story_test
            found_styles = styles_test
            found_pad_small = ps
            found_pad_med = pm
        else:
            # binary search iterations
            for _ in range(12):
                mid = (lo + hi) / 2.0
                styles_mid, ps_mid, pm_mid = make_styles(scale=mid)
                story_mid = build_story(styles_mid, ps_mid, pm_mid, usable_w)
                req_mid = estimate_height(story_mid, usable_w)
                if req_mid <= frame_height:
                    found_scale = mid
                    found_story = story_mid
                    found_styles = styles_mid
                    found_pad_small = ps_mid
                    found_pad_med = pm_mid
                    # try larger
                    lo = mid
                else:
                    # too big, try smaller
                    hi = mid
                # stop early if hi-lo small
                if (hi - lo) < 0.005:
                    break

        if found_scale is not None:
            # store best if larger scale than previous found
            if not best_found['fit'] or found_scale > best_found['scale']:
                best_found.update({
                    'fit': True,
                    'scale': found_scale,
                    'top_margin': preserved_top_margin,
                    'bottom_margin': preserved_bottom_margin,
                    'usable_w': usable_w,
                    'frame_height': frame_height,
                    'story': found_story,
                    'styles': found_styles,
                    'pad_small': found_pad_small,
                    'pad_med': found_pad_med
                })
            # we prefer larger margin factor (less reduction) if same scale: break
            break

    # If nothing fit with min scale even after margin reductions, pick the minimal scale & last margin attempt to allow multi-page
    if not best_found['fit']:
        # pick the smallest scale and last attempted margins
        last_m_factor = margin_reduction_factors[-1]
        preserved_top_margin = preserved_top_margin_base * last_m_factor
        preserved_bottom_margin = preserved_bottom_margin_base * last_m_factor
        usable_w = original_usable_w
        frame_top = PAGE_H - preserved_top_margin - header_height_base
        frame_bottom = preserved_bottom_margin + footer_total_height_base
        frame_height = max(1.0 * inch, frame_top - frame_bottom)
        styles_min, ps_min, pm_min = make_styles(scale=MIN_SCALE)
        story_min = build_story(styles_min, ps_min, pm_min, usable_w)
        best_found.update({
            'fit': False,
            'scale': MIN_SCALE,
            'top_margin': preserved_top_margin,
            'bottom_margin': preserved_bottom_margin,
            'usable_w': usable_w,
            'frame_height': frame_height,
            'story': story_min,
            'styles': styles_min,
            'pad_small': ps_min,
            'pad_med': pm_min
        })
        logger.info("Não foi possível encaixar tudo em 1 página mesmo em min-scale; usaremos scale mínimo %.2f e permitiremos múltiplas páginas.", MIN_SCALE)
    else:
        logger.info("Conteúdo caberá na primeira página com scale=%.3f (margens: top=%.2fmm bottom=%.2fmm).",
                    best_found['scale'], best_found['top_margin']*25.4, best_found['bottom_margin']*25.4)

    # Now build actual doc with chosen margins and story/styles
    chosen_top_margin = best_found['top_margin']
    chosen_bottom_margin = best_found['bottom_margin']
    chosen_styles = best_found['styles']
    chosen_pad_small = best_found['pad_small']
    chosen_pad_med = best_found['pad_med']
    story = best_found['story']
    usable_w = best_found['usable_w']
    frame_top = PAGE_H - chosen_top_margin - header_height_base
    frame_bottom = chosen_bottom_margin + footer_total_height_base
    frame_height = max(1.0 * inch, frame_top - frame_bottom)

    doc = BaseDocTemplate(pdf_buffer, pagesize=PAGE_SIZE,
                          leftMargin=MARG, rightMargin=MARG,
                          topMargin=chosen_top_margin, bottomMargin=chosen_bottom_margin)

    content_frame = Frame(MARG, frame_bottom, usable_w, frame_height,
                          leftPadding=6, rightPadding=6, topPadding=6, bottomPadding=6, id='content_frame')

    # Prepare drawing functions that capture chosen_top_margin etc.
    lp = app.config.get('LOGO_PATH') or DEFAULT_LOGO

    def draw_header(canvas, doc_local):
        canvas.saveState()
        canvas.setLineJoin(1)
        canvas.setLineWidth(LINE_WIDTH)
        canvas.setStrokeColor(colors.black)

        left_x = MARG
        right_x = MARG + usable_w
        top_y = PAGE_H - doc_local.topMargin
        bottom_y = top_y - header_height_base

        sep_x1 = left_x + square_side
        sep_x2 = left_x + square_side + (usable_w - 2 * square_side if usable_w > 2 * square_side else usable_w - square_side)

        canvas.setFillColor(GRAY)
        canvas.rect(sep_x1, top_y - header_row0, (sep_x2 - sep_x1), header_row0, stroke=0, fill=1)
        canvas.setFillColor(colors.black)

        eps = 0.4
        canvas.line(left_x - eps, top_y + eps, right_x + eps, top_y + eps)
        canvas.line(left_x - eps, bottom_y - eps, right_x + eps, bottom_y - eps)
        canvas.line(left_x - eps, bottom_y - eps, left_x - eps, top_y + eps)
        canvas.line(right_x + eps, bottom_y - eps, right_x + eps, top_y + eps)

        canvas.line(sep_x1, bottom_y - eps, sep_x1, top_y + eps)
        canvas.line(sep_x2, bottom_y - eps, sep_x2, top_y + eps)

        y_top = top_y
        y_row0 = y_top - header_row0
        y_row1 = y_row0 - header_row
        y_row2 = y_row1 - header_row
        y_row3 = y_row2 - header_row

        canvas.line(sep_x1, y_row0, sep_x2, y_row0)
        canvas.line(sep_x1, y_row1, sep_x2, y_row1)
        canvas.line(sep_x1, y_row2, sep_x2, y_row2)
        canvas.line(sep_x1, y_row3, sep_x2, y_row3)

        inner_label_w = 0.7 * inch
        inner_val_w_left = 1.6 * inch * 1.25
        inner_label_w2 = 0.6 * inch
        total_center = sep_x2 - sep_x1

        delta_pts = 75.0
        delta_inch = (delta_pts / 72.0) * inch
        inner_val_w_left = inner_val_w_left + delta_inch

        right_available = total_center - (inner_label_w + inner_val_w_left + inner_label_w2)
        min_right = 0.6 * inch
        if right_available < min_right:
            shortage = min_right - right_available
            inner_val_w_left = max(0.9 * inch, inner_val_w_left - shortage)
            right_available = min_right
        inner_val_w_right = right_available

        col0_w, col1_w, col2_w, col3_w = inner_label_w, inner_val_w_left, inner_label_w2, inner_val_w_right
        col_x0 = sep_x1
        col_x1 = col_x0 + col0_w
        col_x2 = col_x1 + col1_w
        col_x3 = col_x2 + col2_w
        col_x4 = col_x3 + col3_w

        canvas.line(col_x1, y_row3, col_x1, y_row0)
        canvas.line(col_x2, y_row3, col_x2, y_row0)
        canvas.line(col_x3, y_row3, col_x3, y_row0)

        canvas.setFont(FONT_BOLD, BASE_TITLE_FONT_SIZE * best_found['scale'])
        canvas.drawCentredString((sep_x1 + sep_x2) / 2.0, y_top - header_row0 / 2.0 - 3, "RELATÓRIO DE SERVIÇO")

        try:
            if lp and os.path.exists(lp):
                img_reader = ImageReader(lp)
                iw, ih = img_reader.getSize()
                pad = 6.0
                max_w = max(1.0, square_side - 2 * pad)
                max_h = max(1.0, header_height_base - 2 * pad)
                ratio_w = max_w / iw if iw > 0 else 1.0
                ratio_h = max_h / ih if ih > 0 else 1.0
                ratio = min(1.0, ratio_w, ratio_h)
                logo_w = iw * ratio
                logo_h = ih * ratio
                logo_w = logo_w + 3.0
                logo_h = max(1.0, logo_h - 3.0)
                if logo_w > max_w:
                    factor = max_w / logo_w
                    logo_w = logo_w * factor
                    logo_h = logo_h * factor
                if logo_h > max_h:
                    factor = max_h / logo_h
                    logo_w = logo_w * factor
                    logo_h = logo_h * factor
                logo_x = left_x + (square_side - logo_w) / 2.0
                logo_y = bottom_y + (header_height_base - logo_h) / 2.0
                canvas.drawImage(img_reader, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
        except Exception as ie:
            logger.info("Erro ao desenhar logo (final): %s", ie)

        contact_x_center = sep_x2 + (square_side / 2.0)
        title_text = "PRONAV MARINE"
        title_font_size = max(7, int(9 * best_found['scale']))
        detail_font_size = max(5, int(6 * best_found['scale']))
        detail_lines = ["Tel.: (22) 2141-2458", "Cel.: (22) 99221-1893", "service@pronav.com.br", "www.pronav.com.br"]
        detail_leading = detail_font_size * 1.2
        total_height = title_font_size + 4 + (len(detail_lines) * detail_leading)
        square_top = top_y
        square_bottom = bottom_y
        mid_y = (square_top + square_bottom) / 2.0
        y = mid_y + total_height / 2.0

        canvas.setFont(FONT_BOLD, title_font_size)
        canvas.setFillColor(colors.HexColor('#005BD0'))
        canvas.drawCentredString(contact_x_center, y - (title_font_size * 0.3), title_text)

        canvas.setFillColor(colors.black)
        canvas.setFont(FONT_REGULAR, detail_font_size)
        y = y - (title_font_size * 0.7) - 4
        for i, ln in enumerate(detail_lines):
            canvas.drawCentredString(contact_x_center, y - i * detail_leading, ln)

        labels_left = ["NAVIO:", "CONTATO:", "LOCAL:"]
        values_left = [
            ensure_upper_safe(report_request.NAVIO or ''),
            ensure_upper_safe(report_request.CONTATO or ''),
            ' - '.join(filter(None, [ensure_upper_safe(report_request.LOCAL or ''), ensure_upper_safe(report_request.CIDADE or ''), ensure_upper_safe(report_request.ESTADO or '')]))
        ]
        labels_right = ["CLIENTE:", "OBRA:", "OS:"]
        values_right = [ensure_upper_safe(report_request.CLIENTE or ''), ensure_upper_safe(report_request.OBRA or ''), ensure_upper_safe(report_request.OS or '')]

        rows_y = [y_row0, y_row1, y_row2, y_row3]
        for i in range(3):
            top = rows_y[i]
            bottom = rows_y[i + 1]
            center_y = (top + bottom) / 2.0 - 4
            canvas.setFont(FONT_BOLD, max(6, int(BASE_LABEL_FONT_SIZE * best_found['scale'])))
            canvas.setFillColor(colors.black)
            canvas.drawString(col_x0 + 4, center_y, labels_left[i])
            val_font = max(6, int(BASE_VALUE_FONT_SIZE * best_found['scale']))
            if labels_left[i].startswith("LOCAL"):
                val_font = max(5, val_font - 1)
            canvas.setFont(FONT_REGULAR, val_font)
            canvas.drawString(col_x1 + 4, center_y, values_left[i])
            canvas.setFont(FONT_BOLD, max(6, int(BASE_LABEL_FONT_SIZE * best_found['scale'])))
            canvas.drawString(col_x2 + 4, center_y, labels_right[i])
            canvas.setFont(FONT_REGULAR, val_font)
            canvas.drawString(col_x3 + 4, center_y, values_right[i])

        canvas.restoreState()

    def draw_signatures_and_footer(canvas, doc_local):
        canvas.saveState()
        canvas.setLineWidth(LINE_WIDTH)
        canvas.setStrokeColor(colors.black)

        left = MARG
        right = MARG + usable_w
        mid = left + usable_w / 2.0

        bottom_margin = doc_local.bottomMargin
        sig_header_h_local = sig_header_h_base
        sig_area_h_local = sig_area_h_base
        footer_h_local = footer_h_base
        footer_y = bottom_margin

        canvas.setFillColor(GRAY)
        canvas.rect(left, footer_y, usable_w, footer_h_local, stroke=0, fill=1)
        canvas.setFillColor(colors.black)
        canvas.setFont(FONT_BOLD, max(6, int(BASE_VALUE_FONT_SIZE * best_found['scale'])))
        canvas.drawCentredString(left + usable_w / 2.0, footer_y + footer_h_local / 2.0 - 2, "O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE")

        sig_bottom = footer_y + footer_h_local
        sig_total_h_local = sig_area_h_local + sig_header_h_local
        canvas.setFillColor(GRAY)
        canvas.rect(left, sig_bottom + sig_area_h_local, usable_w / 2.0, sig_header_h_local, stroke=0, fill=1)
        canvas.rect(mid, sig_bottom + sig_area_h_local, usable_w / 2.0, sig_header_h_local, stroke=0, fill=1)
        canvas.setFillColor(colors.black)
        canvas.setFont(FONT_BOLD, max(6, int(BASE_LABEL_FONT_SIZE * best_found['scale'])))
        canvas.drawCentredString(left + (usable_w / 4.0), sig_bottom + sig_area_h_local + sig_header_h_local / 2.0 - 2, "ASSINATURA DO COMANDANTE")
        canvas.drawCentredString(mid + (usable_w / 4.0), sig_bottom + sig_area_h_local + sig_header_h_local / 2.0 - 2, "ASSINATURA DO TÉCNICO")

        canvas.setLineWidth(LINE_WIDTH)
        canvas.rect(left, sig_bottom, usable_w / 2.0, sig_total_h_local, stroke=1, fill=0)
        canvas.rect(mid, sig_bottom, usable_w / 2.0, sig_total_h_local, stroke=1, fill=0)
        eps = 0.4
        canvas.line(mid, sig_bottom - eps, mid, sig_bottom + sig_total_h_local + eps)

        canvas.restoreState()

    def on_page_template(canvas, doc_local):
        draw_header(canvas, doc_local)
        draw_signatures_and_footer(canvas, doc_local)
        try:
            canvas.saveState()
            canvas.setFont(FONT_REGULAR, max(6, int(7 * best_found['scale'])))
            canvas.setFillColor(colors.HexColor('#666666'))
            y_page = frame_bottom + (0.06 * inch)
            canvas.drawCentredString(PAGE_W / 2.0, y_page, f"PÁGINA {doc_local.page}")
            canvas.restoreState()
        except Exception as e:
            logger.info("Erro ao desenhar numeração de página: %s", e)

    page_template = PageTemplate(id='default', frames=[content_frame], onPage=on_page_template)
    doc.addPageTemplates([page_template])

    # Build PDF (story already tailored to scale and will fit first page if possible)
    doc.build(story)
    pdf_buffer.seek(0)

    # filename
    equip_name_for_file = ''
    try:
        if equipments_list and len(equipments_list) > 0:
            e0 = equipments_list[0]
            if isinstance(e0, dict):
                equip_name_for_file = e0.get('equipamento') or e0.get('Equipamento') or ''
            else:
                equip_name_for_file = str(e0)
        if not equip_name_for_file:
            equip_name_for_file = report_request.EQUIPAMENTO or ''
        equip_name_for_file = str(equip_name_for_file).strip().replace(' ', '_').replace('/', '-')
    except Exception:
        equip_name_for_file = ''

    safe_ship = (report_request.NAVIO or 'Geral').replace(' ', '_')
    date_str = datetime.utcnow().strftime('%Y%m%d')
    filename = f"RS_{date_str}_{safe_ship}"
    if equip_name_for_file:
        filename = f"{filename}_{equip_name_for_file}"
    filename = f"{filename}.pdf"

    resp: Response = send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    try:
        resp.headers['X-Report-Id'] = str(saved_report_id)
    except Exception:
        logger.info("Não foi possível setar header X-Report-Id")
    return resp

# Initialize DB on import/startup so WSGI servers have DB ready
try:
    init_db()
except Exception as e:
    logger.exception("Falha ao inicializar DB: %s", e)

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')
