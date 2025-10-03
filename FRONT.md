# 🌐 PARTE 3: FRONTEND (Interface Web)

## 17. **Arquitetura Completa do Frontend**

### Tecnologias e Estrutura
```html
<!-- Estrutura Principal Single Page Application (SPA) -->
index.html
├── 🎨 CSS Variables System (Design System)
├── 🧭 Header Navigation (Sticky)
├── 📄 Main Content Area
│   ├── 👤 Novo Relatório View (Formulário Principal)
│   └── 💾 Relatórios Salvos View (Listagem)
├── 🎪 Modal System (Sucesso/Erro/Confirmação)
└── 📱 Footer Informativo
```

### Dependências Externas
```javascript
// CDN Resources
- Tailwind CSS 3.x          // Framework de utilitários CSS
- Font Awesome 6.4.0        // Sistema de ícones
- Google Fonts (Inter)      // Tipografia moderna
- JavaScript ES6+           // Lógica da aplicação (vanilla)
```

## 18. **Sistema de Design e Variáveis CSS**

### Palette de Cores Corporativa
```css
:root {
  /* Cores Principais Pronav */
  --pronav-blue: #035acd;           /* Azul primário */
  --pronav-dark-blue: #023d8c;      /* Azul escuro (header/footer) */
  --pronav-light-blue: #468cf5;     /* Azul claro (gradientes) */
  
  /* Sistema de Cores Neutras */
  --pronav-gray: #E0E7E9;           /* Cinza de fundo */
  --pronav-light-gray: #F8FAFC;     /* Cinza claro (inputs) */
  --pronav-text: #334155;           /* Cor principal do texto */
  --pronav-border: #E2E8F0;         /* Bordas e divisórias */
  
  /* Cores Semânticas */
  --pronav-success: #10B981;        /* Confirmações e sucesso */
  --pronav-red: #EF4444;            /* Erros e ações destrutivas */
  --pronav-saved: #3B82F6;          /* Ações secundárias */
  
  /* Componentes Visuais */
  --pronav-card-bg: #fff;           /* Fundo de cartões */
  --pronav-shadow: rgba(0,0,0,0.06); /* Sombras suaves */
}
```

### Sistema de Tipografia
```css
/* Hierarquia de Fontes */
font-family: 'Inter', sans-serif;    /* Fonte principal */

/* Pesos Utilizados */
font-weight: 300;   /* Light - textos secundários */
font-weight: 400;   /* Regular - corpo do texto */
font-weight: 500;   /* Medium - labels importantes */
font-weight: 600;   /* SemiBold - títulos e botões */
font-weight: 700;   /* Bold - seções e labels críticos */

/* Escala de Tamanhos */
text-xs:     0.75rem    /* 12px - textos auxiliares */
text-sm:     0.875rem   /* 14px - pequenos labels */
text-base:   1rem       /* 16px - corpo principal */
text-lg:     1.125rem   /* 18px - títulos menores */
```

## 19. **Componentes de Interface Principais**

### Header com Navegação Sticky
```html
<header class="header text-white w-full py-3 px-4 flex flex-col md:flex-row items-center justify-between sticky top-0 z-50">
  <!-- Logo e Identificação Visual -->
  <div class="flex items-center space-x-3">
    <div class="w-10 h-10 rounded-lg bg-white bg-opacity-10 flex items-center justify-center">
      <img src="pronav.png" alt="Logo Pronav" class="h-8" />
    </div>
    <div>
      <h1 class="text-lg font-bold">Portal de Relatórios</h1>
      <p class="text-xs font-light opacity-80">Pronav Marine</p>
    </div>
  </div>

  <!-- Sistema de Navegação por Abas -->
  <div class="flex items-center space-x-3">
    <button id="new-report-nav" class="nav-item active">
      <i class="fas fa-plus mr-2"></i>Novo Relatório
    </button>
    <button id="saved-reports-nav" class="nav-item">
      <i class="fas fa-folder mr-2"></i>Relatórios Salvos
    </button>
  </div>
</header>
```

