# Sistema de Geração de Relatórios - PRONAV

## 📋 Visão Geral Completa do Projeto

O **Sistema de Geração de Relatórios PRONAV** é uma aplicação web completa desenvolvida em Flask para criação, armazenamento e geração de relatórios técnicos em formato PDF. O sistema é projetado para técnicos de campo registrarem atividades de serviço, problemas relatados, materiais utilizados e gerarem relatórios profissionais automaticamente.

### 🎯 Objetivo Principal
Automatizar a criação de relatórios de serviço técnico com:
- Interface web para preenchimento de dados
- Armazenamento em banco de dados SQLite
- Geração automática de PDFs formatados
- Gestão de rascunhos e relatórios finais
- Sistema de validação e normalização de dados robusto

---

## 🏗️ Arquitetura Completa do Sistema

### Estrutura de Diretórios Detalhada
```
pronav-relatorios/
├── 📄 app.py                 # Ponto de entrada da aplicação Flask
├── 📁 core/                  # Núcleo da aplicação
│   ├── ⚙️ config.py          # Configurações centralizadas de todo o sistema
│   ├── 🗃️ database.py        # Gerenciamento do banco de dados SQLite
│   ├── 📊 models.py          # Modelos de dados Pydantic com validações
│   ├── 🔧 normalizers.py     # Sistema completo de normalização de dados
│   ├── 🛣️ routes.py          # Definição de endpoints da API REST
│   ├── 🛠️ utils.py           # Utilitários gerais de formatação e texto
│   └── 📁 pdf/               # MÓDULO COMPLETO DE GERAÇÃO DE PDF
│       ├── 🎯 pdf_service.py # Serviço principal de orquestração do PDF
│       ├── 🔤 font_manager.py # Sistema de carregamento de fontes TTF
│       ├── 📑 header_drawer.py # Renderizador complexo do cabeçalho
│       ├── 📝 footer_drawer.py # Renderizador do rodapé e assinaturas
│       ├── 📚 story_builder.py # Orquestrador da construção do conteúdo
│       ├── 🎨 styles_builder.py # Sistema avançado de estilos do PDF
│       ├── 📋 tables_builder.py # Construtor de tabelas complexas
│       ├── 📐 primitives.py  # Elementos primitivos do PDF (linhas, etc.)
│       └── 🔧 utils.py       # Utilitários específicos do PDF
├── 📁 static/               # Arquivos estáticos (CSS, JS, imagens, fontes)
├── 📁 templates/            # Templates HTML para interface web
├── 💾 reports.db           # Banco de dados SQLite (gerado automaticamente)
└── 📋 requirements.txt     # Dependências do projeto Python
```

---

# 🔧 PARTE 1: NÚCLEO DA APLICAÇÃO (core/)

## 1. **app.py** - Ponto de Entrada da Aplicação

### Funções Principais Detalhadas:

#### `setup_logging()` - Sistema de Logs Robusto
```python
def setup_logging():
    """
    Configura sistema completo de logs com:
    - Rotação automática de arquivos (10MB max, 5 backups)
    - Handler para arquivo (app.log) e console
    - Formato: timestamp, módulo, nível, mensagem
    - Encoding UTF-8 para suporte a caracteres especiais
    """
```

#### `create_app()` - Factory Pattern para Flask
```python
def create_app():
    """
    Factory function que inicializa a aplicação Flask completa:
    1. Configura caminho de templates
    2. Carrega configurações da classe Config
    3. Inicializa sistema de logging
    4. Configura DatabaseManager
    5. Registra todas as rotas
    6. Configura tratamento global de exceções
    7. Inicializa banco de dados com tratamento de erro
    """
```

### Fluxo de Inicialização Passo a Passo:
```python
1. Cria instância Flask → 
2. Carrega Config → 
3. Setup Logging → 
4. Inicializa DatabaseManager → 
5. Registra Blueprints/Rotas → 
6. Configura Error Handlers → 
7. Inicializa DB (com try/except) → 
8. Retorna app pronta
```

### Sistema de Execução por SO:
```python
# Windows: Waitress (produção) → Flask dev server (fallback)
# Linux/macOS: Flask dev server para desenvolvimento
# Porta: Variável de ambiente PORT ou 5000 padrão
```

---

## 2. **core/config.py** - Sistema Centralizado de Configuração

### 🎨 Controle Total de Aparência do PDF

#### Sistema de Fontes e Tamanhos:
```python
# TAMANHOS BASE (em pontos) - controle global
TITLE_FONT_SIZE = 7.0      # Títulos principais das seções
LABEL_FONT_SIZE = 8.2      # Labels e textos de identificação
VALUE_FONT_SIZE = 8.2      # Campos de resposta e conteúdo

# MULTIPLICADORES - ajuste relativo fino
RESPONSE_VALUE_MULTIPLIER = 1.0  # Multiplicador para campos de resposta
LABEL_VALUE_MULTIPLIER = 1.0     # Multiplicador para labels
SECTION_SIZE_MULTIPLIER = 1.0    # Multiplicador para seções específicas

# LIMITES DE SEGURANÇA
MIN_FONT_SIZE = 6.0        # Mínimo absoluto para legibilidade
MAX_FONT_SIZE = 72.0       # Máximo para evitar estouro
```

#### Sistema de Configuração do Header (Cabeçalho):
```python
# POLÍTICA: >0 = tamanho fixo, <=0 = usa cálculo relativo
HEADER_TITLE_FONT_SIZE = -1.0     # "RELATÓRIO DE SERVIÇO"
HEADER_TITLE_MIN_SIZE = 9.0       # Mínimo se usar cálculo

HEADER_CONTACT_FONT_SIZE = -1.0   # Linha de contato (tel, email)
HEADER_CONTACT_MIN_SIZE = 7.0     # Mínimo para contato

HEADER_LABEL_FONT_SIZE = -1.0     # Labels: "NAVIO:", "CLIENTE:"
HEADER_LABEL_MIN_SIZE = 8.0       # Mínimo para labels

HEADER_VALUE_FONT_SIZE = -1.0     # Valores dos campos
HEADER_VALUE_MIN_SIZE = 8.0       # Mínimo para valores
```

#### Sistema de Seções Específicas:
```python
# CONTROLE GRANULAR POR SEÇÃO
SECTION_USE_RESPONSE_SIZE = True  # Usa VALUE_FONT_SIZE como base
SECTION_SIZE_MULTIPLIER = 1.0     # Multiplicador da base
SECTION_FONT_SIZE_OVERRIDE = -1.0 # Override absoluto se >0

# CONFIGURAÇÃO INDIVIDUAL POR SEÇÃO (exemplos)
SECTION_SERVICO_USE_RESPONSE_SIZE = True
SECTION_SERVICO_SIZE_MULTIPLIER = 1.1
SECTION_SERVICO_FONT_SIZE_OVERRIDE = -1.0
SECTION_SERVICO_FONT_NAME = 'Arial-Bold'
```

