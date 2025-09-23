import json
from typing import Dict, Any, List

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

def ensure_upper_safe(s):
    try:
        return str(s or '').upper()
    except Exception:
        return str(s or '')