### Sistema de Cartões (Cards)
```css
.card {
  background: var(--pronav-card-bg);
  border-radius: 0.6rem;           /* Cantos arredondados consistentes */
  padding: 0.75rem;                /* Espaçamento interno padrão */
  box-shadow: 0 8px 18px -6px var(--pronav-shadow); /* Sombra suave */
}
```

### Botões com Hierarquia Visual
```css
/* Botão Primário - Ação Principal */
.btn-primary {
  background: linear-gradient(90deg, var(--pronav-blue), var(--pronav-light-blue));
  color: #fff;
  font-weight: 600;
  padding: .36rem .7rem;
  border-radius: 9999px;           /* Forma "pill" completamente arredondada */
  font-size: 0.92rem;
  border: none;
}

/* Botão Secundário - Ações de Suporte */
.btn-secondary {
  background: var(--pronav-saved);
  color: #fff;
  padding: .36rem .7rem;
  border-radius: 9999px;
  font-size: 0.92rem;
  border: none;
}

/* Botão de Ação Destrutiva */
.btn-delete {
  background: var(--pronav-red);
  color: #fff;
  padding: .36rem .7rem;
  border-radius: 9999px;
  border: none;
}

/* Botões de Ícone para Ações Compactas */
.btn-icon {
  border-radius: 8px;
  padding: 0.4rem;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  height: 38px;
  box-shadow: 0 2px 6px rgba(2,6,23,0.04);
}
```

## 20. **Sistema de Formulários Inteligente**

### Campos de Formulário com Validação
```css
.form-label {
  font-weight: 700;
  margin-bottom: .25rem;
  font-size: 0.9rem;
}

.form-control {
  border: 1px solid var(--pronav-border);
  border-radius: .5rem;
  padding: .36rem .5rem;
  width: 100%;
  background: var(--pronav-light-gray);
  min-height: 36px;                /* Altura mínima para acessibilidade */
  font-size: 0.94rem;
}

/* Estados dos Campos */
.form-control:focus {
  outline: none;
  border-color: var(--pronav-blue);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(3,90,205,.06); /* Anel de foco sutil */
}

.form-control.error {
  border-color: var(--pronav-red); /* Feedback visual de erro */
}

/* Campos com Auto-Uppercase */
.uppercase-input {
  text-transform: uppercase;       /* Para padronização de dados */
}
```

### Grid System Responsivo
```css
/* Layout Base Mobile-First */
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }

/* Tablet (≥640px) */
@media (min-width: 640px) {
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* Desktop (≥1024px) - Sistema de 12 colunas para atividades */
.activity-item.grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

@media (min-width: 640px) {
  .activity-item.grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .activity-item.grid {
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 0.6rem;
  }
  
  /* Sistema de span para grid de 12 colunas */
  .c2 { grid-column: span 2; }
  .c3 { grid-column: span 3; }
  .c4 { grid-column: span 4; }
  .c6 { grid-column: span 6; }
  .c12 { grid-column: 1 / -1; }
}
```

## 21. **Sistema de Atividades Dinâmicas**