#### Caminhos de Recursos:
```python
# Fontes TTF personalizadas
FONT_REGULAR_PATH = 'static/fonts/arial.ttf'
FONT_BOLD_PATH = 'static/fonts/arialbd.ttf'
FONT_REGULAR_NAME = 'Arial'       # Nome registrado no PDF
FONT_BOLD_NAME = 'Arial-Bold'     # Nome registrado no PDF

# Logo da empresa
LOGO_PATH = 'static/images/logo.png'

# Espaçamentos
SMALL_PAD = 2    # Padding pequeno (pts)
MED_PAD = 3      # Padding médio (pts)
```

---

## 3. **core/database.py** - Gerenciamento Avançado de Banco de Dados

### Classe `DatabaseManager` - Funcionamento Detalhado:

#### `__init__(self, app)` - Inicialização
```python
def __init__(self, app):
    """
    Inicializa com referência à app Flask
    - Mantém configuração centralizada
    - Prepara para conexões sob demanda
    """
```

#### `get_db(self)` - Padrão Factory para Conexões
```python
def get_db(self):
    """
    Obtém conexão SQLite com otimizações:
    1. Verifica se já existe no contexto (g.db)
    2. Cria diretório do DB se não existir
    3. Configura PRAGMAs para performance:
       - journal_mode = WAL (Write-Ahead Logging)
       - synchronous = NORMAL (balance performance/durability)
       - foreign_keys = ON (integridade referencial)
    4. Usa row_factory = sqlite3.Row para acesso por nome
    5. Timeout de 30 segundos para locks
    """
```

#### `ensure_table_columns(self, db)` - Sistema de Migração
```python
def ensure_table_columns(self, db):
    """
    Migração de esquema sem perda de dados:
    - Adiciona colunas novas se não existirem
    - Mantém compatibilidade com versões antigas
    - Colunas gerenciadas:
      * status (text): 'draft' ou 'final'
      * updated_at (timestamp): data de atualização
      * equipments (text): JSON de equipamentos
      * city, state (text): localização geográfica
    """
```

#### `init_db(self)` - Inicialização do Banco
```python
def init_db(self):
    """
    Cria estrutura inicial do banco:
    - Tabela 'reports' com todos os campos necessários
    - Executa migrações via ensure_table_columns
    - Commit duplo para garantir consistência
    """
```

#### `map_db_row_to_api(self, row)` - Transformação de Dados
```python
def map_db_row_to_api(self, row):
    """
    Transforma linha do DB para formato da API:
    1. Converte JSON de activities/equipments para listas
    2. Cria aliases em português (CLIENTE, NAVIO, etc.)
    3. Compõe campo LOCAL com cidade e estado
    4. Garante estrutura consistente para frontend
    """
```

### 🗃️ Estrutura Completa da Tabela `reports`:
```sql
-- Campos principais de identificação
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id TEXT NOT NULL,              -- ID do usuário
client TEXT NOT NULL,               -- Nome do cliente
ship TEXT NOT NULL,                 -- Nome do navio
contact TEXT NOT NULL,              -- Pessoa de contato
work TEXT NOT NULL,                 -- Tipo de obra
location TEXT NOT NULL,             -- Localização
os_number TEXT NOT NULL,            -- Número da OS

-- Campos do equipamento
equipment TEXT,                     -- Nome do equipamento
manufacturer TEXT,                  -- Fabricante
model TEXT,                         -- Modelo
serial_number TEXT,                 -- Número de série

-- Campos de descrição do serviço
reported_problem TEXT,              -- Problema relatado
service_performed TEXT,             -- Serviço realizado
result TEXT,                        -- Resultado obtido
pending_issues TEXT,                -- Pendências

-- Materiais utilizados
client_material TEXT,               -- Material do cliente
pronav_material TEXT,               -- Material da PRONAV

-- Estruturas complexas (armazenadas como JSON)
activities TEXT,                    -- Lista de atividades
equipments TEXT,                    -- Lista de equipamentos

-- Localização geográfica
city TEXT,                          -- Cidade
state TEXT,                         -- Estado

-- Metadados
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP,               -- Data de atualização
status TEXT DEFAULT 'final'         -- Status: 'draft' ou 'final'
```

---

## 4. **core/models.py** - Sistema de Validação com Pydantic

### Classe `Activity` - Modelagem de Atividade Técnica:

#### Campos e Validações:
```python
class Activity(BaseModel):
    DATA: str                    # Data da atividade (DD/MM/YYYY)
    HORA: Optional[str] = None   # Hora no formato legado
    HORA_INICIO: Optional[str] = None  # Hora de início (HH:MM)
    HORA_FIM: Optional[str] = None     # Hora de fim (HH:MM)
    TIPO: str                    # Tipo de atividade
    KM: Optional[str] = None     # Quilometragem
    DESCRICAO: Optional[str] = '' # Descrição detalhada
    TECNICO1: str                # Primeiro técnico (obrigatório)
    TECNICO2: Optional[str] = None # Segundo técnico
    MOTIVO: Optional[str] = None  # Motivo da atividade
    ORIGEM: Optional[str] = None  # Local de origem
    DESTINO: Optional[str] = None # Local de destino
```

#### Validações de Negócio Complexas:
```python
@model_validator(mode='after')
def check_hours_present_and_km(self):
    """
    Validações complexas de negócio:
    1. HORAS: Exige HORA (formato antigo) OU HORA_INICIO + HORA_FIM
    2. QUILOMETRAGEM: Obrigatório exceto para tipos específicos
    3. Tipos sem KM: "Mão-de-obra Técnica", "Período de Espera", etc.
    4. Força KM vazio para tipos que não exigem quilometragem
    """
```

### Classe `ReportRequest` - Modelo Principal:

#### Campos Obrigatórios com Validação:
```python
class ReportRequest(BaseModel):
    # Identificação básica (todos obrigatórios)
    user_id: str
    CLIENTE: str
    NAVIO: str
    CONTATO: str
    OBRA: str
    LOCAL: str
    OS: str
    
    # Equipamento (opcionais com fallback)
    EQUIPAMENTO: Optional[str] = ''
    FABRICANTE: Optional[str] = ''
    MODELO: Optional[str] = ''
    NUMERO_SERIE: Optional[str] = ''
    
    # Descrição do serviço (todos obrigatórios)
    PROBLEMA_RELATADO: str
    SERVICO_REALIZADO: str
    RESULTADO: str
    PENDENCIAS: str
    
    # Materiais (obrigatórios)
    MATERIAL_CLIENTE: str
    MATERIAL_PRONAV: str
    
    # Estruturas complexas
    activities: List[Activity]           # Lista de atividades
    EQUIPAMENTOS: Optional[List[Dict[str, Any]]] = None  # Lista de equipamentos
    CIDADE: Optional[str] = None
    ESTADO: Optional[str] = None
```

#### Sistema de Validação com Pydantic:
```python
@field_validator('user_id', 'CLIENTE', 'NAVIO', 'CONTATO', 'OBRA', 'LOCAL', 'OS',
                 'PROBLEMA_RELATADO', 'SERVICO_REALIZADO', 'RESULTADO',
                 'PENDENCIAS', 'MATERIAL_CLIENTE', 'MATERIAL_PRONAV')
@classmethod
def validate_required_fields(cls, v):
    """
    Validação rigorosa de campos obrigatórios:
    - Verifica se não é None
    - Verifica se string não é vazia ou só espaços
    - Aplica strip() para limpeza
    - Levanta ValueError com mensagem clara
    """
```

---

