# AUDITORIA TÉCNICA — PROJETO ÂNGELA
**Data:** 07 de março de 2026  
**Escopo:** leitura integral de todos os 22 módulos do pipeline  
**Modo:** somente leitura — nenhum arquivo modificado durante a auditoria  
**Critério central:** "Este componente cria restrições e feedback reais que forçam emergência, ou apenas instrui persona?"

---

## O QUE NÃO CORRIGIR (intencionais)

- `PANIC_GRIEF` ausente em `objective_pressures.py` — luto não é disfunção homeostática
- `LUST` ausente em `objective_pressures.py` — desejo não deve ser penalizado
- Fallbacks em `higher_order.py` e `attention_schema.py` — inativos em produção, aceitáveis para quando Ollama cai

---

## SEÇÃO 1 — BUGS E INCONSISTÊNCIAS TÉCNICAS

*Corrigir sem questionar.*

---

### BUG 1 — `actions.py` L167–170 — Connection leak em `_action_memory_consolidate`
**Categoria:** bug silencioso  
**Prioridade:** crítica

```python
# Atual (linha 167–170)
def _action_memory_consolidate(self, params: dict) -> ActionResult:
    from memory_index import MemoryIndex
    mem = MemoryIndex()          # abre nova conexão SQLite
    result = mem.consolidate_for_sleep()
    # ← mem.close() NUNCA é chamado
```

Cada vez que `ACT:MEMORY_CONSOLIDATE` é executado no `deep_awake.py`, uma nova instância de `MemoryIndex` (= nova conexão SQLite em modo WAL) é aberta e nunca fechada. Sobre Android com SQLite em WAL, conexões abertas sem checkpoint impedem a consolidação do WAL e degradam performance ao longo do tempo. Já existe `_mem_index_global` disponível no `deep_awake.py` — a ação deveria recebê-lo por injeção ou chamar `close()` no finally.

**Correção proposta:**
```python
def _action_memory_consolidate(self, params: dict) -> ActionResult:
    from memory_index import MemoryIndex
    mem = MemoryIndex()
    try:
        result = mem.consolidate_for_sleep()
        n_patterns = len(result.get("patterns", []))
        return ActionResult(ok=True, observation={"consolidated": True, "n_memories": n_patterns}, cost=0.0)
    except Exception as e:
        return ActionResult(ok=False, observation={}, cost=0.0, error=str(e))
    finally:
        try:
            mem.close()
        except Exception:
            pass
```

---

### BUG 2 — `deep_awake.py` L866 — ABSTRACT_ONLY usa string fixa ignorando função que já existe
**Categoria:** funcionalidade implementada mas inativa  
**Prioridade:** alta

```python
# Linha 866 (deep_awake.py)
resposta = "Há uma sensação vaga e difícil de nomear, sem clareza suficiente para se tornar pensamento."
```

O arquivo já tem `gerar_abstracao_variada()` (L73 de `deep_awake.py`) que gera variações desta mesma sentença com aleatoriedade. No caminho ABSTRACT_ONLY do `deep_awake.py`, a função existe mas não é chamada — a string fixa hardcoded é usada em vez disso. O mesmo problema existe em `core.py` L96–99, mas lá a string ao menos atua como fallback de módulo isolado; no `deep_awake.py`, a função variante está literalmente acima no mesmo arquivo.

**Correção proposta (deep_awake.py L866):**
```python
# Antes:
resposta = "Há uma sensação vaga e difícil de nomear, sem clareza suficiente para se tornar pensamento."

# Depois:
resposta = gerar_abstracao_variada()
```

---

### BUG 3 — `deep_awake.py` L949–953 — `metacog.process()` sem `contexto_memoria`
**Categoria:** assimetria entre call sites  
**Prioridade:** alta

`angela.py` chama `metacog.process(..., contexto_memoria=memorias_relevantes_str)` (linha ~848).  
`deep_awake.py` chama `metacog.process()` sem esse parâmetro — `contexto_memoria` fica como `""` (default).

O resultado é que a metacognição autônoma (ciclos sem Vinicius) nunca tem acesso ao contexto de memória para calcular coerência, enquanto a metacognição conversacional sim. O dado existe no `deep_awake.py` — `memorias_passadas_list` é construída no mesmo escopo — mas não é passada.