### Componente de Atividade Individual
```html
<div class="activity-item grid">
  <!-- Botão de Remover com Posicionamento Absoluto -->
  <button class="remove-activity-btn" title="Remover atividade">
    <i class="fas fa-times"></i>
  </button>

  <!-- Grid de 12 Colunas para Organização Complexa -->
  <div class="c2">
    <label class="form-label block">Data</label>
    <input name="DATA" required class="form-control" type="date">
  </div>
  
  <div class="c2">
    <label class="form-label block">Hora Início</label>
    <input name="HORA_INICIO" required class="form-control" type="time">
  </div>

  <!-- ... mais campos organizados no grid ... -->

  <!-- Sistema de Descrição Automática -->
  <div class="c12">
    <div class="desc-prefix hidden" aria-hidden="true"></div>
    <div class="field-help">
      Descrição será gerada pelo sistema. Preencha Motivo/Origem/Destino conforme necessário.
    </div>
  </div>

  <!-- Campos Condicionais por Tipo de Atividade -->
  <div class="c12" style="display:flex;gap:8px;">
    <div style="flex:1">
      <label class="form-label block">Motivo (apenas Período de Espera)</label>
      <input name="MOTIVO" class="form-control" type="text" disabled>
    </div>
    <div style="flex:1;display:flex;gap:8px;">
      <div style="flex:1">
        <label class="form-label block">Origem</label>
        <input name="ORIGEM" class="form-control" type="text" disabled>
      </div>
      <div style="flex:1">
        <label class="form-label block">Destino</label>
        <input name="DESTINO" class="form-control" type="text" disabled>
      </div>
    </div>
  </div>

  <!-- Seção de Técnicos com Layout Específico -->
  <div class="c12">
    <div class="tech-row">
      <div class="tech-box">
        <label class="form-label">Técnico 1</label>
        <input name="TECNICO1" required class="form-control" type="text">
      </div>
      <div class="tech-box">
        <label class="form-label">Técnico 2 (opcional)</label>
        <input name="TECNICO2" class="form-control" type="text">
      </div>
    </div>
  </div>
</div>
```

### Lógica de Regras por Tipo de Atividade
```javascript
function applyTipoRulesToActivity(activityEl) {
  const tipoEl = activityEl.querySelector('[name="TIPO"]');
  const kmEl = activityEl.querySelector('[name="KM"]');
  const motivoEl = activityEl.querySelector('[name="MOTIVO"]');
  const origemEl = activityEl.querySelector('[name="ORIGEM"]');
  const destinoEl = activityEl.querySelector('[name="DESTINO"]');
  const prefixEl = activityEl.querySelector('.desc-prefix');

  const t = (tipoEl.value || '').toString().trim().toLowerCase();

  // Sistema de Tipos Bloqueados para KM
  const KM_BLOCKED_TYPES = [
    'mão-de-obra técnica', 'mão-de-obra-técnica', 
    'período de espera', 'viagem aérea', 'translado'
  ].map(s => s.toLowerCase());

  // Sistema de Tipos de Viagem
  const TRAVEL_TYPES = [
    'viagem terrestre', 'viagem aérea', 'translado'
  ].map(s => s.toLowerCase());

  // Lógica de KM (habilitar/desabilitar baseado no tipo)
  if (KM_BLOCKED_TYPES.includes(t)) {
    kmEl.value = '';
    kmEl.disabled = true;
    kmEl.removeAttribute('required');
  } else {
    kmEl.disabled = false;
    kmEl.setAttribute('required','required');
  }

  // Lógica de Descrição Automática
  let descVal = '';
  if (t === 'mão-de-obra técnica' || t === 'mão de obra técnica') {
    descVal = 'Mão-de-Obra-Técnica';
  } else if (t === 'período de espera') {
    if (motivoEl && !motivoEl.disabled && motivoEl.value.trim()) {
      descVal = motivoEl.value.trim();
    }
  } else if (TRAVEL_TYPES.includes(t)) {
    const o = (origemEl && origemEl.value) ? origemEl.value.trim() : '';
    const d = (destinoEl && destinoEl.value) ? destinoEl.value.trim() : '';
    if (o || d) descVal = `${o} x ${d}`;
  }

  // Aplicação da Descrição
  if (descVal) {
    prefixEl.textContent = descVal;
    prefixEl.classList.remove('hidden');
  } else {
    prefixEl.textContent = '';
    prefixEl.classList.add('hidden');
  }
}
```

## 22. **Sistema de Estado e Gerenciamento de Dados**

### Variáveis de Estado Global
```javascript
// Estado da Aplicação
let firebaseAvailable = false;      // Compatibilidade futura com Firebase
let userId = 'anonymous_user';      // Identificação do usuário
let currentDocRef = null;           // Referência do documento atual

// Referências de DOM Principais
const reportForm = document.getElementById('report-form');
const activitiesContainer = document.getElementById('activities-container');
const equipmentsContainer = document.getElementById('equipments-container');
```