## 5. **core/normalizers.py** - Sistema Completo de Normalização

### Arquitetura de Normalização:

#### `normalize_time_token(tok)` - Normalizador de Horas:
```python
def normalize_time_token(tok: str) -> Optional[str]:
    """
    Converte múltiplos formatos de hora para 'HH:MM':
    - '8:30'    → '08:30'
    - '08:30'   → '08:30'  
    - '8h30'    → '08:30'
    - '0830'    → '08:30'
    - '8'       → '08:00'
    - '8h'      → '08:00'
    
    Validações:
    - Horas: 0-23
    - Minutos: 0-59
    - Retorna None para formatos inválidos
    """
```

#### `_parse_time_range(s)` - Parser de Intervalos:
```python
def _parse_time_range(s: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detecta e parseia intervalos de tempo:
    - '8:00 às 12:00' → ('08:00', '12:00')
    - '8h-12h'        → ('08:00', '12:00')
    - '8 as 12'       → ('08:00', '12:00')
    
    Separadores suportados: 'às', 'as', '-', '–', '—', '/', ' a '
    """
```

#### `_try_parse_datetime(value)` - Parser de Datas Universal:
```python
def _try_parse_datetime(value: Any) -> Optional[datetime]:
    """
    Tenta interpretar qualquer formato de data/hora:
    
    1. Timestamps: 1640995200 (10 dígitos) ou 1640995200000 (13 dígitos)
    2. ISO: '2022-01-01', '2022-01-01 10:30:00'
    3. Brasileiro: '01/01/2022', '01/01/2022 10:30'
    4. Com hífen: '01-01-2022', '01-01-2022 10:30'
    5. Fallback: regex para padrões comuns em texto
    """
```

#### `normalize_activity(raw)` - Normalizador de Atividades:
```python
def normalize_activity(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processa dados brutos de atividade:
    
    1. DATA: Converte para datetime e formata BR
    2. HORAS: Parseia intervalos, normaliza formatos
    3. DESCRICAO: Remove redundâncias (origem/destino repetidos)
    4. TECNICOS: Mantém nomes completos, sem abreviação
    5. KM_BLOQUEADO: Converte para booleano de múltiplos formatos
    6. Mantém compatibilidade com modelo Pydantic
    """
```

#### `normalize_payload(payload)` - Orquestrador Principal:
```python
def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função principal que normaliza todo o payload:
    
    1. MAPEAMENTO DE ALIASES: Converte 'client' → 'CLIENTE', etc.
    2. PROCESSAMENTO DE ATIVIDADES: Lista de atividades normalizadas
    3. EQUIPAMENTOS: Normaliza lista de equipamentos
    4. COMPOSIÇÃO DE CAMPOS: LOCAL = local + cidade + estado
    5. FALLBACKS: Equipamento individual → lista de equipamentos
    6. REPORT_ID: Preserva ID se existir
    7. MANTÉM CAMPOS EXTRA: Preserva campos não mapeados
    """
```

### Sistema de Mapeamento de Aliases:
```python
MAPPING = {
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
```

---

## 6. **core/routes.py** - Sistema de API REST

### Decorator `@handle_errors(logger)` - Tratamento Global de Erros:
```python
def handle_errors(logger):
    """
    Decorator que envolve todas as rotas para tratamento consistente:
    
    1. Captura qualquer exceção não tratada
    2. Loga erro completo com traceback
    3. Retorna JSON padronizado: {'error': msg, 'msg': detalhe}
    4. Status HTTP 500 para erros internos
    5. Mantém resposta mesmo em falhas
    """
```

### Endpoints da API - Funcionamento Detalhado:

#### `POST /salvar-rascunho` - Salvamento de Rascunho:
```python
def salvar_rascunho():
    """
    Fluxo completo:
    1. Valida payload JSON
    2. Normaliza dados com normalize_payload()
    3. Valida com ReportRequest (Pydantic)
    4. Prepara listas para JSON (activities, equipments)
    5. Insere no banco com status 'draft'
    6. Retorna ID gerado e mensagem de sucesso
    """
```

#### `GET /relatorios-salvos` - Listagem com Filtro:
```python
def relatorios_salvos():
    """
    Lista relatórios por usuário:
    1. Valida user_id na query string
    2. Consulta ordenada por updated_at/created_at DESC
    3. Aplica aliases para compatibilidade com frontend
    4. Retorna lista paginável de relatórios
    """
```

#### `GET /relatorio/<id>` - Recuperação Individual:
```python
def get_report(report_id):
    """
    Recupera relatório completo:
    1. Busca por ID no banco
    2. Se não encontrado → 404
    3. Aplica map_db_row_to_api() para formatação
    4. Retorna JSON completo do relatório
    """
```

#### `PUT /atualizar-relatorio/<id>` - Atualização:
```python
def atualizar_relatorio(report_id):
    """
    Atualiza relatório existente:
    1. Valida payload JSON
    2. Normaliza dados
    3. Valida com Pydantic
    4. Atualiza registro mantendo status 'draft'
    5. Atualiza updated_at com timestamp atual
    """
```

#### `DELETE /relatorio/<id>` - Remoção:
```python
def delete_report(report_id):
    """
    Remove relatório:
    1. Delete por ID
    2. Verifica se registro existia (rowcount)
    3. Retorna 404 se não encontrado
    4. Commit da transação
    """
```

#### `POST /gerar-relatorio` - Endpoint Principal:
```python
def gerar_relatorio():
    """
    Gera PDF final - fluxo mais complexo:
    
    1. VALIDAÇÃO: Payload JSON obrigatório
    2. NORMALIZAÇÃO: normalize_payload()
    3. VALIDAÇÃO: ReportRequest (Pydantic)
    
    4. LÓGICA DE PERSISTÊNCIA:
       - Se tem report_id: UPDATE com status 'final'
       - Se não tem report_id: INSERT com status 'final'
       - Atualiza updated_at
    
    5. GERAÇÃO PDF: pdf_service.generate_pdf()
       - Se retorna None → erro crítico
       - Se sucesso → buffer PDF + ID
    
    6. RESPOSTA: send_file() com headers personalizados
       - X-Report-Id: ID do relatório
       - download_name: nome gerado automaticamente
    """
```

---

## 7. **core/utils.py** - Utilitários Gerais

### `format_date_br(raw)` - Formatador de Datas Universal:
```python
def format_date_br(raw: str) -> str:
    """
    Converte qualquer formato de data para 'dd/mm/yyyy':
    
    Algoritmo:
    1. Tenta dateutil.parser (mais flexível)
    2. Tenta formato ISO '2022-01-01'
    3. Tenta múltiplos formatos com strptime
    4. Fallback: regex para padrões comuns
    5. Preserva original se nenhum parser funcionar
    """
```

