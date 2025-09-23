# PRONAV — Portal de Relatórios

---

## 📌 Visão Geral

Aplicação web para criação, armazenamento e geração de **PDFs de relatórios técnicos**.

* **Backend:** Flask
* **Banco:** SQLite (`reports.db`)
* **Geração de PDF:** ReportLab
* **Frontend:** `templates/index.html` + estáticos em `static/`

O repositório contém a aplicação pronta para execução local, endpoints principais para CRUD de relatórios e rotina de exportação para PDF.

---

## 🚀 Execução Rápida

### Criar e ativar ambiente virtual

```bash
python -m venv venv
# Windows PowerShell
env\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Iniciar aplicação

```bash
python app.py
```

Aplicação disponível em: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## 📂 Estrutura do Repositório

```
pronav-relatorios/
├─ app.py
├─ requirements.txt
├─ templates/
│  └─ index.html
├─ static/
│  └─ images/logo.png
├─ core/
│  ├─ config.py
│  ├─ database.py
│  ├─ models.py
│  ├─ normalizers.py
│  ├─ pdf_service.py
│  └─ routes.py
└─ reports.db
```

### Funções principais

* **app.py** → inicialização do Flask e configs.
* **core/routes.py** → endpoints HTTP.
* **core/pdf\_service.py** → geração de PDF (ReportLab).
* **core/normalizers.py** → padronização de payloads.
* **core/models.py** → modelos e validações (Pydantic).
* **core/database.py** → gerenciamento SQLite + migrações leves.

---

## 🌐 Endpoints Principais

* `GET /` → página inicial.
* `POST /salvar-rascunho` → salva rascunho (`status = draft`).
* `GET /relatorios-salvos` → lista relatórios.
* `GET /relatorio/<id>` → recupera relatório por ID.
* `PUT /atualizar-relatorio/<id>` → atualiza rascunho.
* `POST /gerar-relatorio` → gera e retorna PDF (header `X-Report-Id`).

🔎 Observação: o payload passa por **normalização** antes da validação e persistência.

---

## 📝 Payload Exemplo

```json
{
  "user_id":"tech1",
  "CLIENTE":"ACME S/A",
  "NAVIO":"NAVIO X",
  "CONTATO":"FULANO",
  "OBRA":"OB001",
  "LOCAL":"PORTO A",
  "OS":"000123",
  "EQUIPAMENTO":"RADAR XYZ",
  "FABRICANTE":"RADARCO",
  "MODELO":"R-1",
  "NUMERO_SERIE":"SN123",
  "PROBLEMA_RELATADO":"Falha intermitente",
  "SERVICO_REALIZADO":"Substituição de módulo",
  "RESULTADO":"OK",
  "PENDENCIAS":"",
  "MATERIAL_CLIENTE":"",
  "MATERIAL_PRONAV":"",
  "activities":[
     {"DATA":"2025-09-22","HORA_INICIO":"08:00","HORA_FIM":"09:00","TIPO":"Servico","KM":"0","DESCRICAO":"Serviço X","TECNICO1":"T1"}
  ]
}
```

---

## 📑 Modelos & Validações

* **Activity**

  * Campos obrigatórios: `DATA`, `TIPO`, `TECNICO1`.
  * Aceita `HORA` (legacy) ou `HORA_INICIO` e `HORA_FIM`.
* **ReportRequest**

  * Campos essenciais: `CLIENTE`, `NAVIO`, `CONTATO`, `EQUIPAMENTO`, `PROBLEMA_RELATADO`, `SERVICO_REALIZADO`, `activities`.
* **Normalização**

  * Ajusta **maiúsculas/minúsculas** e mapeia valores para formato esperado pelos validadores.

---

## 🗄️ Banco de Dados — Estrutura (SQLite)

**Tabela:** `reports`

Colunas principais:

* `id` (PK autoincrement)
* `user_id`
* `client`, `ship`, `contact`, `work`, `location`
* `os_number`, `equipment`, `manufacturer`, `model`, `serial_number`
* `reported_problem`, `service_performed`, `result`
* `pending_issues`, `client_material`, `pronav_material`
* `activities` (JSON/text)
* `equipments` (JSON/text)
* `city`, `state`
* `status`, `created_at`, `updated_at`

⚙️ **Migrations leves**: garantidas em `DatabaseManager.ensure_table_columns`.

---

## 🎨 Logo — Implementações

### 1️⃣ Arquivo estático (recomendado)

```html
<img src="{{ url_for('static', filename='images/logo.png') }}" alt="Logo Pronav" class="h-8" />
```

### 2️⃣ Base64 no contexto do template

```python
import os, base64
from flask import current_app, render_template