### Sistema de Normalização de Dados
```javascript
// Normalizador de Texto para Comparações
const norm = s => (s || '')
  .toString()
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')   // Remove acentos
  .replace(/[-_]/g, ' ')             // Normaliza separadores
  .replace(/\s+/g, ' ')              // Colapsa múltiplos espaços
  .trim()
  .toLowerCase();
```

### Construção do Payload para API
```javascript
function buildPayload() {
  const fd = new FormData(reportForm);
  const payload = {
    // Dados Básicos do Relatório
    CLIENTE: fd.get('CLIENTE') || '',
    NAVIO: fd.get('NAVIO') || '',
    CONTATO: fd.get('CONTATO') || '',
    OBRA: fd.get('OBRA') || '',
    LOCAL: fd.get('LOCAL') || '',
    OS: fd.get('OS') || '',
    
    // Equipamento Principal
    EQUIPAMENTO: fd.get('EQUIPAMENTO') || '',
    FABRICANTE: fd.get('FABRICANTE') || '',
    MODELO: fd.get('MODELO') || '',
    NUMERO_SERIE: fd.get('NUMERO_SERIE') || '',
    
    // Descrições Técnicas
    PROBLEMA_RELATADO: fd.get('PROBLEMA_RELATADO') || '',
    SERVICO_REALIZADO: fd.get('SERVICO_REALIZADO') || '',
    RESULTADO: fd.get('RESULTADO') || '',
    PENDENCIAS: fd.get('PENDENCIAS') || '',
    
    // Materiais
    MATERIAL_CLIENTE: fd.get('MATERIAL_CLIENTE') || '',
    MATERIAL_PRONAV: fd.get('MATERIAL_PRONAV') || '',
    
    // Estruturas Complexas
    user_id: userId || 'anonymous_user',
    activities: [],
    EQUIPAMENTOS: []
  };

  // Processamento de Equipamentos Adicionais
  const equipItems = equipmentsContainer.querySelectorAll('.equip-item');
  equipItems.forEach(el => {
    const equip = el.querySelector('[data-key="equip"]')?.value || '';
    const fab = el.querySelector('[data-key="fabricante"]')?.value || '';
    const mod = el.querySelector('[data-key="modelo"]')?.value || '';
    const sn = el.querySelector('[data-key="sn"]')?.value || '';
    
    if (equip || fab || mod || sn) {
      payload.EQUIPAMENTOS.push({
        equipamento: equip,
        fabricante: fab,
        modelo: mod,
        numero_serie: sn
      });
    }
  });

  // Processamento de Atividades com Regras Complexas
  const items = activitiesContainer.querySelectorAll('.activity-item');
  items.forEach(it => {
    const tipoVal = (it.querySelector('[name="TIPO"]')?.value || '').trim();
    
    // Aplicação das regras de negócio para cada atividade
    const activityData = {
      DATA: it.querySelector('[name="DATA"]')?.value || '',
      HORA_INICIO: it.querySelector('[name="HORA_INICIO"]')?.value || '',
      HORA_FIM: it.querySelector('[name="HORA_FIM"]')?.value || '',
      TIPO: tipoVal,
      // ... mais campos com lógica específica
    };
    
    payload.activities.push(activityData);
  });

  return payload;
}
```

## 23. **Sistema de Validação em Tempo Real**

### Validação Completa do Formulário
```javascript
function validateForm() {
  let ok = true;
  
  // Validação de Campos Obrigatórios
  const required = reportForm.querySelectorAll('[required]');
  required.forEach(f => {
    if (f.disabled) return;
    if (!f.value || f.value.toString().trim() === '') {
      f.classList.add('error');
      ok = false;
    } else {
      f.classList.remove('error');
    }
  });

  // Validação de Pelo Menos Uma Atividade
  if (activitiesContainer.children.length === 0) {
    showModal(errorModal, 'Adicione pelo menos uma atividade.');
    ok = false;
  }

  // Validação de Horários nas Atividades
  const activities = activitiesContainer.querySelectorAll('.activity-item');
  activities.forEach(item => {
    const h1 = item.querySelector('[name="HORA_INICIO"]');
    const h2 = item.querySelector('[name="HORA_FIM"]');
    if (!h1.value || !h2.value) {
      if (h1) h1.classList.add('error');
      if (h2) h2.classList.add('error');
      ok = false;
    }
  });

  return ok;
}
```