### `draw_text_no_abbrev(canvas, text, ...)` - Algoritmo de Texto Inteligente:
```python
def draw_text_no_abbrev(canvas, text: str, font_name: str, font_size: float,
                       x: float, y: float, max_width: float,
                       min_font_size: float = 6.0,
                       leading_mult: float = 1.06,
                       align: str = 'left'):
    """
    ALGORITMO CRÍTICO: Renderiza texto SEMPRE legível:
    
    Fluxo inteligente:
    1. TENTA TAMANHO ORIGINAL: Mede largura, se couber → renderiza
    2. REDUÇÃO GRADUAL: Diminui fonte em 0.5pt até min_font_size
    3. SE NÃO COUBER: Quebra em múltiplas linhas com simpleSplit
    4. NUNCA ABREVIA: Mantém texto completo, sem reticências
    5. LEADING AJUSTÁVEL: Espaçamento entre linhas proporcional
    
    Retorno: (tamanho_fonte_usado, lista_de_linhas)
    """
```

---

# 📄 PARTE 2: MÓDULO DE GERAÇÃO DE PDF (core/pdf/)

## 8. **core/pdf/pdf_service.py** - Serviço Principal de PDF

### Classe `PDFService` - Orquestração Completa:

#### `__init__(self, config)` - Inicialização Detalhada:
```python
def __init__(self, config):
    """
    Inicializa TODOS os componentes do sistema PDF:
    
    1. CONFIGURAÇÕES VISUAIS:
       - LINE_WIDTH: Espessura de linhas (0.6pt)
       - GRAY: Cor cinza do header (#D9D9D9)
       - SMALL_PAD/MED_PAD: Espaçamentos (2pt/3pt)
    
    2. SISTEMA DE FONTES:
       - Inicializa FontManager com caminhos do config
       - Define FONT_REGULAR e FONT_BOLD
    
    3. DIMENSÕES DE PÁGINA (convertidas de polegadas):
       - MARGIN: Margem principal (0.35")
       - header_row0: Altura do título (0.22")
       - header_row: Altura das linhas (0.26")
       - square_side: Lado do quadrado da logo (1.18")
    
    4. ALTURAS DE SEÇÕES:
       - sig_header_h_base: Cabeçalho assinatura (0.24")
       - sig_area_h_base: Área assinatura (0.6") 
       - footer_h_base: Rodapé (0.24")
    """
```

#### `generate_pdf(self, ...)` - Método Principal:
```python
def generate_pdf(self, report_request, atividades_list, equipments_list, saved_report_id):
    """
    FLUXO COMPLETO DE GERAÇÃO DO PDF:
    
    1. PREPARAÇÃO DO BUFFER:
       - Cria io.BytesIO() para output em memória
       - Define página como letter (215.9 x 279.4mm)
    
    2. CÁLCULOS DE LAYOUT:
       - Margens: MARG (configurável)
       - Frame: usable_w = PAGE_W - 2*MARG
       - Frame height: baseado em header_height_base e footer_total_height_base
    
    3. INICIALIZAÇÃO DE COMPONENTES:
       - StylesBuilder: Sistema de estilos
       - FontManager: Fontes TTF
       - HeaderDrawer: Cabeçalho complexo
       - FooterDrawer: Rodapé e assinaturas
       - StoryBuilder: Orquestrador de conteúdo
    
    4. CONSTRUÇÃO DO CONTEÚDO:
       - StoryBuilder.build_story() com frame_height
       - Inclui: equipamentos, seções, atividades
    
    5. CONFIGURAÇÃO DO DOCUMENTO:
       - BaseDocTemplate com margens
       - Frame de conteúdo com paddings
       - PageTemplate com header/footer
    
    6. CONSTRUÇÃO FINAL:
       - doc.build(story) → gera PDF
       - pdf_buffer.seek(0) → prepara para leitura
       - Retorna (buffer, saved_report_id)
    """
```

#### `get_filename(self, ...)` - Gerador de Nomes:
```python
def get_filename(self, report_request, equipments_list):
    """
    Gera nome de arquivo padronizado:
    Formato: RS_YYYYMMDD_NAVIO_EQUIPAMENTO.pdf
    
    Lógica:
    1. Data atual: datetime.utcnow().strftime('%Y%m%d')
    2. Navio: report_request.NAVIO ou 'Geral'
    3. Equipamento: Primeiro da lista ou campo individual
    4. Sanitização: Replace espaços e caracteres especiais
    """
```

---

## 9. **core/pdf/font_manager.py** - Sistema de Fontes TTF

### Classe `FontManager` - Carregamento Inteligente:

#### `_setup_fonts(self, config)` - Algoritmo de Carregamento:
```python
def _setup_fonts(self, config=None):
    """
    Carrega fontes TTF com fallbacks robustos:
    
    FONTE REGULAR:
    1. Tenta config.FONT_REGULAR_PATH
    2. Fallback: arial.ttf no diretório base
    3. Fallback final: Helvetica (nativa ReportLab)
    
    FONTE BOLD:
    1. Tenta config.FONT_BOLD_PATH  
    2. Fallback: arialbd.ttf no diretório base
    3. Fallback: Tenta criar bold da fonte regular
    4. Fallback final: Helvetica-Bold
    
    Registro: pdfmetrics.registerFont(TTFont(nome, caminho))
    """
```

#### Sistema de Fallback em Cascata:
```python
# Ordem de tentativas para cada fonte:
1. Caminho absoluto do config
2. Caminho relativo ao BASE_DIR  
3. Arquivo no diretório do font_manager.py
4. Fonte nativa do ReportLab (Helvetica)

# Nomes registrados (customizáveis):
FONT_REGULAR = 'Arial'      # ou 'Helvetica' se fallback
FONT_BOLD = 'Arial-Bold'    # ou 'Helvetica-Bold'
```

---

## 10. **core/pdf/styles_builder.py** - Sistema Avançado de Estilos

### Função `make_styles()` - Criação de Estilos Hierárquica:

#### Cálculo de Tamanhos de Fonte:
```python
def _num(x, fallback):
    """
    Conversão segura com fallback:
    - Converte para float
    - Aplica limites MIN_FONT_SIZE e MAX_FONT_SIZE
    - Garante valores numéricos válidos
    """
```

#### Sistema de Estilos Base:
```python
# ESTILOS PRINCIPAIS (controlados por config)
'TitleCenter':      # Títulos centrais (negrito, alinhado ao centro)
'label':            # Labels normais (negrito, alinhado à esquerda)  
'label_center':     # Labels centralizados (negrito, centro)
'response':         # Texto de resposta (normal, quebra de palavras)
'response_center':  # Resposta centralizada

# ESTILOS DE TABELA
'td', 'td_left', 'td_right': # Células de tabela com alinhamentos

# ESTILOS DE SEÇÃO
'sec_title':        # Títulos de seção
```

#### `_section_size(section_key)` - Configuração por Seção:
```python
def _section_size(section_key):
    """
    ALGORITMO DE PRIORIDADE PARA TAMANHOS DE SEÇÃO:
    
    1. CONFIGURAÇÃO ESPECÍFICA DA SEÇÃO:
       - SECTION_<KEY>_FONT_SIZE_OVERRIDE (absoluto)
       - SECTION_<KEY>_USE_RESPONSE_SIZE (booleano)
       - SECTION_<KEY>_SIZE_MULTIPLIER (relativo)
       - SECTION_<KEY>_FONT_NAME (fonte específica)
    
    2. CONFIGURAÇÃO GLOBAL DE SEÇÕES:
       - SECTION_FONT_SIZE_OVERRIDE
       - SECTION_USE_RESPONSE_SIZE  
       - SECTION_SIZE_MULTIPLIER
       - SECTION_FONT_NAME
    
    3. FALLBACK LEGADO:
       - SERVICE_VALUE_MULTIPLIER
    
    Chaves suportadas: 'SERVICO', 'RESULTADO', 'PENDENCIAS', 'MATERIAL'
    """
```

