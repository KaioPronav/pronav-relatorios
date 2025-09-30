# core/pdf/styles_builder.py
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def make_styles(config, font_regular, font_bold, small_pad, med_pad, base_title_sz, base_label_sz, base_value_sz):
    """
    Cria e retorna (styles, pad_small, pad_med).
    Tudo relativo às seções pode ser controlado via config (globalmente ou por-seção).
    """

    # --- helper para conversões seguras ---
    def _num(x, fallback):
        try:
            if x is None:
                return float(fallback)
            return float(x)
        except Exception:
            return float(fallback)

    # bases com limites
    base_title = max(getattr(config, 'MIN_FONT_SIZE', 6.0), _num(base_title_sz, 8.0))
    base_label = max(getattr(config, 'MIN_FONT_SIZE', 6.0), _num(base_label_sz, 8.0))
    base_value = max(getattr(config, 'MIN_FONT_SIZE', 6.0), _num(base_value_sz, 7.0))

    resp_mult = _num(getattr(config, 'RESPONSE_VALUE_MULTIPLIER', 1.0), 1.0)
    label_mult = _num(getattr(config, 'LABEL_VALUE_MULTIPLIER', 1.0), 1.0)

    response_sz = max(getattr(config, 'MIN_FONT_SIZE', 6.0),
                      min(getattr(config, 'MAX_FONT_SIZE', 72.0), float(base_value) * float(resp_mult)))

    label_sz = max(getattr(config, 'MIN_FONT_SIZE', 6.0),
                   min(getattr(config, 'MAX_FONT_SIZE', 72.0), float(base_label) * float(label_mult)))

    title_sz = max(getattr(config, 'MIN_FONT_SIZE', 6.0),
                   min(getattr(config, 'MAX_FONT_SIZE', 72.0), float(base_title)))

    pad_small = max(0, int(small_pad if small_pad is not None else getattr(config, 'SMALL_PAD', 2)))
    pad_med = max(0, int(med_pad if med_pad is not None else getattr(config, 'MED_PAD', 3)))

    styles = getSampleStyleSheet()

    def add_or_update(name, **kwargs):
        if name in styles:
            s = styles[name]
            for k, v in kwargs.items():
                setattr(s, k, v)
        else:
            styles.add(ParagraphStyle(name=name, **kwargs))

    # estilos base
    add_or_update('TitleCenter',
        fontName=font_bold,
        fontSize=title_sz,
        alignment=1,
        leading=max(8, title_sz * 1.15)
    )

    add_or_update('label',
        fontName=font_bold,
        fontSize=label_sz,
        leading=max(7, label_sz * 1.05),
        alignment=0,
        spaceAfter=2,
        spaceBefore=2
    )

    add_or_update('response',
        fontName=font_regular,
        fontSize=response_sz,
        leading=max(7, response_sz * 1.06),
        alignment=0,
        wordWrap='CJK',
        spaceAfter=0,
        spaceBefore=0
    )

    add_or_update('label_center',
        fontName=font_bold,
        fontSize=label_sz,
        leading=max(7, label_sz * 1.05),
        alignment=1,
        spaceAfter=2,
        spaceBefore=2
    )

    add_or_update('response_center',
        fontName=font_regular,
        fontSize=response_sz,
        leading=max(7, response_sz * 1.06),
        alignment=1,
        spaceAfter=0,
        spaceBefore=0
    )

    add_or_update('td', fontName=font_regular, fontSize=response_sz, leading=max(7, response_sz * 1.06), alignment=0, spaceBefore=0, spaceAfter=0)
    add_or_update('td_left', fontName=font_regular, fontSize=response_sz, alignment=0, leading=max(7, response_sz * 1.06), spaceBefore=0, spaceAfter=0)
    add_or_update('td_right', fontName=font_regular, fontSize=response_sz, alignment=2, leading=max(7, response_sz * 1.06), spaceBefore=0, spaceAfter=0)
    add_or_update('sec_title', fontName=font_bold, fontSize=label_sz, alignment=0, leading=max(7, label_sz * 1.05), spaceAfter=2, spaceBefore=2)

    # --- helper para calcular tamanho por-seção ---
    def _section_size(section_key):
        """
        section_key: str, ex: 'RESULT' or 'SERVICO' or 'PENDENCIAS' or 'MATERIAL'
        Procura por configurações específicas em config com prefix SECTION_<KEY>_*
        Se não existir, usa as configurações globais SECTION_*
        """
        # Global defaults
        use_resp = bool(getattr(config, 'SECTION_USE_RESPONSE_SIZE', True))
        global_mult = _num(getattr(config, 'SECTION_SIZE_MULTIPLIER', 1.0), 1.0)
        global_override = _num(getattr(config, 'SECTION_FONT_SIZE_OVERRIDE', -1.0), -1.0)
        global_font = getattr(config, 'SECTION_FONT_NAME', '') or ''

        # Specific keys mapping
        key_prefix = None
        if section_key == 'RESULTADO':
            key_prefix = 'SECTION_RESULT'
        elif section_key == 'SERVICO':
            key_prefix = 'SECTION_SERVICO'
        elif section_key == 'PENDENCIAS':
            key_prefix = 'SECTION_PENDENCIAS'
        elif section_key == 'MATERIAL':
            key_prefix = 'SECTION_MATERIAL'
        else:
            key_prefix = None

        # read per-section values if available (None -> inherit)
        if key_prefix:
            use_resp_sec = getattr(config, f'{key_prefix}_USE_RESPONSE_SIZE', None)
            size_mult_sec = getattr(config, f'{key_prefix}_SIZE_MULTIPLIER', None)
            override_sec = getattr(config, f'{key_prefix}_FONT_SIZE_OVERRIDE', None)
            font_sec = getattr(config, f'{key_prefix}_FONT_NAME', None)
        else:
            use_resp_sec = size_mult_sec = override_sec = font_sec = None

        # decide effective settings
        use_resp_eff = use_resp_sec if use_resp_sec is not None else use_resp
        mult_eff = _num(size_mult_sec, global_mult) if size_mult_sec is not None else global_mult
        override_eff = _num(override_sec, global_override) if override_sec is not None else global_override
        font_eff = ''
        if font_sec is not None:
            font_eff = font_sec or ''
        else:
            font_eff = global_font or ''

        # compute size with priority: override > use_resp*mult > fallback service_mult
        if override_eff and float(override_eff) > 0:
            svc = max(getattr(config, 'MIN_FONT_SIZE', 6.0), float(override_eff))
        elif use_resp_eff:
            svc = max(getattr(config, 'MIN_FONT_SIZE', 6.0), float(response_sz) * float(mult_eff))
        else:
            svc_mult = _num(getattr(config, 'SERVICE_VALUE_MULTIPLIER', 1.0), 1.0)
            svc = max(getattr(config, 'MIN_FONT_SIZE', 6.0), float(response_sz) * float(svc_mult))

        svc = max(8.2, svc)
        # resolve font name: section font or default regular
        section_font = font_eff if font_eff else font_regular
        return section_font, svc

    # compute each section style using helper
    serv_font, serv_sz = _section_size('SERVICO')
    res_font, res_sz = _section_size('RESULTADO')
    pend_font, pend_sz = _section_size('PENDENCIAS')
    mat_font, mat_sz = _section_size('MATERIAL')

    # register styles (nome principal + aliases)
    add_or_update('section_value_large', fontName=serv_font, fontSize=serv_sz, leading=max(8, serv_sz * 1.06), alignment=0, spaceAfter=0, spaceBefore=0)

    add_or_update('servico_continuacao', fontName=serv_font, fontSize=serv_sz, leading=max(8, serv_sz * 1.06))
    add_or_update('resultado', fontName=res_font, fontSize=res_sz, leading=max(8, res_sz * 1.06))
    add_or_update('pendencias', fontName=pend_font, fontSize=pend_sz, leading=max(8, pend_sz * 1.06))
    add_or_update('material_fornecido_cliente', fontName=mat_font, fontSize=mat_sz, leading=max(8, mat_sz * 1.06))

    # muted helper
    add_or_update('muted', fontName=font_regular, fontSize=max(6, int(response_sz * 0.9)), leading=max(7, response_sz * 0.95), textColor=colors.grey)

    return styles, pad_small, pad_med
