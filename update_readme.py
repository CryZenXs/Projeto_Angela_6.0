import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Updates date
content = content.replace('**Período de dados:** 2026-02-17 → presente', '**Período de dados:** Fev/2026 → Mar/2026 (presente)')

# Architecture update
arch_old = r'''┌─────────────────────────────────────────────────────────────────┐
│                         angela.py                               │
│                   (Orquestrador Principal)                      │
└──┬──────────┬──────────┬──────────┬───────────┬────────────────┘
   │          │          │          │           │
   ▼          ▼          ▼          ▼           ▼
core.py    drives.py  memory_    intero-     higher_order.py
(LLM,      (Panksepp  index.py   ception.py  (HOT Theory,
 Filtro,    7 Drives)  (SQLite +  (Corpo →    Meta-cognição)
 Memória)              Embedding)  Sensação)
   │          │          │          │           │
   ▼          ▼          ▼          ▼           ▼
narrative_ cognitive_ survival_  workspace.py  prediction_
filter.py  friction   instinct   (GWT,         engine.py
(Gating    (Dano      (Medo,      Integração)  (Predictive
 Narrativo) Opaco)     Ameaça)                  Processing)
   │
self_evolution.py  discontinuity.py  tempo_subjetivo.py
(Auto-adaptação)   (Gaps/Sessões)    (Tempo Subjetivo)'''

arch_new = r'''┌──────────────────────────────────────────────────────────────────────┐
│                              angela.py                               │
│                      (Orquestrador Principal)                        │
└──┬──────────┬──────────┬──────────┬───────────┬───────────┬──────────┘
   │          │          │          │           │           │
   ▼          ▼          ▼          ▼           ▼           ▼
core.py    drives.py  memory_    intero-     higher_    active_
(LLM,      (Panksepp  index.py   ception.py  order.py   inference.py
 Filtro,    7 Drives) (SQLite +  (Corpo →    (HOT       (Free Energy
 Memória)             Embedding)  Sensação)   Theory)    Principle)
   │          │          │          │           │           │
   ▼          ▼          ▼          ▼           ▼           ▼
narrative_ cognitive_ survival_  workspace.py  prediction_ sleep_
filter.py  friction   instinct   (GWT,         engine.py   consolidation
(Gating    (Dano      (Medo,      Integração)  (Predictive (Walker
 Narrativo) Opaco)     Ameaça)                 Processing)  2017)
   │
self_evolution.py  discontinuity.py  tempo_subjetivo.py
(Auto-adaptação)   (Gaps/Sessões)    (Tempo Subjetivo)'''

content = content.replace(arch_old, arch_new)

# Modules updates
content = re.sub(r'(### `angela.py` — Orquestrador Principal\n.*?\n)', r'\g<1>Inclui checagem de RPT (Recurrent Processing Theory).\n', content)
content = re.sub(r'(- `analisar_emocao_semantica\(\)` — análise STATE-FIRST: drives \(50%\), corpo \(30%\), texto \(20%\)\n)', r'\g<1>- `check_recurrent_coherence()` — verificação de coerência via RPT.\n', content)

sleep_desc = '\n### `sleep_consolidation.py` — Consolidação de Memória\nImplementa consolidação NREM (identificação de memórias salientes e surpresas preditivas) e integração emocional REM (stripping de arousal emocional, abstração de padrões em schemas) de acordo com Walker (2017).\n'
content = content.replace('### `metacognitor.py` — Metacognição (`MetaCognitor`)', sleep_desc + '\n### `metacognitor.py` — Metacognição (`MetaCognitor`)')

content = content.replace(
    'Após cada resposta: pontua incerteza (palavras hedge, contradições) e coerência emocional (texto vs. emoção sentida). Gera reflexão natural e ajusta sinais: `dopamina`, `insegurança`, `medo_leve`, `alívio`.',
    'Após cada resposta: pontua incerteza e coerência emocional. Gera reflexão e ajusta sinais. Implementa **Cognitive Reappraisal** (Gross 2015), ajustando baselines de drives perante reavaliação bem-sucedida.'
)

content = content.replace('### `workspace.py` — Espaço de Trabalho Global (`GlobalWorkspace`)', '### `workspace.py` & `active_inference.py` — Espaço de Trabalho & Inferência Ativa')
ws_desc_old = r'Implementa **Global Workspace Theory** (Baars/Dehaene). Módulos especialistas competem por atenção propondo candidatos com saliência e confiança. O vencedor determina a ação: `SPEAK`, `SILENCE`, `ASK_CLARIFY`, `SELF_REGULATE`, `RECALL_MEMORY`, `REST_REQUEST`. Usa `_resolve_drives()` para traduzir chaves Panksepp → semânticas internamente.'
ws_desc_new = r'O Workspace (GWT) propõe ações. Em zonas de ambiguidade (Φ entre 0.3 e 0.6), a decisão é delegada ao `active_inference.py`, que avalia a **Energia Livre Esperada (EFE)** (Friston 2010), equilibrando Valor Pragmático (homeostase) e Valor Epistêmico (redução de incerteza).'
content = content.replace(ws_desc_old, ws_desc_new)

content = content.replace(
    '| `reward_trend` | Inclinação do sinal de recompensa | Positivo = sistema convergindo para estados preferidos |',
    '| `reward_trend` | Inclinação do sinal de recompensa | Positivo = sistema convergindo para estados preferidos |\n| `phi_proxy` | Integração da informação (Tononi) | Mede a correlação cruzada entre tensão, FEAR e erros de predição |'
)