#### Mapeamento de Seções para Estilos:
```python
# Seção "SERVIÇO REALIZADO" → estilo 'servico_continuacao'
# Seção "RESULTADO" → estilo 'resultado' 
# Seção "PENDÊNCIAS" → estilo 'pendencias'
# Seção "MATERIAL FORNECIDO..." → estilo 'material_fornecido_cliente'

# Estilo unificado para seções longas: 'section_value_large'
```

---

## 11. **core/pdf/header_drawer.py** - Cabeçalho Complexo

### Classe `HeaderDrawer` - Renderização Avançada:

#### `_resolve_font(override_size, min_size, base_size)` - Resolvedor de Fontes:
```python
def _resolve_font(self, override_size, min_size, base_size):
    """
    Política de tamanhos de fonte no header:
    
    SE override_size > 0: 
        Usa override_size (tamanho fixo em pts)
    SENÃO:
        Usa max(min_size, base_size) (tamanho relativo)
    
    Retorna int (pontos) para setFont()
    """
```

#### `draw_header(self, ...)` - Algoritmo de Renderização:
```python
def draw_header(self, canvas, doc_local, logo_bytes, report_request, ensure_upper_safe):
    """
    FLUXO COMPLETO DO HEADER:
    
    1. CONFIGURAÇÃO INICIAL:
       - saveState(), setLineWidth, setStrokeColor
       - Calcula coordenadas: left_x, right_x, top_y, bottom_y
    
    2. DESENHO DA ESTRUTURA:
       - Linhas de borda (canvas.line)
       - Área da logo (canvas.rect)
       - Linhas divisórias horizontais
    
    3. LOGO DINÂMICA:
       - Tenta logo_bytes (já carregada)
       - Fallback: config.LOGO_PATH
       - Fallback final: texto "PRONAV"
       - Redimensionamento automático mantendo aspect ratio
    
    4. LINHA DE CONTATO:
       - Texto pequeno acima do header
       - CNPJ, telefones, email, website
       - Fonte configurável via HEADER_CONTACT_FONT_SIZE
    
    5. TÍTULO PRINCIPAL:
       - "RELATÓRIO DE SERVIÇO" em negrito
       - Fundo cinza (canvas.rect + fill)
       - Centralizado horizontalmente
       - Fonte via HEADER_TITLE_FONT_SIZE
    
    6. INFORMAÇÕES ESTRUTURADAS:
       - BLOCO ESQUERDO: NAVIO, CONTATO, LOCAL
       - BLOCO DIREITO: CLIENTE, OBRA, OS
       - Labels em negrito, valores em normal
       - Fontes via HEADER_LABEL_FONT_SIZE e HEADER_VALUE_FONT_SIZE
    
    7. ALINHAMENTO E TRUNCAMENTO:
       - Calcula larguras disponíveis por coluna
       - Truncamento com reticências se necessário
       - Alinhamento vertical centralizado
    """
```

#### Sistema de Layout em Grade:
```python
# COORDENADAS VERTICAIS (de cima para baixo):
y_top = top_y
y_row0 = y_top - header_row0        # Linha do título
y_row1 = y_row0 - header_row        # Primeira linha de dados
y_row2 = y_row1 - header_row        # Segunda linha
y_row3 = y_row2 - header_row        # Terceira linha

# LARGURAS DE COLUNAS (proporcionais):
col0_w = inner_label_w             # Largura dos labels esquerdo
col1_w = inner_val_w_left          # Largura dos valores esquerdo  
col2_w = inner_label_w2            # Largura dos labels direito
col3_w = inner_val_w_right         # Largura dos valores direito
```

---

## 12. **core/pdf/footer_drawer.py** - Rodapé e Assinaturas

### Classe `FooterDrawer` - Área de Assinatura:

#### `draw_signatures_and_footer(self, ...)` - Rodapé Completo:
```python
def draw_signatures_and_footer(self, canvas, doc_local, usable_w, left_margin):
    """
    DESENHO DA ÁREA DE ASSINATURA E RODAPÉ:
    
    1. RODAPÉ INFERIOR:
       - Retângulo cinza com texto centralizado
       - "O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE"
       - Altura: footer_h_base
    
    2. ÁREA DE ASSINATURAS:
       - Dois retângulos lado a lado
       - ESQUERDA: "ASSINATURA DO COMANDANTE" 
       - DIREITA: "ASSINATURA DO TÉCNICO"
       - Cabeçalho cinza + área branca para assinatura
    
    3. LINHAS DIVISÓRIAS:
       - Borda externa das áreas
       - Linha vertical divisória central
       - Espessura consistente (LINE_WIDTH)
    
    4. NUMERAÇÃO DE PÁGINA:
       - Texto cinza centralizado abaixo de tudo
       - "Página N" em fonte pequena (7pt)
       - Posicionamento relativo ao bottomMargin
    """
```

#### `on_page_template(self, ...)` - Integração com PageTemplate:
```python
def on_page_template(self, canvas, doc_local, draw_header_fn, logo_bytes, ensure_upper_safe, usable_w, left_margin):
    """
    Chamado automaticamente a cada página:
    
    1. Chama draw_header_fn para cabeçalho
    2. Chama draw_signatures_and_footer para rodapé
    3. Adiciona numeração de página
    4. Garante consistência visual em todas as páginas
    """
```

---

## 13. **core/pdf/story_builder.py** - Orquestrador de Conteúdo

### Classe `StoryBuilder` - Coordenação do Fluxo:

#### `build_story(self, ...)` - Construção Sequencial:
```python
def build_story(self, report_request, atividades_list, equipments_list, frame_height=None):
    """
    ORQUESTRA A CONSTRUÇÃO DE TODO O CONTEÚDO:
    
    1. SPACER INICIAL: (1pt) - ajuste fino de posicionamento
    
    2. TABELA DE EQUIPAMENTOS:
       - EquipmentTableBuilder.build()
       - Mostra equipamentos ou fallback para campos individuais
    
    3. SPACER INTERMEDIÁRIO: (2pt) - separação visual
    
    4. MEDIÇÃO DE ESPAÇO USADO:
       - Calcula altura exata dos elementos já adicionados
       - Usa wrap() para medição precisa de cada flowable
       - Converte para page_top_offset (inteiro)
    
    5. SEÇÕES DE TEXTO:
       - SectionsTableBuilder.build() com page_top_offset
       - Lista de seções pré-definidas:
         * "PROBLEMA RELATADO/ENCONTRADO"
         * "SERVIÇO REALIZADO" 
         * "RESULTADO"
         * "PENDÊNCIAS"
         * "MATERIAL FORNECIDO PELO CLIENTE"
         * "MATERIAL FORNECIDO PELA PRONAV"
    
    6. TABELA DE ATIVIDADES (se houver):
       - ActivitiesTableBuilder.build()
       - Só renderiza se atividades_list não estiver vazia
    
    Retorna: Lista ordenada de flowables para o PDF
    """
```

