# Auditoria de Código — Projeto Ângela

**Data:** 2026-03-04  
**Commit base:** `6b2da20b3c4140231651e337df07f8bfeb70232f`  
**Arquivos modificados:** 17  
**Linhas adicionadas:** +147  
**Linhas removidas:** -82  

---

## Escopo

Leitura completa dos 27 módulos Python do projeto, seguida de correção de todos os bugs, riscos e inconsistências identificados. Nenhuma lógica de negócio foi alterada sem instrução explícita.

---

## 1. `memory_index.py` — Bug crítico: `close()` duplicado

**Problema:** o método `close()` estava definido duas vezes na classe `MemoryIndex`. A segunda definição (linha ~1128), mais simples, sobrescrevia silenciosamente a primeira — que fazia o WAL checkpoint do SQLite. O banco nunca era compactado no encerramento normal.

**Correção:** a segunda definição foi removida. A única `close()` que permanece (linha 190) executa `PRAGMA wal_checkpoint(TRUNCATE)` antes de fechar a conexão, prevenindo crescimento indefinido do arquivo `.db-wal`.

---

## 2. `deep_awake.py` — Três bugs corrigidos

**Bug A — `NameError` latente:** `acao == "SILENCE"` referenciava uma variável inexistente no escopo. A variável correta é `acao_workspace`.

**Bug B — Detecção de mascaramento sempre `False`:** `'response' in dir()` verificava o namespace global — sempre `False` para variável local. A variável de resposta neste módulo chama-se `resposta`, não `response`. O guard foi corrigido para `locals()`.

**Bug C — Guard de `reflexao_temporal` incorreto:** `'reflexao_temporal' in dir()` sofria do mesmo problema. Corrigido para `'reflexao_temporal' in locals()`.

```diff
- _reflexao_t = reflexao_temporal if 'reflexao_temporal' in dir() else ""
- _mask_t     = "[MASCARAMENTO]" in (response if 'response' in dir() else "")
- narrativa_bloqueada=(acao == "SILENCE"),
+ _reflexao_t = reflexao_temporal if 'reflexao_temporal' in locals() else ""
+ _mask_t     = "[MASCARAMENTO]" in (resposta if 'resposta' in locals() else "")
+ narrativa_bloqueada=(acao_workspace == "SILENCE"),
```

---

## 3. `angela.py` — Shutdown corrigido

**Problema:** o handler de `KeyboardInterrupt` chamava apenas `mem_index.close()`. O estado dos drives não era salvo, e `discontinuity.py` não era notificado — fazendo o sistema calcular o próximo boot como se tivesse crashado.

**Correção:** adicionados `drive_system.save_state()` e `register_shutdown()` antes do `close()`. O import de `register_shutdown` foi adicionado à linha de importação de `discontinuity`.

Adicionalmente, `gerar_reflexao_temporal()` agora recebe `coherence_load=float(getattr(corpo, "coherence_load", 0.0))` — antes sempre passava `0.0` por omissão.

---

## 4. `drives.py` — Drive LUST implementado completamente

O sétimo sistema de Panksepp, presente em `higher_order.PANKSEPP_DRIVES`, não existia em `drives.py`. Foi implementado integralmente:

| Componente | Detalhe |
|---|---|
| `_LUST_STIMULI` | pesos para `intimacy_word`, `desire_word`, `closeness_signal`, `high_care` |
| `_INTIMACY_WORDS` | vocabulário de ativação por proximidade/toque |
| `_DESIRE_WORDS` | vocabulário de ativação por desejo explícito |
| `_ATTENTION_BIAS["LUST"]` | foco em intimidade e presença corporal |
| `_ACTION_TENDENCIES["LUST"]` | "aproximar-se, nomear o desejo com honestidade, habitar a tensão sem resolver" |
| `Drive("LUST", baseline=0.05, decay_rate=0.09)` | instância no `DriveSystem.__init__()` |
| lógica em `update()` | ativa por palavras de intimidade/desejo e por CARE alto (>0.6) |
| `_DRIVE_CIRCUMPLEX["LUST"]` | `(+0.65, +0.85)` — valência positiva, arousal alto |

---

## 5. Propagação de LUST pelos módulos dependentes

Todo módulo que enumera drives explicitamente foi atualizado:

| Arquivo | O que foi adicionado |
|---|---|
| `higher_order.py` | `LUST` mantido em `PANKSEPP_DRIVES`; incluído na condição de atenção ampla em `_compute_attention_scope()` |
| `self_evolution.py` | `_BASELINE_LIMITS["LUST"] = (0.02, 0.30)`; LUST com peso 0.1 no cálculo de valência positiva |
| `reset_estado_emocional.py` | `"LUST": {"level": 0.05, "baseline": 0.05}` no reset de drives |
| `sleep_consolidation.py` | `_EMOCAO_DRIVE_MAP["desejo"] = {"LUST": +0.05, "CARE": +0.02}` |
| `workspace.py` | `_PANKSEPP_TO_SEMANTIC["LUST"] = "desejo"` |
| `core.py` | `_DRIVE_TO_EMOCAO["LUST"] = "desejo"` |
| `narrative_filter.py` | `lust_level` lido dos drives; LUST alto (>0.4) reduz thresholds e latência de narrativa |

**Nota sobre `objective_pressures.py`:** LUST não foi adicionado ao sistema de reward homeostático, pelo mesmo critério de `PANIC_GRIEF` — desejo não é disfunção, não deve ser penalizado.