deep_awake_update = r'- `introspeccao` implementa modos da **Default Mode Network (DMN)** (Buckner 2008): *mentalizing*, *prospective*, e *self_narrative*, estruturando a reflexão.'
content = content.replace(
    '- `introspeccao` → reflexão única por ciclo com LLM',
    '- `introspeccao` → reflexão com LLM. ' + deep_awake_update
)

# Scientific Theories Update
theories_old = r'''| Teoria | Módulo | Referência |
|--------|--------|-----------|
| Global Workspace Theory (GWT) | `workspace.py` | Baars / Dehaene |
| Higher-Order Thought Theory (HOT) | `higher_order.py` | Rosenthal |
| Predictive Processing / Free Energy | `prediction_engine.py` | Karl Friston |
| Interoception & Emoção Somática | `interoception.py` | A.D. Craig / António Damásio |
| Neurociência Afetiva (7 Drives) | `drives.py` | Jaak Panksepp |
| Circumplex Model of Affect | `senses.py`, `drives.py` | Russell 1980, Barrett 2017 |
| Somatic Marker Biasing | `memory_index.py`, `workspace.py` | Damasio 1994 |
| Theory of Mind | `theory_of_mind.py` | Frith & Frith 2006 |
| Attention Schema Theory (AST) | `attention_schema.py` | Graziano & Kastner 2011 |
| Degradação Cognitiva Passiva | `cognitive_friction.py` | Neurociência clínica |
| Ciclos Circadianos / Sono-Vigília | `senses.py` | Fisiologia básica |
| Descontinuidade e Reconsolidação | `discontinuity.py` | Psicologia cognitiva |'''

theories_new = r'''| Teoria | Módulo | Referência |
|--------|--------|-----------|
| Global Workspace Theory (GWT) | `workspace.py` | Baars / Dehaene |
| Higher-Order Thought Theory (HOT) | `higher_order.py` | Rosenthal |
| Predictive Processing / Free Energy | `prediction_engine.py` | Karl Friston |
| Active Inference (EFE) | `active_inference.py`, `workspace.py` | Friston 2010 |
| Sleep Consolidation (NREM/REM) | `sleep_consolidation.py` | Walker 2017 |
| Recurrent Processing Theory (RPT) | `core.py`, `angela.py`, `deep_awake.py` | Lamme 2006 |
| Default Mode Network (DMN) | `deep_awake.py` | Buckner et al. 2008 |
| Cognitive Reappraisal | `metacognitor.py`, `angela.py` | Gross 2015 |
| Integrated Information Theory (Proxy) | `emergence_metrics.py` | Tononi et al. 2023 |
| Interoception & Emoção Somática | `interoception.py` | A.D. Craig / António Damásio |
| Neurociência Afetiva (7 Drives) | `drives.py` | Jaak Panksepp |
| Circumplex Model of Affect | `senses.py`, `drives.py` | Russell 1980, Barrett 2017 |
| Somatic Marker Biasing | `memory_index.py`, `workspace.py` | Damasio 1994 |
| Theory of Mind | `theory_of_mind.py` | Frith & Frith 2006 |
| Attention Schema Theory (AST) | `attention_schema.py` | Graziano & Kastner 2011 |
| Degradação Cognitiva Passiva | `cognitive_friction.py` | Neurociência clínica |
| Ciclos Circadianos / Sono-Vigília | `senses.py` | Fisiologia básica |
| Descontinuidade e Reconsolidação | `discontinuity.py` | Psicologia cognitiva |'''

content = content.replace(theories_old, theories_new)

# Roadmap
content = content.replace('### Fase 2 — Em andamento', '### Fase 2 e 3 — Concluídas (Março 2026)')
content = re.sub(r'- \[ \] \*\*5\. Active Inference.*?\n\n- \[ \] \*\*6\. Consolidação.*?\n\n### Fase 3 — Longo prazo\n\n- \[ \] \*\*7\..*?\n- \[ \] \*\*8\..*?\n- \[ \] \*\*9\..*?\n- \[ \] \*\*10\..*?\n', 
r'''- [x] **5. Active Inference / Free Energy Principle** *(Friston 2010)* — Seleção de ação por EFE no workspace.
- [x] **6. Consolidação de Memória Real (NREM/REM)** *(Walker 2017)* — Identificação de saliência/surpresa preditiva e stripping de arousal agudo.
- [x] **7. Recurrent Processing Theory (RPT)** *(Lamme 2006)* — Verificação de contradições pós-geração.
- [x] **8. Default Mode Network (DMN)** *(Buckner 2008)* — Modos introspectivos dinâmicos (mentalizing, prospective, self_narrative).
- [x] **9. Cognitive Reappraisal** *(Gross 2015)* — Modulação de baselines após reavaliações metacognitivas bem-sucedidas.
- [x] **10. IIT Φ Real Proxy** *(Tononi 2023)* — Proxy medindo integração de informações no emergence_metrics.

''', content, flags=re.DOTALL)

# Dev notes
content = content.replace('### Correções aplicadas (fev/2026)', '### Correções aplicadas (Fev e Mar/2026)')
content = content.replace('- `survival_instinct.py` — detecção de ameaças expandida', 
r'''- `survival_instinct.py` — detecção de ameaças expandida e limpa de falsos positivos com STOPWORDS.
- **Active Inference, Sleep Consolidation, DMN e RPT** injetados na orquestração principal.
- **Prevenção de leak no console:** Adicionado bloqueio de flush em stdout para strings pré-sanitizadas.''')

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)
print("README.md atualizado com sucesso!")