@app.route('/')
def index():
    logo_b64 = None
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_b64 = base64.b64encode(f.read()).decode('ascii')
    return render_template('index.html', logo_b64=logo_b64)
```

```html
<img src="{{ 'data:image/png;base64,' + logo_b64 if logo_b64 else url_for('static', filename='images/logo.png') }}" alt="Logo" class="h-8"/>
```

### 3️⃣ Inserção do logo no PDF

```python
from reportlab.platypus import Image as RLImage, Table, TableStyle, Spacer, Paragraph
import os

logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'logo.png')
if os.path.exists(logo_path):
    try:
        logo_img = RLImage(logo_path, width=square_side, height=square_side)
        header_table = Table([[logo_img, Paragraph('<b>PRONAV</b><br/>Portal de Relatórios', styles['TitleCenter'])]], colWidths=[square_side, usable_w - square_side])
        header_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story_local.insert(0, header_table)
        story_local.insert(1, Spacer(1, 0.08 * inch))
    except Exception:
        pass
```

---

## ✅ Trechos PR-Ready

### Substituição no **templates/index.html**

```diff
- <img src="https://.../pronav.png" alt="Logo" />
+ <img src="{{ url_for('static', filename='images/logo.png') }}" alt="Logo Pronav" class="h-8" />
```

### Inserção `logo_b64` em **routes.py**

```python
import os, base64
from flask import current_app, render_template

@app.route('/')
def index():
    logo_b64 = None
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_b64 = base64.b64encode(f.read()).decode('ascii')
    return render_template('index.html', logo_b64=logo_b64)
```

### Inserção do logo em **pdf\_service.py**

```python
from reportlab.platypus import Image as RLImage

logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'logo.png')
if os.path.exists(logo_path):
    try:
        logo_img = RLImage(logo_path, width=square_side, height=square_side)
        header_table = Table([[logo_img, Paragraph('<b>PRONAV</b><br/>Portal de Relatórios', styles['TitleCenter'])]], colWidths=[square_side, usable_w - square_side])
        header_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story_local.insert(0, header_table)
        story_local.insert(1, Spacer(1, 0.08 * inch))
    except Exception:
        pass
```

---

## 📋 Checklist de Alterações

* Mudanças **atômicas** (um objetivo por PR).
* Validar payloads com **normalizers** antes de mexer nos models.
* Não alterar **schema do DB** sem migração.
* Testar frontend após modificação de templates.

### PR mínimo deve conter:

* Patch unificado.
* Teste manual descrito.
* Commit + descrição do impacto.
* Rollback simples documentado.

---

## 🔧 Teste Manual Rápido

1. Colocar `static/images/logo.png`.
2. Substituir template por `url_for`.
3. `python app.py` → acessar [http://127.0.0.1:5000/](http://127.0.0.1:5000/).
4. Preencher relatório + gerar PDF.
5. Verificar logo no site e no PDF.

---

## ⚠️ Observações Finais

* PDF já tem setup de fontes — **não sobrescrever**.
* Rotas têm tratamento de erros — **preservar handlers**.
* Normalização aceita diferentes formatos de payload — **sempre testar**.

---