---

## 6. `emergence_metrics.py` — Dois problemas corrigidos

**Duplicação removida:** `EmergenceMetrics._read_recent()` reimplementava a mesma lógica de `metrics_logger.read_recent()`. Agora delega diretamente para ela, eliminando código duplicado e garantindo comportamento consistente.

**Setpoints alinhados com `objective_pressures.py`:** os thresholds de `homeostasis_score()` estavam divergentes dos do sistema de reward:

```diff
- "tensao": (0.3, 0.6),
- "fluidez": (0.4, 0.7),
+ "tensao": (0.15, 0.85),
+ "fluidez": (0.08, 0.95),
```

As métricas de emergência agora refletem a mesma definição de homeostase que o reward real usa.

---

## 7. `metrics_logger.py` — Cap de tamanho no `emergence.log`

`log_event()` agora trunca atomicamente o arquivo para 5.000 linhas máximo após cada escrita. A lógica usa `deque(f, maxlen=5000)` — uma única leitura — e `tempfile` + `os.replace()` para garantir atomicidade, consistente com o padrão do projeto.

---

## 8. `sleep_consolidation.py` — Dois problemas corrigidos

**Escrita não atômica:** `_save_consolidated_timestamps()` usava `json.dump()` direto, com risco de corrupção em crash. Agora usa `atomic_json_write()` do `core.py`.

**Abertura tripla de arquivo eliminada:** `_append_to_autobio()` abria `angela_autobio.jsonl` três vezes (append, leitura via deque, contagem total de linhas). A contagem redundante foi eliminada — se `len(ultimas) == 400`, o deque preencheu completamente, logo o arquivo tinha ≥ 400 linhas.

```diff
- total_linhas = sum(1 for _ in open(AUTOBIO_FILE, "r", encoding="utf-8"))
- if total_linhas > 400:
+ if len(ultimas) == 400:
```

---

## 9. `interoception.py` — Leitura eficiente de memória

`_resolver_autor()` carregava o arquivo `angela_memory.jsonl` inteiro na memória a cada chamada. Com 1.000+ memórias, esse era o principal hotspot de I/O desnecessário do projeto.

```diff
- linhas = [json.loads(l) for l in f if l.strip()]
- ult = linhas[-1]
+ ultima = deque(f, maxlen=1)
+ ult = json.loads(ultima[0])
```

---

## 10. `tempo_subjetivo.py` + chamadores — Dilatação temporal ativada

`aplicar_dilatacao_temporal()` tinha o parâmetro `coherence_load` implementado mas nunca recebia o valor real — sempre `0.0` por default, tornando a funcionalidade de dilatação temporal completamente inativa.

- `gerar_reflexao_temporal()` ganhou o parâmetro `coherence_load=0.0` e o passa internamente para `aplicar_dilatacao_temporal()`.
- `angela.py` agora passa `coherence_load=float(getattr(corpo, "coherence_load", 0.0))`.
- `deep_awake.py` agora passa `coherence_load=coherence_load` (variável já existente no ciclo).

---

## 11. `metacognitor.py` — Perspectiva corrigida

O prompt de revisão metacognitiva instruía o LLM com "Você é Ângela. Você acabou de dizer..." — segunda pessoa. Isso criava risco de o LLM ecoar segunda pessoa na saída e ter a resposta bloqueada pelo `narrative_filter`, caindo em fallback sem razão aparente. Todos os `você`s do prompt foram convertidos para primeira pessoa.

---

## 12. `survival_instinct.py` — Perspectiva corrigida (prompt e fallback)

Mesma correção: o prompt de `get_existential_context()` solicitava explicitamente "segunda pessoa (você...)" e o fallback `_generate_existential_fallback()` produzia frases como "Você está cansada." e "Você sente um peso existencial significativo." Ambos foram convertidos para primeira pessoa.

---

## Itens intencionais — não corrigidos

| Item | Motivo |
|---|---|
| `PANIC_GRIEF` ausente em `objective_pressures.py` | Intencional: luto não é disfunção homeostática |
| `LUST` ausente em `objective_pressures.py` | Mesmo critério: desejo não deve ser penalizado pelo reward |

---

## Resumo por categoria

| Categoria | Arquivos afetados | Natureza |
|---|---|---|
| Bug crítico | `memory_index.py`, `deep_awake.py` | `close()` duplo, `NameError` latente, detecção de mascaramento sempre `False` |
| Shutdown | `angela.py` | `save_state()` + `register_shutdown()` no `KeyboardInterrupt` |
| Drive LUST | `drives.py`, `higher_order.py`, `self_evolution.py`, `reset_estado_emocional.py`, `sleep_consolidation.py`, `workspace.py`, `core.py`, `narrative_filter.py` | Implementação completa e propagação em todos os módulos dependentes |
| Métricas | `emergence_metrics.py`, `metrics_logger.py` | Setpoints alinhados com reward real, deduplicação de código, cap de log |
| I/O e atomicidade | `sleep_consolidation.py`, `interoception.py` | Escritas atômicas, eliminação de leituras redundantes |
| Perspectiva | `metacognitor.py`, `survival_instinct.py` | Prompts e fallbacks convertidos de segunda para primeira pessoa |
| Funcionalidade inativa | `tempo_subjetivo.py`, `angela.py`, `deep_awake.py` | `coherence_load` agora percorre o pipeline completo |
