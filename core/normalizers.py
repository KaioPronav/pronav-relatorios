# core/normalizers.py
import json
import re
from typing import Dict, Tuple, Any, List, Optional
from datetime import datetime

TIME_SEPARATORS = ['às', 'as', 'AS', 'ÀS', '-', '–', '—', '/', ' a ']  # possíveis separadores de período

def _pick_first(d: Dict[str, Any], keys: List[str], default=''):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def _safe_str(x: Any) -> str:
    try:
        return str(x or '')
    except Exception:
        return ''

def _normalize_time_token(tok: str) -> Optional[str]:
    """
    Normaliza um token de tempo para 'HH:MM' quando possível.
    Aceita formatos: '8:30', '08:30', '8h30', '0830', '8' -> '08:00'
    """
    if not tok:
        return None
    s = _safe_str(tok).strip()
    if not s:
        return None

    s = s.replace('h', ':').replace('H', ':')
    s = s.replace('.', ':')
    s = re.sub(r'\s+', '', s)

    m = re.match(r'^(\d{1,2}):?(\d{0,2})$', s)
    if m:
        hh = int(m.group(1))
        mm = m.group(2)
        mm = int(mm) if mm else 0
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"
        if 0 <= hh <= 23:
            return f"{hh:02d}:00"

    m2 = re.match(r'^(\d{2})(\d{2})$', s)
    if m2:
        hh = int(m2.group(1)); mm = int(m2.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"

    if re.match(r'^\d{1,2}$', s):
        hh = int(s)
        if 0 <= hh <= 23:
            return f"{hh:02d}:00"

    return None

def _parse_time_range(s: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna (start, end) normalizados em 'HH:MM' quando possível.
    """
    if not s:
        return None, None
    text = _safe_str(s).strip()
    for sep in TIME_SEPARATORS:
        if sep in text:
            parts = [p.strip() for p in text.split(sep, 1)]
            if len(parts) >= 2:
                start = _normalize_time_token(parts[0])
                end = _normalize_time_token(parts[1])
                return start, end
    single = _normalize_time_token(text)
    return single, None

def _try_parse_datetime(value: Any) -> Optional[datetime]:
    """
    Tenta interpretar várias formas de date/datetime e retorna datetime ou None.
    """
    if value is None:
        return None
    v = _safe_str(value).strip()
    if not v:
        return None

    # timestamps numéricos (10 ou 13 dígitos)
    if re.fullmatch(r'^\d{10,13}$', v):
        try:
            if len(v) == 13:
                ts = int(v) / 1000.0
            else:
                ts = int(v)
            return datetime.utcfromtimestamp(ts)
        except Exception:
            pass

    # ISO / fromisoformat
    try:
        return datetime.fromisoformat(v)
    except Exception:
        pass

    fmts = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]
    for f in fmts:
        try:
            return datetime.strptime(v, f)
        except Exception:
            continue

    # fallback: procurar por pattern de data na string
    m = re.search(r'(\d{2}/\d{2}/\d{4})', v)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d/%m/%Y")
        except Exception:
            pass
    m2 = re.search(r'(\d{4}-\d{2}-\d{2})', v)
    if m2:
        try:
            return datetime.strptime(m2.group(1), "%Y-%m-%d")
        except Exception:
            pass

    return None

def _format_date_br(dt: datetime) -> str:
    try:
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ''

def _sanitize_description(descricao: str, origem: str, destino: str, motivo: str, tipo: str) -> str:
    """
    Remove repetição de origem/destino e garante que Motivo apareça se necessário.
    NÃO remove o MOTIVO.
    """
    s = _safe_str(descricao).strip()
    for piece in (origem, destino):
        if piece:
            try:
                s = s.replace(_safe_str(piece), '')
            except Exception:
                pass
    s = ' '.join(s.split())

    motivo_str = _safe_str(motivo).strip()
    if motivo_str:
        if not s:
            s = f"Motivo: {motivo_str}"
        else:
            if motivo_str.lower() not in s.lower():
                s = f"{s} - Motivo: {motivo_str}"
    return s

def normalize_activity(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza uma entrada de atividade. Mantém compatibilidade com Pydantic
    esperando DATA como string (DD/MM/YYYY). Adiciona DATA_DT com datetime quando possível.
    """
    a: Dict[str, Any] = {}

    # DATA: tentamos obter datetime; armazenamos string em a['DATA'] (compatível com Pydantic)
    raw_date = _pick_first(raw, ['DATA', 'data', 'Data', 'DATA_HORA', 'data_hora', 'datetime', 'timestamp', 'created_at'])
    parsed_dt = _try_parse_datetime(raw_date)
    if parsed_dt:
        a['DATA_DT'] = parsed_dt                 # datetime útil internamente
        a['DATA'] = _format_date_br(parsed_dt)   # string compatível com Pydantic
    else:
        a['DATA_DT'] = None
        a['DATA'] = _safe_str(_pick_first(raw, ['DATA', 'data', 'Data'])) or ''

    # HORA / HORA_INICIO / HORA_FIM
    hora_legacy = _pick_first(raw, ['HORA', 'hora', 'Hora']) or ''
    a['HORA'] = _safe_str(hora_legacy).strip() or ''

    h_inicio = _pick_first(raw, ['HORA_INICIO', 'hora_inicio', 'horaInicio', 'HORAINICIO']) or ''
    h_fim = _pick_first(raw, ['HORA_FIM', 'hora_fim', 'horaFim', 'HORAFIM']) or ''
    a['HORA_INICIO'] = _safe_str(h_inicio).strip() or ''
    a['HORA_FIM'] = _safe_str(h_fim).strip() or ''

    if (not a['HORA_INICIO'] and not a['HORA_FIM']) and isinstance(hora_legacy, str) and hora_legacy.strip():
        start, end = _parse_time_range(hora_legacy.strip())
        if start:
            a['HORA_INICIO'] = start
        if end:
            a['HORA_FIM'] = end
        if not a['HORA_INICIO'] and not a['HORA_FIM']:
            single = _normalize_time_token(hora_legacy.strip())
            if single:
                a['HORA_INICIO'] = single

    if a['HORA_INICIO']:
        t = _normalize_time_token(a['HORA_INICIO'])
        a['HORA_INICIO'] = t or a['HORA_INICIO']
    if a['HORA_FIM']:
        t = _normalize_time_token(a['HORA_FIM'])
        a['HORA_FIM'] = t or a['HORA_FIM']

    if a['HORA_INICIO'] and a['HORA_FIM']:
        a['HORA'] = f"{a['HORA_INICIO']} às {a['HORA_FIM']}"
    else:
        if (not a.get('HORA')) and a['HORA_INICIO']:
            a['HORA'] = a['HORA_INICIO']

    # demais campos
    a['TIPO'] = _safe_str(_pick_first(raw, ['TIPO', 'tipo'])) or ''
    a['KM'] = _safe_str(_pick_first(raw, ['KM', 'km'])) or ''
    raw_desc = _pick_first(raw, ['DESCRICAO', 'descricao', 'Descricao', 'description']) or ''
    a['MOTIVO'] = _safe_str(_pick_first(raw, ['MOTIVO', 'motivo'])) or ''
    a['ORIGEM'] = _safe_str(_pick_first(raw, ['ORIGEM', 'origem'])) or ''
    a['DESTINO'] = _safe_str(_pick_first(raw, ['DESTINO', 'destino'])) or ''

    a['DESCRICAO'] = _sanitize_description(raw_desc, a['ORIGEM'], a['DESTINO'], a['MOTIVO'], a['TIPO'])

    # TECNICOS: manter nomes COMPLETOS, sem abreviação
    t1 = _pick_first(raw, ['TECNICO1', 'tecnico1', 'tecnico_1', 'TECNICO', 'tecnico'])
    t2 = _pick_first(raw, ['TECNICO2', 'tecnico2', 'tecnico_2'])
    a['TECNICO1'] = _safe_str(t1).strip()
    a['TECNICO2'] = _safe_str(t2).strip()
    a['TECNICO1_FULL'] = a['TECNICO1']
    a['TECNICO2_FULL'] = a['TECNICO2']

    # KM_BLOQUEADO normalização booleana
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

def ensure_upper_safe(s):
    try:
        return str(s or '').upper()
    except Exception:
        return str(s or '')