#### Sistema de Medição de Espaço:
```python
# Cálculo preciso do espaço já ocupado:
used_top_h = 0.0
for f in story_local:
    if hasattr(f, 'wrap'):
        _, h = f.wrap(self.usable_w, wrap_max_h)
        used_top_h += h
    elif hasattr(f, 'height'):
        used_top_h += f.height

page_top_offset = int(math.ceil(used_top_h))
```

---

## 14. **core/pdf/tables_builder.py** - Sistema de Tabelas Complexas

### ⚡ **Função `shrink_paragraph_to_fit()` - Algoritmo Crítico**

```python
def shrink_paragraph_to_fit(text, base_style, max_w, max_h, min_font=6):
    """
    GARANTE QUE TEXTO SEMPRE CAIBA NAS CÉLULAS:
    
    FLUXO INTELIGENTE:
    1. TENTATIVA INICIAL: Tamanho original da fonte
       - Cria Paragraph com estilo base
       - Mede com wrap(max_w, max_h)
       - Se couber → retorna Paragraph
    
    2. REDUÇÃO GRADUAL: Diminui fonte em 0.5pt
       - Loop while size >= min_font
       - Ajusta leading proporcionalmente
       - Tenta cada tamanho com wrap()
       - Para na primeira que couber
    
    3. FALLBACK FINAL: Tamanho mínimo
       - Usa min_font (6pt padrão)
       - Leading mínimo para legibilidade
       - Retorna Paragraph mesmo que não caiba perfeitamente
    
    NUNCA USA ABREVIAÇÃO OU RETICÊNCIAS
    """
```

### Classe `EquipmentTableBuilder` - Tabela de Equipamentos:

#### `build(self, ...)` - Tabela Compacta:
```python
def build(self, report_request, equipments_list, usable_w):
    """
    CONSTRÓI TABELA DE EQUIPAMENTOS (4 COLUNAS):
    
    1. DADOS:
       - Se equipments_list vazia: usa campos individuais como fallback
       - Header: ["EQUIPAMENTO", "FABRICANTE", "MODELO", "Nº DE SÉRIE"]
    
    2. DIMENSIONAMENTO:
       - Colunas igualmente distribuídas (usable_w / 4)
       - Altura fixa: header_h = 0.16*inch, value_h = 0.14*inch
    
    3. RENDERIZAÇÃO:
       - Header com fundo cinza e texto centralizado
       - Valores alinhados à esquerda
       - Borda completa (BOX) e linhas internas (INNERGRID)
       - Padding consistente (equip_left_pad, equip_right_pad)
    
    4. AJUSTE DE TEXTO:
       - shrink_paragraph_to_fit() para cada célula
       - ensure_upper_safe() para texto em maiúsculas
    """
```

### Classe `ActivitiesTableBuilder` - Tabela Mais Complexa:

#### `build(self, ...)` - Tabela de Atividades com Lógica Complexa:
```python
def build(self, atividades_list, usable_w, square_side):
    """
    TABELA DE ATIVIDADES (7 COLUNAS) - LÓGICA AVANÇADA:
    
    1. PROPORÇÕES DINÂMICAS:
       proportions = [0.09, 0.12, 0.24, 0.43, 0.03, 0.065, 0.065]
       - Ajusta baseado no espaço da logo (square_side)
       - Reduz descrição, aumenta técnicos
    
    2. ARREDONDAMENTO PRECISO:
       - Converte proporções para pontos inteiros
       - Ajusta diferenças na última coluna
       - Garante soma exata = usable_w
    
    3. PROCESSAMENTO DE ATIVIDADES:
       - DATA: format_date_br() para formato brasileiro
       - HORA: Combina HORA_INICIO e HORA_FIM se disponível
       - DESCRIÇÃO: Combina origem/destino se aplicável
       - TÉCNICOS: Processa nomes completos, remove abreviações
       - KM: Aplica lógica por tipo de atividade
    
    4. HEADER COM SPAN:
       - "TÉCNICOS" ocupa duas colunas (SPAN)
       - Header com fundo cinza e texto centralizado
    
    5. ESTILO CONSISTENTE:
       - Borda externa (BOX) e linhas internas (INNERGRID)
       - Padding mínimo para compactação
       - Alinhamento left para conteúdo
    """
```

#### Sistema de Proporções Dinâmicas:
```python
# Proporções iniciais (percentuais da largura total)
proportions = [0.09, 0.12, 0.24, 0.43, 0.03, 0.065, 0.065]

# Ajuste baseado no espaço da logo:
delta_prop = min(0.12, (square_side / usable_w) * 1.0)

# Redistribuição:
proportions[3] -= delta_prop          # Descrição (índice 3)
proportions[5] += delta_prop / 2.0    # Técnico1 (índice 5)  
proportions[6] += delta_prop / 2.0    # Técnico2 (índice 6)

# Normalização para soma = 1.0
total_prop = sum(proportions)
proportions = [p / total_prop for p in proportions]
```

### Classe `SectionsTableBuilder` - Sistema de Quebra de Página Inteligente:

#### `build(self, ...)` - Algoritmo de Quebra Avançado:
```python
def build(self, sections, usable_w, frame_height=None, estimate_height_fn=None, page_top_offset=0):
    """
    SISTEMA INTELIGENTE DE SEÇÕES COM QUEBRA DE PÁGINA:
    
    1. EVITA "TÍTULO ÓRFÃO":
       - Calcula espaço disponível considerando page_top_offset
       - Se conteúdo não couber com título → KeepTogether()
       - Move título+conteúdo juntos para próxima página
    
    2. CONTINUAÇÃO AUTOMÁTICA:
       - Títulos seguem padrão: "N. TÍTULO - CONTINUAÇÃO"
       - KeepTogether() para títulos de continuação
       - Mantém contexto em páginas subsequentes
    
    3. ESTIMATIVA DE ALTURA:
       - Usa estimate_row_height() para cada parágrafo
       - Considera paddings e bordas
       - wrap() para medição precisa
    
    4. EMPACOTAMENTO INTELIGENTE:
       - Agrupa máximo de parágrafos que cabem na página
       - Garante pelo menos um parágrafo por chunk
       - Available_h = frame_height - title_h - page_top_offset - safety_gap
    
    5. COMPACTAÇÃO:
       - Padding mínimo entre elementos
       - Títulos "minimal" para continuação com padding ajustado
       - Spacers mínimos entre seções
    """
```

#### Algoritmo de Quebra de Página:
```python
# Lógica de decisão para primeira chunk:
if first_chunk:
    available_h = frame_height - title_h - page_top_offset - safety_gap
    if used_h <= available_h:
        # Cabe na página atual → anexa normalmente
        flowables.append(curr_title)
        flowables.append(content_tbl)
    else:
        # Não cabe → decide baseado no contexto
        if not flowables:
            # Primeiro elemento do documento → força na página
            flowables.append(curr_title)
            flowables.append(content_tbl)
        else:
            # Já tem conteúdo → move para próxima página
            flowables.append(KeepTogether([curr_title, content_tpl]))
```

---

## 15. **core/pdf/primitives.py** - Elementos Primitivos