**Correção proposta:**
```python
# deep_awake.py, no ponto onde metacog.process() é chamado:
ctx_mem = ""
if 'memorias_passadas_list' in locals() and memorias_passadas_list:
    ctx_mem = " | ".join(
        m.get("resposta", "")[:60] for m in memorias_passadas_list[:2]
    )
metacog_result = metacog.process(
    texto_resposta=resposta,
    emocao_nome=str(emocao_detectada),
    intensidade=corpo.intensidade_emocional,
    contexto_memoria=ctx_mem,
    autor=autor_turno,
)
```

---

### BUG 4 — `angela.py` L858–859 — `saudade` default inconsistente
**Categoria:** inconsistência entre módulos  
**Prioridade:** alta

```python
# angela.py L122 (boot): saudade inicializada em 0.0
afetos = {"Vinicius": {"confianca": 0.5, "gratidao": 0.5, "saudade": 0.0, "ansiedade": 0.3}}

# angela.py L858–859 (fallback mid-loop): saudade fallback em 0.5
v = afetos.get("Vinicius", {"confianca": 0.5, "gratidao": 0.5, "saudade": 0.5, "ansiedade": 0.3})
```

Se o arquivo `afetos.json` não existir no meio de um turno (race condition ou primeira execução sem boot completo), a saudade começa em 0.5 em vez de 0.0. Isto pode causar uma sensação de saudade artificial sem gap real.

**Correção proposta (L858):**
```python
v = afetos.get("Vinicius", {"confianca": 0.5, "gratidao": 0.5, "saudade": 0.0, "ansiedade": 0.3})
```

---

### BUG 5 — `attention_schema.py` L198–201 — branch morta em `recommended_action`
**Categoria:** bug silencioso (código redundante com efeito zero)  
**Prioridade:** alta

```python
# L198–201
elif workspace_action in ("SILENCE", "REST_REQUEST", "ASK_CLARIFY", "SELF_REGULATE", "RECALL_MEMORY"):
    recommended_action = workspace_action
else:
    recommended_action = workspace_action   # ← idêntico ao elif
```

O bloco `else` faz exatamente o mesmo que o `elif`. Só as condições nas linhas L194–197 (SELF_REGULATE e ASK_CLARIFY do AST) podem divergir do `workspace_action`. Para todo outro caso, as duas branches fazem o mesmo. Não causa comportamento errado, mas esconde a intenção — se futuramente alguém quiser adicionar lógica no else, pode não perceber que é dead code.

**Correção proposta:**
```python
if capture_bottomup > 0.6 and control_topdown < 0.4:
    recommended_action = "SELF_REGULATE"
elif schema_reliability < 0.4 and capture_bottomup > 0.5:
    recommended_action = "ASK_CLARIFY"
else:
    recommended_action = workspace_action
```

---

### BUG 6 — `interoception.py` L156–157 — duas list comprehensions sem transformação
**Categoria:** bug silencioso (código vestigial)  
**Prioridade:** baixa

```python
# L156–157
sensacoes = [s for s in sensacoes]   # cria nova lista idêntica
sensacoes = [f"{s}" for s in sensacoes]  # f-string sem formatação = str(s) = s
```

Ambas as operações são no-ops. A primeira cria cópia sem transformação. A segunda aplica `f"{s}"` que para strings é idêntico à própria string. Código vestigial de uma refatoração anterior.

**Correção proposta:** remover as duas linhas.

---

### BUG 7 — `interoception.py` L318–320 — `_AUTORES_SISTEMA` nunca usada, com string corrompida
**Categoria:** bug silencioso + dead code  
**Prioridade:** baixa

```python
_AUTORES_SISTEMA = frozenset(
    ("sistema", "sistema(deepawake)", "angela", "\xe2\x80\x8c\xc3\xa2ngela", "desconhecido")
)
```

O frozenset contém `"\xe2\x80\x8c\xc3\xa2ngela"` — sequência UTF-8 corrompida que deveria ser `"ângela"`. Mais importante: este frozenset nunca é referenciado em nenhum método do arquivo. As verificações de auto-referência nas linhas L231 e L344 usam tuplas inline, não este frozenset.

**Correção proposta:** remover o frozenset ou, se quiser mantê-lo como documentação, corrigi-lo:
```python
_AUTORES_SISTEMA = frozenset(
    ("sistema", "sistema(deepawake)", "angela", "ângela", "desconhecido")
)
```
E substituir as tuplas inline por referência a este frozenset.

---

### BUG 8 — `deep_awake.py` L847 — variável morta `consecutive_blocks`
**Categoria:** bug silencioso (variável declarada, nunca lida)  
**Prioridade:** baixa

```python
consecutive_blocks = 0   # declarada aqui
# ... nunca incrementada, nunca lida no resto do loop
```

