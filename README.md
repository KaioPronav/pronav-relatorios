# Documentação Completa do Sistema de Relatórios PDF

## 📋 Visão Geral do Projeto

Este é um sistema completo para geração de relatórios de serviço em PDF, construído com Flask e ReportLab. O sistema inclui persistência em banco de dados SQLite, validação de dados com Pydantic, e geração de PDFs altamente customizáveis.

## 🗂️ Estrutura de Arquivos e Localização de Código

### 1. **Configuração Central** (`config.py`)
**Localização**: Raiz do projeto

**Propósito**: Arquivo central de configuração para TODOS os aspectos visuais do PDF.

**Configurações Principais**:

```python
# Fontes e caminhos
FONT_REGULAR_PATH = 'caminho/para/fonte/regular.ttf'
FONT_BOLD_PATH = 'caminho/para/fonte/bold.ttf'
FONT_REGULAR_NAME = 'Arial'
FONT_BOLD_NAME = 'Arial-Bold'

# Tamanhos base de fonte
TITLE_FONT_SIZE = 7.0      # Títulos principais
LABEL_FONT_SIZE = 8.2      # Labels/seções curtas
VALUE_FONT_SIZE = 8.2      # Campos de resposta

# Configurações de Header
HEADER_TITLE_FONT_SIZE = -1.0    # Título "RELATÓRIO DE SERVIÇO"
HEADER_CONTACT_FONT_SIZE = -1.0  # Linha de contato
HEADER_LABEL_FONT_SIZE = -1.0    # Labels do header (NAVIO:, CONTATO:, etc.)
HEADER_VALUE_FONT_SIZE = -1.0    # Valores do header

# Configurações de Seções
SECTION_USE_RESPONSE_SIZE = True
SECTION_SIZE_MULTIPLIER = 1.0
SECTION_FONT_SIZE_OVERRIDE = -1.0
```

### 2. **Gerenciamento de Banco de Dados** (`database.py`)
**Localização**: Raiz do projeto

**Classes Principais**:
- `DatabaseManager`: Gerencia conexões SQLite e operações de banco

**Funções Chave**:
- `get_db()`: Obtém conexão com o banco
- `init_db()`: Inicializa tabelas do banco
- `map_db_row_to_api()`: Converte linhas do DB para formato da API
- `ensure_table_columns()`: Garante que colunas existam (migration)

### 3. **Modelos de Dados** (`models.py`)
**Localização**: Raiz do projeto

**Classes**:
- `Activity`: Modelo para atividades com validações de hora/KM
- `ReportRequest`: Modelo principal do relatório com validações

**Validações Incluídas**:
- Campos obrigatórios
- Validação de formato de horas
- Validação de KM baseada no tipo de atividade

### 4. **Normalização de Dados** (`normalizers.py`)
**Localização**: Raiz do projeto

**Funções Principais**:
- `normalize_activity()`: Normaliza dados de atividade (data, hora, descrição)
- `normalize_payload()`: Normaliza payload completo da requisição
- `normalize_equipments()`: Normaliza lista de equipamentos

**Processa**:
- Formatos de data/hora diversos
- Separação de horas (ex: "08:00 às 12:00")
- Sanitização de descrições

### 5. **Serviço Principal de PDF** (`pdf_service.py`)
**Localização**: `core/pdf/pdf_service.py`

**Classe Principal**: `PDFService`

**Responsabilidades**:
- Coordena toda a geração do PDF
- Configura página, margens, frames
- Chama builders especializados

**Métodos Principais**:
- `generate_pdf()`: Gera o PDF completo
- `get_filename()`: Gera nome do arquivo PDF

### 6. **Sistema de Fontes** (`font_manager.py`)
**Localização**: `core/pdf/font_manager.py`

**Classe**: `FontManager`

**Função**: Registra fontes TTF no ReportLab usando caminhos do config

### 7. **Sistema de Estilos** (`styles_builder.py`)
**Localização**: `core/pdf/styles_builder.py`

**Função Principal**: `make_styles()`

**Cria Estilos Para**:
- Títulos, labels, valores
- Seções específicas (Serviço, Resultado, Pendências)
- Tabelas e parágrafos

### 8. **Componentes Visuais**

#### Header (`header_drawer.py`)
**Localização**: `core/pdf/header_drawer.py`

**Classe**: `HeaderDrawer`

**Desenha**:
- Logo da empresa
- Título "RELATÓRIO DE SERVIÇO"
- Informações do cliente/navio/obra
- Linhas de contato

#### Footer (`footer_drawer.py`)
**Localização**: `core/pdf/footer_drawer.py`

**Classe**: `FooterDrawer`

**Desenha**:
- Área de assinaturas (Comandante/Técnico)
- Rodapé com numeração de páginas
- Texto "O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE"

### 9. **Construtores de Conteúdo**

#### Story Builder (`story_builder.py`)
**Localização**: `core/pdf/story_builder.py`

**Classe**: `StoryBuilder`