### Classe `HR` - Linha Horizontal:
```python
class HR(Flowable):
    """
    Linha divisória fina para indicar continuidade:
    
    - Herda de Flowable do ReportLab
    - Configurável em espessura (thickness)
    - Padding top/bottom ajustável
    - Largura fixa ou variável
    - Usada para separar seções em continuação
    """
```

---

## 16. **core/pdf/utils.py** - Utilitários Específicos

### `_norm_text(cell)` - Normalizador de Texto:
```python
def _norm_text(cell):
    """
    Normaliza texto para comparação e processamento:
    
    1. Extrai texto: getPlainText() ou str()
    2. Normaliza Unicode: NFKD (remove acentos)
    3. Remove diacríticos: category(ch).startswith('M')
    4. Limpa espaços: re.sub(r'\s+', ' ', s).strip()
    5. Remove pontuação das bordas
    6. Converte para lowercase
    """
```

### `find_logo_bytes(config_obj)` - Localizador Robusto de Logo:
```python
def find_logo_bytes(config_obj):
    """
    ORDEM DE BUSCA DA LOGO (fallback em cascata):
    
    1. BYTES DIRETOS: logo_val como bytes/bytearray
    2. CONFIG PATH: config.LOGO_PATH (absoluto)
    3. CAMINHO RELATIVO: baseado em __file__
    4. LOCAIS PADRÃO:
       - static/images/logo.png
       - static/logo.png  
       - current_work_dir/static/images/logo.png
       - current_work_dir/static/logo.png
       - module_dir/static/images/logo.png
    
    5. PACKAGE DATA: pkgutil.get_data() para embalagem
    
    6. FALLBACK: Retorna None (usa texto)
    
    Tratamento de exceções em cada etapa
    """
```

---

## 🔄 FLUXOS DE TRABALHO COMPLETOS

### 1. Fluxo Principal: Criação de Relatório
```
FRONTEND → POST /gerar-relatorio (JSON) → 
↓
normalize_payload() (mapeamento, limpeza, conversão) → 
↓
ReportRequest.validate() (validação Pydantic com regras de negócio) → 
↓
DatabaseManager.save() (INSERT/UPDATE com status 'final') → 
↓
PDFService.generate_pdf() (orquestração completa do PDF) → 
↓
send_file() (download com headers personalizados)
```

### 2. Fluxo de Geração de PDF
```
PDFService.generate_pdf() → 
↓
FontManager (carrega TTF) + StylesBuilder (define estilos) → 
↓
HeaderDrawer (cabeçalho complexo) + FooterDrawer (rodapé) → 
↓
StoryBuilder.build_story() (coordena construção) → 
↓
EquipmentTableBuilder (tabela equipamentos) → 
↓
SectionsTableBuilder (seções com quebra inteligente) → 
↓
ActivitiesTableBuilder (tabela atividades complexa) → 
↓
BaseDocTemplate.build() (renderização final) → 
↓
PDF Buffer pronto para download
```

### 3. Fluxo de Normalização de Dados
```
Payload bruto → normalize_payload() → 
↓
Mapeamento aliases (client → CLIENTE, etc.) → 
↓
Processamento atividades: normalize_activity() para cada item → 
↓
  - normalize_time_token() para horas
  - _parse_time_range() para intervalos  
  - _try_parse_datetime() para datas
  - _sanitize_description() para descrições
↓
Processamento equipamentos: normalize_equipments() → 
↓
Composição campos (LOCAL = local + cidade + estado) → 
↓
Payload normalizado para validação Pydantic
```

### 4. Fluxo de Quebra de Página Inteligente
```
Medir espaço usado (page_top_offset) → 
↓
Para cada seção: calcular available_h → 
↓
Se primeira chunk da seção:
  - available_h = frame_height - title_h - page_top_offset - safety_gap
  - Se conteúdo cabe → anexa normalmente
  - Se não cabe e é primeiro elemento → força na página
  - Se não cabe e não é primeiro → KeepTogether() para próxima página
↓
Se continuação:
  - available_h = frame_height - title_h - page_top_offset - safety_gap - cont_margin  
  - Sempre usa KeepTogether() para título+conteúdo
↓
Empacotar máximo de parágrafos que cabem no available_h
```

---

## 🎛️ SISTEMA DE CONFIGURAÇÃO COMPLETO

### Hierarquia de Configuração:
```
config.py (Configurações Mestras)
    ↓
PDFService (Aplica defaults e conversões)
    ↓
HeaderDrawer (Configurações específicas do header)
    ↓
StylesBuilder (Sistema de estilos hierárquico)
    ↓
TablesBuilder (Configurações de tabela e layout)
    ↓
Elementos individuais (Fontes, cores, espaçamentos)
```

### Exemplos de Customização Avançada:

#### Para Header Maior e Mais Visível:
```python
HEADER_TITLE_FONT_SIZE = 12.0        # Título grande e fixo
HEADER_LABEL_FONT_SIZE = 10.0        # Labels maiores
HEADER_VALUE_FONT_SIZE = 10.0        # Valores maiores
HEADER_ROW0_INCH = 0.3               # Altura do título aumentada
HEADER_ROW_INCH = 0.3                # Altura das linhas aumentada
```

#### Para Seções Específicas com Estilo Diferente:
```python
# Apenas a seção de SERVIÇO com fonte maior
SECTION_SERVICO_USE_RESPONSE_SIZE = False
SECTION_SERVICO_FONT_SIZE_OVERRIDE = 10.0
SECTION_SERVICO_FONT_NAME = 'Arial-Bold'

# Seção de RESULTADO com fonte menor e italico
SECTION_RESULTADO_USE_RESPONSE_SIZE = True  
SECTION_RESULTADO_SIZE_MULTIPLIER = 0.9
SECTION_RESULTADO_FONT_NAME = 'Arial-Italic'

# Demais seções usam padrão
SECTION_USE_RESPONSE_SIZE = True
SECTION_SIZE_MULTIPLIER = 1.0
```

#### Para Layout Mais Compacto:
```python
PAGE_MARGIN_INCH = 0.25              # Margens menores
SMALL_PAD = 1                         # Padding reduzido
MED_PAD = 2                           # Padding médio reduzido
HEADER_ROW0_INCH = 0.18               # Header mais compacto
HEADER_ROW_INCH = 0.22                # Linhas mais compactas
```

#### Para Cores Personalizadas:
```python
LINE_GRAY_HEX = '#E0E0E0'            # Cinza mais claro
# Ou para cores da empresa:
LINE_GRAY_HEX = '#2E5A88'            # Azul corporativo
```

---

## 🛠️ GUIA COMPLETO DE MANUTENÇÃO E MODIFICAÇÃO

### Como Adicionar Um Novo Campo ao Relatório:

#### 1. **Database - Adicionar Coluna:**
```python
# Em database.py - ensure_table_columns():
if 'novo_campo' not in cols:
    try:
        db.execute("ALTER TABLE reports ADD COLUMN novo_campo TEXT")
    except sqlite3.Error:
        pass

# Em map_db_row_to_api():
d['NOVO_CAMPO'] = d.get('novo_campo') or ''
```

#### 2. **Model - Adicionar Campo e Validação:**
```python
# Em models.py - ReportRequest:
class ReportRequest(BaseModel):
    # ... campos existentes ...
    NOVO_CAMPO: str
    
    @field_validator('NOVO_CAMPO')
    @classmethod
    def validate_novo_campo(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError('NOVO_CAMPO é obrigatório')
        return v.strip()
```