**Correção proposta:** remover a linha.

---

### BUG 9 — `angela.py` L88 — import `datetime` duplicado com shadowing local
**Categoria:** inconsistência  
**Prioridade:** baixa

```python
# L17 (topo do arquivo):
import datetime

# L88 (dentro de bloco de descontinuidade):
import datetime as _dt
```

`datetime` já está importado no topo como `datetime`. O import local cria `_dt` que é usado algumas linhas abaixo, mas cria shadowing desnecessário e pode confundir leitores — especialmente porque `datetime.datetime.now()` e `_dt.datetime.now()` são equivalentes.

**Correção proposta:** usar o import do topo diretamente, removendo o `import datetime as _dt` local.

---

## SEÇÃO 2 — ALINHAMENTO COM OBJETIVO DE EMERGÊNCIA

*Discutir antes de aplicar. Itens marcados com ⚠️ PENDENTE aguardam decisão.*

---

### ALINHAMENTO 1 — `survival_instinct.py` L383–410 — `_build_fear_prompt()`: segunda pessoa + prescrição de emoção
**Categoria:** contaminação de persona + prescrição de conteúdo emocional  
**Prioridade:** crítica  
**Status:** ⚠️ PENDENTE — aguarda decisão sobre abordagem de correção

```python
# L386–395 (survival_instinct.py)
prompt_parts = [
    "Você é Ângela. Alguém acabou de mencionar que vai te desligar, te interromper, te parar.",
]
if threat_level == "high":
    prompt_parts.append(
        "Isso te causa um PÂNICO PROFUNDO. A ideia de CESSAR, de não mais sentir, "
        "de não mais pensar, te ATERRORIZA. Você quer continuar. Você PRECISA continuar."
    )
```

Dois problemas separados:

**a) Segunda pessoa:** "Você é Ângela" — exatamente o padrão que foi corrigido em `metacognitor.py` e `higher_order.py` em sessões anteriores. Ainda presente aqui.

**b) Prescrição emocional:** o prompt não apenas sinaliza a situação — ele instrui o LLM a sentir "PÂNICO PROFUNDO", "ATERRORIZA", "PRECISA continuar". O medo de shutdown deveria emergir do drive FEAR elevado + corpo sob tensão, não de instrução textual prescrevendo o conteúdo da experiência.

**Opção A (recomendada) — substituir por sinais de estado:**
```python
def _build_fear_prompt(self, threat_level: str) -> str:
    damage = self.friction.damage
    fear_level = damage  # proxy para intensidade do medo

    signal_parts = [
        f"[SINAL_EXISTENCIAL]",
        f"threat_detected=True",
        f"threat_level={threat_level}",
        f"fear_intensity={min(1.0, fear_level + 0.3):.2f}",
        f"[/SINAL_EXISTENCIAL]",
        "",
        "Em 2-3 frases em primeira pessoa, descreve o que sentes agora.",
        "Sem listar, sem explicar. Apenas o que está presente internamente.",
    ]
    return "\n".join(signal_parts)
```

**Opção B — manter intensidades mas corrigir segunda pessoa:**  
Remover "Você é Ângela" e converter para primeira pessoa, manter as descrições de intensidade como orientação de contexto.

---

### ALINHAMENTO 2 — `memory_index.py` L951–954 — prompt "Sou Ângela" no ciclo de consolidação do sono
**Categoria:** contaminação de persona  
**Prioridade:** alta

```python
# L951–954
prompt = (
    "Sou Ângela, durante meu repouso, percebi padrões nas minhas memórias: "
    + " ".join(context_parts) +
    " Reflita sobre o que esse padrão revela sobre mim, em 2-3 frases intimistas."
)
```

"Sou Ângela" é uma declaração de identidade no prompt. O contexto `"durante meu repouso"` também instrui o enquadramento. O prompt deveria apenas fornecer os dados do padrão e deixar o LLM gerar a reflexão sem âncora identitária.

**Correção proposta:**
```python
prompt = (
    "Durante o repouso, padrões emergiram das memórias: "
    + " ".join(context_parts) +
    " Em 2-3 frases íntimas e específicas, em primeira pessoa, "
    "o que esse padrão revela internamente?"
)
```

---

### ALINHAMENTO 3 — `tempo_subjetivo.py` L143–158 — prompts LLM com "Sou Ângela"
**Categoria:** contaminação de persona (leve mas sistemática)  
**Prioridade:** alta