## 24. **Sistema de Modais e Feedback**

### Arquitetura de Modais
```html
<!-- Modal de Sucesso -->
<div id="success-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden items-center justify-center p-4 z-50">
  <div class="bg-white rounded-xl p-6 shadow-xl max-w-sm w-full text-center">
    <div class="mb-3"><i class="fas fa-check-circle text-green-500 text-3xl"></i></div>
    <h3 class="font-bold mb-1">Sucesso</h3>
    <p id="success-text" class="text-gray-600 mb-3">Operação realizada com sucesso.</p>
    <button id="close-modal-btn" class="btn-primary px-4 py-1 rounded-full">Fechar</button>
  </div>
</div>

<!-- Modal de Confirmação para Ações Destrutivas -->
<div id="confirm-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden items-center justify-center p-4 z-50">
  <div class="bg-white rounded-xl p-6 shadow-xl max-w-sm w-full text-center">
    <div class="mb-3"><i class="fas fa-question-circle text-yellow-500 text-3xl"></i></div>
    <h3 class="font-bold mb-1">Confirmação</h3>
    <p id="confirm-message" class="text-gray-600 mb-3">Confirmação necessária.</p>
    <div class="flex justify-center space-x-3">
      <button id="confirm-cancel-btn" class="px-4 py-1 rounded-full bg-gray-200">Cancelar</button>
      <button id="confirm-ok-btn" class="px-4 py-1 rounded-full btn-delete text-white">OK</button>
    </div>
  </div>
</div>
```

### Sistema de Gerenciamento de Modais
```javascript
function showModal(modal, message = '') {
  if (!modal) return;
  if (message) {
    const selector = modal.querySelector('#confirm-message, #error-message, #success-text');
    if (selector) selector.textContent = message;
  }
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  document.body.style.overflow = 'hidden'; // Previne scroll do body
}

function hideModal(modal) {
  if (!modal) return;
  modal.classList.add('hidden');
  modal.classList.remove('flex');
  document.body.style.overflow = '';
}
```

## 25. **Sistema de Equipamentos Dinâmicos**

### Componente de Equipamento Adicional
```javascript
function addEquipment(data = null) {
  const div = document.createElement('div');
  div.className = 'equip-item';
  div.innerHTML = `
    <input class="form-control equip-mini uppercase-input" placeholder="Equipamento" data-key="equip" />
    <input class="form-control equip-mini uppercase-input" placeholder="Fabricante" data-key="fabricante" />
    <input class="form-control equip-mini uppercase-input" placeholder="Modelo" data-key="modelo" />
    <input class="form-control equip-mini uppercase-input" placeholder="Nº Série" data-key="sn" />
    <button type="button" class="equip-remove" title="Remover equipamento">&times;</button>
  `;
  
  equipmentsContainer.appendChild(div);
  
  // Sistema de Auto-Uppercase
  div.querySelectorAll('.uppercase-input').forEach(inp => {
    inp.addEventListener('input', (e) => {
      const pos = inp.selectionStart;
      inp.value = inp.value.toUpperCase();
      try { inp.setSelectionRange(pos, pos); } catch(e){}
    });
  });

  return div;
}
```

## 26. **Integração com Backend API**

### Endpoints Consumidos
```javascript
// Sistema de Rascunhos
POST   /salvar-rascunho
PUT    /atualizar-relatorio/:id
GET    /relatorios-salvos?user_id=:userId
GET    /relatorio/:id
DELETE /relatorio/:id

// Geração de PDF
POST   /gerar-relatorio
```