**Orquestra**:
- Tabela de equipamentos
- Seções de texto
- Tabela de atividades

#### Tables Builder (`tables_builder.py`)
**Localização**: `core/pdf/tables_builder.py`

**Classes**:
- `EquipmentTableBuilder`: Tabela de equipamentos
- `SectionsTableBuilder`: Seções de texto com quebra de página
- `ActivitiesTableBuilder`: Tabela de atividades dos técnicos

### 10. **Rotas da API** (`routes.py`)
**Localização**: Raiz do projeto

**Endpoints**:
- `POST /salvar-rascunho`: Salva rascunho no banco
- `GET /relatorios-salvos`: Lista relatórios do usuário
- `GET /relatorio/<id>`: Obtém relatório específico
- `PUT /atualizar-relatorio/<id>`: Atualiza relatório
- `DELETE /relatorio/<id>`: Remove relatório
- `POST /gerar-relatorio`: Gera e retorna PDF

### 11. **Utilitários** (`utils.py`)
**Localização**: Raiz do projeto e `core/pdf/utils.py`

**Funções**:
- `format_date_br()`: Formata datas para PT-BR
- `find_logo_bytes()`: Localiza bytes da logo
- `_norm_text()`: Normaliza texto para comparação

## 🔧 Como Customizar o PDF

### Modificar Fontes
1. Edite em `config.py`:
```python
FONT_REGULAR_PATH = 'novo/caminho/fonte.ttf'
FONT_BOLD_PATH = 'novo/caminho/fonte_bold.ttf'
```

### Ajustar Tamanhos de Fonte
```python
# Tamanhos base
TITLE_FONT_SIZE = 9.0
LABEL_FONT_SIZE = 10.0
VALUE_FONT_SIZE = 9.5

# Header específico
HEADER_TITLE_FONT_SIZE = 12.0  # Override absoluto
HEADER_VALUE_FONT_SIZE = -1.0  # Usa valor base
```

### Customizar Seções Específicas
```python
# Usar tamanho diferente para "SERVIÇO REALIZADO"
SECTION_USE_RESPONSE_SIZE = True
SECTION_SIZE_MULTIPLIER = 1.2  # 20% maior que response size

# Ou override absoluto
SECTION_FONT_SIZE_OVERRIDE = 10.0
```

## 📊 Fluxo de Geração de PDF

1. **Recebimento de Dados** → `routes.py`
2. **Validação** → `models.py` (Pydantic)
3. **Normalização** → `normalizers.py`
4. **Persistência** → `database.py`
5. **Construção do PDF**:
   - Configuração → `pdf_service.py`
   - Fontes → `font_manager.py`
   - Estilos → `styles_builder.py`
   - Header → `header_drawer.py`
   - Conteúdo → `story_builder.py` + `tables_builder.py`
   - Footer → `footer_drawer.py`
6. **Retorno** → PDF para download

## 🎨 Estrutura Visual do PDF

### Header
```
[LOGO] | RELATÓRIO DE SERVIÇO
       | NAVIO: [valor]    CLIENTE: [valor]
       | CONTATO: [valor]  OBRA: [valor]  
       | LOCAL: [valor]    OS: [valor]
```

### Corpo
- **Tabela de Equipamentos** (4 colunas)
- **Seções de Texto** (com quebra inteligente)
- **Tabela de Atividades** (7 colunas)

### Footer
```
[Área Assinatura Comandante] [Área Assinatura Técnico]
O SERVIÇO ACIMA FOI EXECUTADO SATISFATORIAMENTE
Página X
```

## 🔍 Localização Rápida de Funcionalidades

| Funcionalidade | Arquivo | Classe/Função |
|---------------|---------|---------------|
| Configuração geral | `config.py` | `Config` |
| Conexão com banco | `database.py` | `DatabaseManager` |
| Validação de dados | `models.py` | `ReportRequest`, `Activity` |
| Normalização | `normalizers.py` | `normalize_payload()` |
| Geração PDF | `pdf_service.py` | `PDFService` |
| Fontes | `font_manager.py` | `FontManager` |
| Estilos | `styles_builder.py` | `make_styles()` |
| Cabeçalho | `header_drawer.py` | `HeaderDrawer` |
| Rodapé | `footer_drawer.py` | `FooterDrawer` |
| Conteúdo | `story_builder.py` | `StoryBuilder` |
| Tabelas | `tables_builder.py` | Vários Builders |
| API Routes | `routes.py` | Várias funções |
| Formatação datas | `utils.py` | `format_date_br()` |

## 💡 Dicas de Manutenção

1. **Sempre use `config.py`** para ajustes visuais
2. **Teste quebras de página** com textos longos
3. **Verifique fonts** em diferentes sistemas
4. **Monitore validações** no `normalizers.py` para novos formatos de dados
5. **Use os multiplicadores** em vez de valores absolutos quando possível

Este sistema é altamente configurável e modular, permitindo ajustes precisos em cada componente do PDF sem afetar outros aspectos do sistema.