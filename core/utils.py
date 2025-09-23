from dateutil import parser as date_parser

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