### Fluxo de Geração de PDF
```javascript
async function generateReport() {
  if (!validateForm()) {
    showModal(errorModal, 'Preencha os campos obrigatórios.');
    return;
  }
  
  submitBtn.disabled = true;
  const payload = buildPayload();
  
  try {
    const res = await fetch('/gerar-relatorio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) throw new Error('Erro na geração do PDF');
    
    // Download Automático do PDF
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Nome do Arquivo com Metadados
    const shipSafe = (payload.NAVIO || 'Geral').replace(/\s+/g,'_');
    const date = new Date().toISOString().split('T')[0];
    a.download = `PRONAV_${date}_${shipSafe}.pdf`;
    
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    
    showModal(successModal, 'Relatório gerado com sucesso!');
    
  } catch (err) {
    showModal(errorModal, 'Erro ao gerar relatório: ' + err.message);
  } finally {
    submitBtn.disabled = false;
  }
}
```

## 27. **Sistema de Relatórios Salvos**

### Componente de Listagem Compacta
```html
<div class="activity-item compact">
  <div class="meta">
    <p title="CLIENTE - NAVIO">CLIENTE - NAVIO</p>
    <p class="meta-sub">Atualizado em: 01/01/2024 10:30</p>
  </div>
  <div class="actions" role="group" aria-label="Ações do relatório">
    <button class="btn-icon edit edit-report-btn" data-id="123"><i class="fas fa-edit"></i></button>
    <button class="btn-icon download download-report-btn" data-id="123"><i class="fas fa-download"></i></button>
    <button class="btn-icon delete delete-report-btn" data-id="123"><i class="fas fa-trash-alt"></i></button>
  </div>
</div>
```

### Carregamento e Renderização de Salvos
```javascript
function renderSavedReports(reports) {
  savedReportsList.innerHTML = '';
  
  if (!reports || reports.length === 0) {
    noReportsMessage.classList.remove('hidden');
    return;
  }
  
  noReportsMessage.classList.add('hidden');
  
  reports.forEach(r => {
    const div = document.createElement('div');
    div.className = 'activity-item compact';
    div.innerHTML = `
      <div class="meta">
        <p title="${r.CLIENTE} — ${r.NAVIO}">${r.CLIENTE} - ${r.NAVIO}</p>
        <p class="meta-sub">Atualizado em: ${formatDateTimeISO(r.updated_at)}</p>
      </div>
      <div class="actions">
        <button class="btn-icon edit edit-report-btn" data-id="${r.id}"><i class="fas fa-edit"></i></button>
        <button class="btn-icon download download-report-btn" data-id="${r.id}"><i class="fas fa-download"></i></button>
        <button class="btn-icon delete delete-report-btn" data-id="${r.id}"><i class="fas fa-trash-alt"></i></button>
      </div>
    `;
    
    savedReportsList.appendChild(div);
  });
}
```

## 28. **Sistema de Responsividade**

### Breakpoints e Adaptações
```css
/* Mobile First (default) */
.activity-item.grid {
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

/* Tablet (≥640px) */
@media (min-width: 640px) {
  .activity-item.grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
  
  .form-actions {
    justify-content: flex-end; /* Alinha ações à direita */
  }
}

/* Desktop (≥1024px) */
@media (min-width: 1024px) {
  .activity-item.grid {
    grid-template-columns: repeat(12, minmax(0, 1fr));
  }
  
  .header {
    flex-direction: row; /* Layout horizontal */
  }
}
```

### Layout de Formulários Adaptativo
```html
<!-- Grid que se adapta de 1 coluna (mobile) para 2 colunas (desktop) -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
  <div>
    <label for="CLIENTE" class="form-label">Cliente</label>
    <input id="CLIENTE" name="CLIENTE" class="form-control" />
  </div>
  <div>
    <label for="NAVIO" class="form-label">Embarcação / Navio</label>
    <input id="NAVIO" name="NAVIO" class="form-control" />
  </div>
</div>
```

## 29. **Sistema de Acessibilidade**