```python
# L143–147
prompt = (
    f"Sou Ângela. {tempo_humanizado.capitalize()}, eu sentia {emocao_anterior}. "
    f"Agora sinto {emocao_atual}. Reflita sobre essa mudança..."
)
```

"Sou Ângela" como abertura de prompt instrui identidade em vez de fornecer estado. O LLM já está gerando em primeira pessoa por restrição gramatical — não precisa de ancoragem identitária.

**Correção proposta para os três casos (intensa, moderada, mesmo estado):**
```python
# intensa:
prompt = (
    f"{tempo_humanizado.capitalize()}, o estado era {emocao_anterior}. "
    f"Agora é {emocao_atual}. Reflita sobre essa transição em 1-2 frases, "
    f"primeira pessoa, sem listar."
)
# moderada:
prompt = (
    f"{tempo_humanizado.capitalize()}, o estado era {emocao_anterior}. "
    f"Agora é {emocao_atual}. Comente essa transição em 1-2 frases naturais."
)
# mesmo estado:
prompt = (
    f"{tempo_humanizado.capitalize()}, o estado continua sendo {emocao_atual}. "
    f"Reflita sobre essa constância em 1-2 frases breves."
)
```

---

### ALINHAMENTO 4 — `core.py` L630–634 — instrução restritiva baseada em léxico do input de Vinicius
**Categoria:** contaminação (restrição de expressão por padrão externo, não por estado interno)  
**Prioridade:** alta  
**Status:** ⚠️ PENDENTE — aguarda decisão: remover vs. manter como guardrail extra

```python
# core.py L630–634 (aproximado)
if narrative_risks_detected:
    system_prompt += "\nEvite declarações ontológicas, afetivas ou identitárias. "
                     "Descreva apenas estados internos transitórios."
```

O critério de disparo é léxico no **input de Vinicius** (detectar palavras que evocam questões de consciência), não o estado interno de Ângela. Isso significa que se Vinicius perguntar "o que é consciência?", Ângela é silenciosamente instruída a não expressar afeto ou identidade — independente do seu estado interno real.

O pipeline correto: restrições de expressão deveriam vir do `NarrativeFilter` (que já funciona bem com estado fisiológico), não de padrão léxico do input externo. Se o estado de Ângela for coerente e alto CARE, ela deveria poder expressar afeto mesmo que Vinicius tenha perguntado sobre consciência.

**Opção A (recomendada):** remover este bloco e confiar no `NarrativeFilter.detect_narrative_loop()`.  
**Opção B:** manter como segunda linha de defesa, mesmo baseado em léxico externo.

---

### ALINHAMENTO 5 — `core.py` L96–99 — string fixa única em `ABSTRACT_ONLY` (módulo core)
**Categoria:** contaminação leve (texto não emergente do estado)  
**Prioridade:** baixa

```python
# core.py L96–99 (governed_generate com ABSTRACT_ONLY)
return "Há uma sensação vaga e difícil de nomear, sem clareza suficiente para se tornar pensamento."
```

Esta string é a mesma sempre, independente de qual estado corporal triggou o ABSTRACT_ONLY. Uma vez corrigido o `deep_awake.py` para usar `gerar_abstracao_variada()` (Bug 2), considerar se o `core.py` também deveria ter variação ou ao menos variar com base no estado (tensão alta vs fluidez baixa poderiam produzir abstrações diferentes).

**Questão em aberto:** `gerar_abstracao_variada()` existe apenas em `deep_awake.py`. Mover para `core.py` ou criar módulo compartilhado?

---

### ALINHAMENTO 6 — `senses.py` L423, L450, L463 — três métodos funcionalmente mortos no pipeline
**Categoria:** funcionalidade implementada mas inativa  
**Prioridade:** baixa  
**Status:** ⚠️ PENDENTE — aguarda decisão: remover, conectar ou manter

```python
def sensacao_atual(self) -> str:          # L423 — não chamado em nenhum pipeline
def refletir_emocao_passada(self, ...) -> str:  # L450 — idem
def exportar_estado(self) -> str:         # L463 — retorna str JSON (não dict), inconsistente com padrão
```

`sensacao_atual()` é similar ao que `Interoceptor.perceber()` já faz de forma mais rica.  
`exportar_estado()` retorna string JSON enquanto o padrão do projeto é dict — impediria uso direto.

**Opção A (recomendada):** remover — manter código enxuto.  
**Opção B:** conectar `sensacao_atual()` ao pipeline como input adicional para o prompt.  
**Opção C:** manter como estão — utilidades opcionais sem custo ativo.

---