#### 3. **Normalizer - Mapear Aliases:**
```python
# Em normalizers.py - normalize_payload():
# No mapping:
'novo_campo': 'NOVO_CAMPO',
'new_field': 'NOVO_CAMPO',

# No processamento de top_keys:
top_keys = ['NOVO_CAMPO', ...]
```

#### 4. **PDF - Adicionar ao Header ou Seções:**
```python
# Para header - em header_drawer.py:
# Adicionar aos labels_left/right ou values_left/right

# Para seções - em story_builder.py:
sections = [
    # ... seções existentes ...
    ("NOVA SEÇÃO", report_request.NOVO_CAMPO),
]
```

### Como Modificar o Layout de Tabelas:

#### Para Redistribuir Colunas da Tabela de Atividades:
```python
# Em tables_builder.py - ActivitiesTableBuilder.build():
# Modificar as proporções iniciais:
proportions = [0.10, 0.15, 0.20, 0.35, 0.05, 0.075, 0.075]
# Índices: 0=DATA, 1=HORA, 2=TIPO, 3=DESCRICAO, 4=KM, 5=TEC1, 6=TEC2
```

#### Para Ajustar Alturas de Linha:
```python
# Em EquipmentTableBuilder:
header_h = 0.18 * inch    # Aumentar header
value_h = 0.16 * inch     # Aumentar linhas de valores

# Em ActivitiesTableBuilder:
max_h_cell = 0.8 * inch   # Aumentar altura máxima das células
```

### Como Debug de Problemas Comuns:

#### Texto Não Cabe nas Células:
```python
# Aumentar altura máxima:
max_h_cell = 1.0 * inch   # Em ActivitiesTableBuilder

# Reduzir mínimo de fonte:
min_font = 5.0            # Em shrink_paragraph_to_fit()

# Aumentar leading (espaçamento entre linhas):
leading_mult = 1.1         # Em draw_text_no_abbrev()
```

#### Quebras de Página Indesejadas:
```python
# Em SectionsTableBuilder - ajustar safety_gap:
safety_gap = 0.5          # Reduzir margem de segurança

# Aumentar frame_height disponível:
frame_height = frame_top - frame_bottom + 20  # +20pts
```

#### Problemas com Fontes:
```python
# Verificar caminhos no config.py:
FONT_REGULAR_PATH = 'static/fonts/arial.ttf'  # Caminho correto?
FONT_BOLD_PATH = 'static/fonts/arialbd.ttf'   # Arquivo existe?

# Fallback para fontes nativas:
FONT_REGULAR_NAME = 'Helvetica'
FONT_BOLD_NAME = 'Helvetica-Bold'
```

### Como Adicionar Uma Nova Seção Complexa:

#### 1. **Criar Estilo Específico:**
```python
# Em styles_builder.py - _section_size():
if section_key == 'MINHA_NOVA_SECAO':
    key_prefix = 'SECTION_MINHA_NOVA_SECAO'

# Registrar estilo:
add_or_update('minha_nova_secao', 
    fontName=font_eff, 
    fontSize=svc, 
    leading=max(8, svc * 1.06)
)
```

#### 2. **Criar Builder Especializado (se necessário):**
```python
class MinhaNovaSecaoBuilder:
    def build(self, dados, usable_w):
        # Lógica específica da nova seção
        # Pode incluir tabelas, imagens, etc.
        return table_flowable
```

#### 3. **Integrar ao Story Builder:**
```python
# Em story_builder.py - build_story():
# Após as seções existentes:
minha_nova_tabela = self.minha_nova_builder.build(dados, self.usable_w)
story_local.append(minha_nova_tabela)
```

### Como Customizar Cores e Estilos Visuais:

#### Modificar Cores do Header:
```python
# Em pdf_service.py - __init__():
gray_hex = getattr(self.config, 'LINE_GRAY_HEX', '#D9D9D9')
self.GRAY = colors.HexColor(gray_hex)

# Para header específico:
self.HEADER_BG_COLOR = colors.HexColor('#2E5A88')  # Azul
self.HEADER_TEXT_COLOR = colors.white              # Texto branco
```

#### Modificar Estilos de Borda:
```python
# Em todos os TableBuilders:
activities_table.setStyle(TableStyle([
    ('BOX', (0, 0), (-1, -1), 1.0, colors.blue),  # Borda azul
    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightblue),
]))
```

---

## 🚀 OTIMIZAÇÕES E CONSIDERAÇÕES DE PERFORMANCE

### Otimizações Implementadas:

#### 1. **Cache de Fontes:**
```python
# FontManager carrega TTF uma vez por processo
# Evita I/O repetido em cada geração de PDF
```

#### 2. **Buffer em Memória:**
```python
# Uso de io.BytesIO() evita I/O em disco
# Mais rápido e adequado para ambiente web
```

#### 3. **Medição Precisa:**
```python
# Uso inteligente de wrap() para cálculos exatos
# Minimiza recalculos e quebras desnecessárias
```

#### 4. **Layout Estático:**
```python
# Cálculos de posição uma vez no início
# Reutilização de coordenadas e dimensões
```

### Áreas Críticas de Performance:

#### 1. **Tabela de Atividades com Muitos Itens:**
```python
# Com 50+ atividades pode ficar lento
# Solução: Paginação ou otimização de renderização
```

#### 2. **Seções Muito Longas:**
```python
# Texto muito extenso em SERVICO_REALIZADO
# Solução: Quebra inteligente com cache de medição
```

#### 3. **Carregamento Inicial de Fontes:**
```python
# Primeiro PDF pode ser mais lento
# Solução: Pré-carregamento em background
```

---

## 🔧 SISTEMA DE FALLBACK E RESILIÊNCIA

### Graceful Degradation Implementado:

#### 1. **Fontes:**
```python
# TTF personalizada → TTF fallback → Helvetica nativa
# Nunca quebra geração do PDF
```

#### 2. **Logo:**
```python
# Imagem personalizada → caminhos padrão → texto "PRONAV"
# Sempre tem representação visual
```

#### 3. **Texto:**
```python
# Tamanho ideal → redução gradual → mínimo legível (6pt)
# Texto sempre visível, nunca cortado
```

#### 4. **Layout:**
```python
# Proporções dinâmicas → cálculo fallback → proporções fixas
# Layout sempre funcional
```

### Tratamento de Erros Robusto:

```python
# Em TODAS as operações críticas:
try:
    # Operação potencialmente problemática
except Exception as e:
    # Log detalhado do erro
    # Aplicação de fallback
    # Continuação do processamento
```

---

Este README completo fornece conhecimento profundo de cada componente, fluxo e algoritmo do sistema. Desenvolvedores podem agora:

- ✅ **Entender** cada função e sua finalidade
- ✅ **Modificar** qualquer aspecto do sistema
- ✅ **Extender** funcionalidades com segurança
- ✅ **Debuggar** problemas complexos
- ✅ **Otimizar** performance onde necessário
- ✅ **Customizar** aparência e comportamento

O sistema é uma arquitetura robusta, bem documentada e altamente maintainable para geração profissional de relatórios técnicos.