### ARIA Labels e Roles
```html
<div class="actions" role="group" aria-label="Ações do relatório">
  <button class="btn-icon edit" aria-label="Editar relatório">
    <i class="fas fa-edit" aria-hidden="true"></i>
  </button>
</div>
```

### Navegação por Teclado
```javascript
// Foco automático em novos elementos
function addActivity(isInitial = false, data = null) {
  // ... criação da atividade ...
  
  if (!isInitial && !data) {
    div.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const firstInput = div.querySelector('[name="DATA"]');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 260);
    }
  }
}
```

## 30. **Otimizações de Performance**

### Event Delegation para Elementos Dinâmicos
```javascript
// Um único listener para todos os botões de ação
savedReportsList.addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  
  const id = btn.dataset.id;
  
  if (btn.classList.contains('edit-report-btn')) {
    loadReportFromBackend(id);
  } else if (btn.classList.contains('download-report-btn')) {
    downloadReport(id);
  } else if (btn.classList.contains('delete-report-btn')) {
    deleteReportBackend(id);
  }
});
```

### Limite de Atividades para Performance
```javascript
function addActivity(isInitial = false) {
  const count = activitiesContainer.querySelectorAll('.activity-item').length;
  
  // Limite de 30 atividades para performance
  if (count >= 30 && !isInitial) {
    showModal(errorModal, 'Máximo de 30 atividades permitidas.');
    return;
  }
  
  // ... criação da atividade ...
}
```

## 31. **Fluxos de Trabalho Principais**

### Fluxo de Criação de Relatório
```
1. Preenchimento de Dados Básicos
   ↓
2. Adição de Equipamentos (Opcional)
   ↓
3. Descrição do Serviço (Problema, Serviço, Resultado, Pendências)
   ↓
4. Adição de Atividades (Múltiplas com regras específicas)
   ↓
5. Revisão e Validação
   ↓
6. Geração de PDF ou Salvamento como Rascunho
```

### Fluxo de Gestão de Rascunhos
```
1. Navegação para "Relatórios Salvos"
   ↓
2. Carregamento Assíncrono da Lista
   ↓
3. Ações por Item:
   - 📝 Editar: Carrega no formulário principal
   - ⬇️ Baixar: Gera PDF diretamente
   - 🗑️ Deletar: Remove com confirmação
```

## 32. **Sistema de Tratamento de Erros**

### Camadas de Tratamento
```javascript
async function loadReportFromBackend(id) {
  try {
    const res = await fetch(`/relatorio/${id}`);
    if (!res.ok) throw new Error('Erro ao carregar relatório');
    
    const data = await res.json();
    // ... processamento dos dados ...
    
  } catch (error) {
    console.error('Erro no carregamento:', error);
    showModal(errorModal, 'Erro ao carregar relatório: ' + error.message);
  }
}
```

### Fallbacks e Estados de Erro
```javascript
function loadSavedReports() {
  savedReportsList.innerHTML = '';
  noReportsMessage.classList.remove('hidden');
  
  try {
    const res = await fetch(`/relatorios-salvos?user_id=${userId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    const reports = await res.json();
    renderSavedReports(reports);
    
  } catch (error) {
    savedReportsList.innerHTML = `
      <div class="p-2 text-sm text-red-600">
        Erro ao carregar relatórios: ${error.message}
      </div>
    `;
  }
}
```

---

Este frontend representa uma aplicação SPA moderna e robusta que oferece:

- ✅ **Interface intuitiva** para criação complexa de relatórios
- ✅ **Validação em tempo real** com feedback visual
- ✅ **Sistema de atividades dinâmico** com regras de negócio
- ✅ **Gestão completa** de rascunhos e relatórios
- ✅ **Responsividade** total across dispositivos
- ✅ **Acessibilidade** e navegação por teclado
- ✅ **Performance otimizada** para grandes formulários
- ✅ **Integração seamless** com backend Flask

A arquitetura modular permite fácil manutenção e extensão para novas funcionalidades.