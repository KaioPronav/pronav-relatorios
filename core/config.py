# config.py
import os

class Config:
    """
    Arquivo central de configuração — TODOS os parâmetros de fonte/tamanho usados
    no relatório devem ser ajustados aqui.
    Edite diretamente os valores abaixo para alterar o visual dos PDFs.
    """

    # -------------------------
    # Diretórios / caminhos
    # -------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Caminho padrão para logo e fontes (ajuste se necessário)
    LOGO_PATH = os.path.join(BASE_DIR, 'static', 'images', 'logo.png')

    # -------------------------
    # Fontes (use nomes registrados nas TTF ou nomes padrão)
    # -------------------------
    # Caminhos para arquivos .ttf (use caminho absoluto ou relativo a BASE_DIR)
    FONT_REGULAR_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'arial.ttf')
    FONT_BOLD_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'arialbd.ttf')

    # Nomes usados no registro (quando registrar fonte TTF, escolha o nome)
    FONT_REGULAR_NAME = 'Arial'
    FONT_BOLD_NAME = 'Arial-Bold'

    # -------------------------
    # Tamanhos base (pontos)
    # -------------------------
    # Altere esses valores para ajustar globalmente os tamanhos do relatório.
    TITLE_FONT_SIZE = 7.0      # usado em títulos principais
    LABEL_FONT_SIZE = 8.2      # usado em labels/secções curtas
    VALUE_FONT_SIZE = 8.2      # usado para campos de resposta (valor/texto)

    # Limites de segurança (garante legibilidade)
    MIN_FONT_SIZE = 6.0
    MAX_FONT_SIZE = 72.0

    # -------------------------
    # Multiplicadores (ajustes relativos)
    # -------------------------
    # RESPONSE_VALUE_MULTIPLIER: multiplicador aplicado ao VALUE_FONT_SIZE para campos 'response'
    RESPONSE_VALUE_MULTIPLIER = 1.0

    # LABEL_VALUE_MULTIPLIER: multiplicador aplicado ao LABEL_FONT_SIZE
    LABEL_VALUE_MULTIPLIER = 1.0

    # SERVICE_VALUE_MULTIPLIER: comportamento legado; se SECTION_USE_RESPONSE_SIZE estiver True,
    # o size das seções obedecerá SECTION_SIZE_MULTIPLIER. Mantido para compatibilidade.
    SERVICE_VALUE_MULTIPLIER = 1.0

    # -------------------------
    # Header font control (TOTALMENTE configurável)
    # Se o valor for > 0, será usado como tamanho absoluto (pts).
    # Se for <= 0, será calculado a partir do BASE_TITLE_FONT_SIZE (padrão passado pelo PDFService).
    # -------------------------
    # Título central do header ("RELATÓRIO DE SERVIÇO")
    HEADER_TITLE_FONT_SIZE = -1.0   # override absoluto (pts). -1 => usar base.
    HEADER_TITLE_MIN_SIZE = 9.0     # mínimo visual caso seja herdado da base

    # linha de contato (texto pequeno central acima do header)
    HEADER_CONTACT_FONT_SIZE = -1.0
    HEADER_CONTACT_MIN_SIZE = 7.0

    # labels do header (NAVIO:, CONTATO:, LOCAL:, CLIENTE, OBRA:, OS:)
    HEADER_LABEL_FONT_SIZE = -1.0
    HEADER_LABEL_MIN_SIZE = 8.0

    # valores ao lado dos labels (texto de informação)
    HEADER_VALUE_FONT_SIZE = -1.0
    HEADER_VALUE_MIN_SIZE = 8.0

    # -------------------------
    # Seções específicas (SERVIÇO REALIZADO - CONTINUAÇÃO, RESULTADO, PENDÊNCIAS, MATERIAL FORNECIDO PELO CLIENTE)
    # Tudo controlado daqui.
    # -------------------------
    # Se True -> usa (por padrão) o tamanho de 'response' como base para as seções.
    SECTION_USE_RESPONSE_SIZE = True

    # Multiplicador aplicado à base de 'response' para definir o tamanho das seções.
    # Se SECTION_USE_RESPONSE_SIZE=True e SECTION_SIZE_MULTIPLIER=1.0 => seções = exatamente response size.
    SECTION_SIZE_MULTIPLIER = 1.0

    # Override absoluto (em pts). Se > 0, este valor tem prioridade e será usado como tamanho fixo.
    # Coloque -1.0 para desativar (padrão).
    SECTION_FONT_SIZE_OVERRIDE = -1.0

    # Fonte opcional específica para essas seções (deixe '' para usar FONT_REGULAR_NAME)
    SECTION_FONT_NAME = ''  # ex.: 'Roboto' ou 'Arial'

    # -------------------------
    # Espaçamentos / paddings (em pts)
    # -------------------------
    SMALL_PAD = 2
    MED_PAD = 3

    # -------------------------
    # Outros (mantidos por compatibilidade)
    # -------------------------
    DEBUG = False
    TESTING = False
  