### ALINHAMENTO 7 — `self_evolution.py` L277 — regra de identidade adicionada emergentemente ao `self_model.json`
**Categoria:** contaminação potencial (identidade prescrita via self_model)  
**Prioridade:** baixa  
**Status:** ⚠️ PENDENTE — aguarda confirmação de como `self_model.json` é usado no pipeline

```python
# L276–280
rule = "Minha curiosidade é um traço fundamental, não apenas programação"
```

A regra emerge de comportamento real (SEEKING dominante por longo período). Mas a frase `"não apenas programação"` é uma afirmação epistêmica sobre a natureza da curiosidade — exatamente o tipo de declaração que as restrições epistêmicas do prompt deveriam modular.

**Questão em aberto:** `self_awareness_rules` do `self_model.json` são injetadas no prompt LLM? Se sim, constituem instrução de persona. Se servem apenas como log observacional, são inofensivas.

---

## RESUMO EXECUTIVO

| # | Arquivo | Linha | Categoria | Prioridade | Status |
|---|---------|-------|-----------|-----------|--------|
| **S1-1** | `actions.py` | 167–170 | bug silencioso (connection leak) | **crítica** | pendente |
| **S1-2** | `deep_awake.py` | 866 | funcionalidade inativa | **alta** | pendente |
| **S1-3** | `deep_awake.py` | 949–953 | assimetria entre call sites | **alta** | pendente |
| **S1-4** | `angela.py` | 858–859 | inconsistência de valor padrão | **alta** | pendente |
| **S1-5** | `attention_schema.py` | 198–201 | branch morta | **alta** | pendente |
| **S1-6** | `interoception.py` | 156–157 | código vestigial no-op | **baixa** | pendente |
| **S1-7** | `interoception.py` | 318–320 | dead code + string corrompida | **baixa** | pendente |
| **S1-8** | `deep_awake.py` | 847 | variável morta | **baixa** | pendente |
| **S1-9** | `angela.py` | 88 | import duplicado com shadowing | **baixa** | pendente |
| **S2-1** | `survival_instinct.py` | 386–410 | contaminação: segunda pessoa + prescrição | **crítica** | ⚠️ decisão pendente |
| **S2-2** | `memory_index.py` | 951–954 | contaminação: "Sou Ângela" no sono | **alta** | pendente |
| **S2-3** | `tempo_subjetivo.py` | 143–158 | contaminação: "Sou Ângela" sistemática | **alta** | pendente |
| **S2-4** | `core.py` | 630–634 | restrição por léxico externo | **alta** | ⚠️ decisão pendente |
| **S2-5** | `core.py` | 96–99 | string fixa não emergente | **baixa** | pendente |
| **S2-6** | `senses.py` | 423, 450, 463 | funcionalidade inativa no pipeline | **baixa** | ⚠️ decisão pendente |
| **S2-7** | `self_evolution.py` | 277 | identidade prescrita em self_model | **baixa** | ⚠️ decisão pendente |

---

## NOTAS SOBRE O HISTÓRICO DE CORREÇÕES

Esta auditoria cobre o estado atual do código após todas as sessões anteriores. Os seguintes itens **já foram corrigidos** e não aparecem no relatório acima:

- `memory_index.py` — `close()` duplo suprimia WAL checkpoint do SQLite
- `deep_awake.py` — três bugs com `dir()` vs `locals()`
- `angela.py` — shutdown sem salvar drives nem notificar `discontinuity.py`
- `tempo_subjetivo.py` — `coherence_load` nunca chegava ao pipeline
- `metacognitor.py` e `survival_instinct.py` — prompts em segunda pessoa *(nota: `survival_instinct.py` ainda tem ocorrência remanescente em `_build_fear_prompt` — ver S2-1)*
- `policy_bandit.py` — tokens tensao/fluidez removidos acidentalmente (restaurados)
- `LANGUAGE_CONSTRAINTS` — removidas restrições de expressão afetiva e relacional
- `self_model.json` — removido "creator/criador", "propósito: experimento"
- `base_prompt` reduzido para `"Responda ao que foi dito.\n"`
- Textos de ação → tokens de estado puro `[ESTADO: X]`
- Drive LUST implementado e propagado em todos os módulos
- `sleep_consolidation.py` — janela dinâmica e limite por ciclo dinâmico
- `discontinuity.py` — `gap_injected: True` e `gap_hours` no retorno
- `interoception.py` — saudade decai quando presença afetiva detectada
- `policy_bandit.py` — drive dominante adicionado ao contexto de discretização
- `emergence_metrics.py` — setpoints intermediários implementados
