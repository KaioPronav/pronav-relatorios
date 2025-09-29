# core/pdf/styles_builder.py
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def make_styles(config, font_regular, font_bold, small_pad, med_pad, base_title_sz, base_label_sz, base_value_sz):
    # Repete a lógica do arquivo original: calcula tamanhos e cria estilos com os nomes esperados.
    base_title = max(6.0, base_title_sz)
    base_label = max(6.0, base_label_sz)
    base_value = max(6.0, base_value_sz)

    try:
        resp_mult = float(getattr(config, 'RESPONSE_VALUE_MULTIPLIER', 1.0))
    except Exception:
        resp_mult = 1.0
    try:
        label_mult = float(getattr(config, 'LABEL_VALUE_MULTIPLIER', 1.0))
    except Exception:
        label_mult = 1.0

    response_sz = max(8.2, float(base_value) * resp_mult)
    label_sz = max(8.2, float(base_label) * label_mult)
    title_sz = max(8.2, base_title * 1.0)

    pad_small = max(0, int(max(0, small_pad)))
    pad_med = max(0, int(max(0, med_pad)))

    styles = getSampleStyleSheet()

    def add_or_update(name, **kwargs):
        if name in styles:
            s = styles[name]
            for k, v in kwargs.items():
                setattr(s, k, v)
        else:
            styles.add(ParagraphStyle(name=name, **kwargs))

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
    add_or_update('td_right', fontName=font_regular, fontSize=response_sz, alignment=0, leading=max(7, response_sz * 1.06), spaceBefore=0, spaceAfter=0)
    add_or_update('sec_title', fontName=font_bold, fontSize=label_sz, alignment=0, leading=max(7, label_sz * 1.05), spaceAfter=2, spaceBefore=2)

    try:
        service_mult = float(getattr(config, 'SERVICE_VALUE_MULTIPLIER', 1.20))
    except Exception:
        service_mult = 1.20
    svc_sz = max(response_sz, int(response_sz * service_mult))
    svc_sz = max(8.2, svc_sz)
    add_or_update('section_value_large', fontName=font_regular, fontSize=svc_sz, leading=max(8, svc_sz * 1.06), alignment=0, spaceAfter=0, spaceBefore=0)

    return styles, pad_small, pad_med
