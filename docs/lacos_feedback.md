# Laços de feedback — Ângela

Diagrama de dados: **toda saída do LLM (ou decisão de silêncio) passa por análise e atualiza estado** para o próximo turno. Objetivo: laços fechados, sem ramos que "pulem" atualização.

---

## angela.py — fluxo conversacional

```
Input do usuário
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ PRÉ-RESPOSTA (sempre)                                             │
│ senses → survival → DigitalBody → interoception → drives          │
│ → memory_index.recall → workspace.broadcast() → acao               │
│ → attention_schema.update() → hot_monitor.observe()               │
│ → prediction (erro anterior, atenção)                            │
│ Construção: vinc_header, tom, hot_header, attention_header,       │
│             intero_header, circumplex, memórias, diálogo         │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ GERAÇÃO                                                           │
│ • acao == SILENCE  → response = "..." (sem LLM)                  │
│ • else             → governed_generate(prompt_final)              │
│   → NarrativeFilter: BLOCKED → ""; DELAYED → sleep + LLM;          │
│     ABSTRACT_ONLY → frase fixa; ALLOWED → LLM                     │
│   → se "" → response = "..."                                     │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ PÓS-RESPOSTA (sempre, para qualquer response incluindo "...")     │
│ • response == "..." e acao != SILENCE → RAGE.activate(blocked_…)  │
│ • analisar_emocao_semantica(response, drives, corpo)             │
│ • friction.step() (se response != "...")                          │
│ • survival.update(); trigger → corpo.tensao; ameaça → friction  │
│ • corpo.aplicar_emocao(emocao_detectada, intensidade)             │
│ • prediction.compare(actual_state); workspace.state.prediction_error │
│ • (opcional) reflexão corporal → append_memory                    │
│ • metacognitor.process() → afetos.json                           │
│ • corpo.decay(); save_emotional_snapshot(); append_memory()      │
│ • mem_index.index_memory()                                        │
│ • reflexão temporal → append_memory                               │
│ • workspace.reset_tick(); interaction_count += 1                   │
│ • cada 10 reais: self_evolution.evaluate_experience / apply      │
└──────────────────────────────────────────────────────────────────┘
       │
       └──────────────────────► próximo turno (input)
```

**Ramos cobertos:**

- **ALLOWED:** LLM → response → todo o bloco pós-resposta ✅  
- **BLOCKED:** response = "..." → RAGE, analisar_emocao_semantica("..."), corpo, memória, friction (sem step), etc. ✅  
- **DELAYED:** sleep + LLM → idem ALLOWED ✅  
- **ABSTRACT_ONLY:** frase fixa → idem ALLOWED ✅  
- **SILENCE (workspace):** response = "..." antes do `if prompt_final is not None`; depois entra no mesmo bloco pós-resposta (analisar_emocao_semantica, corpo, memória, …) ✅  

Nenhum ramo deixa de atualizar corpo, drives, memória ou AST (AST é atualizado no início do próximo turno com o novo workspace/drives).

---

## deep_awake.py — fluxo por ciclo

```
Ciclo (vigilia / introspeccao / sonho / repouso)
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ PRÉ-GERAÇÃO                                                       │
│ discontinuity → reconnection_cost → corpo; attention_schema.apply │
│ workspace (candidatos, drives, memória, interocepção)             │
│ broadcast_result → acao_workspace                                 │
│ attention_schema.update(); hot_monitor.observe()                  │
│ Construção: vinc, tom, hot_header, attention_header, intero,      │
│             circumplex, conversa_recente, prompt_base             │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ GERAÇÃO                                                           │
│ • acao_workspace == SILENCE → resposta = ""                      │
│ • else → NarrativeFilter.evaluate; BLOCKED → ""; DELAYED →       │
│   sleep + governed_generate; ABSTRACT_ONLY → frase; ALLOWED →     │
│   governed_generate                                               │
│ • (dentro do else) analisar_emocao_semantica; corpo.aplicar_emocao│
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ PÓS-CICLO (sempre)                                                │
│ prediction.compare(actual_state); metacog.process(resposta, …)   │
│ reflexao_temporal; append_memory(Sistema(DeepAwake), resposta,…)  │
│ mem_index.index_memory(); friction_metrics.log                    │
│ workspace.reset_tick(); cycle_count += 1                          │
│ cada 5 ciclos ou repouso: self_evolution.evaluate / apply         │
│ repouso: extrair_memorias_significativas; consolidate_for_sleep   │
└──────────────────────────────────────────────────────────────────┘
       │
       └──────────────────────► próximo ciclo (sleep(intervalo))
```

**Ramo SILENCE em deep_awake:**  
Antes da correção: quando `acao_workspace == "SILENCE"`, `resposta = ""` e não se chamava `corpo.aplicar_emocao` (só no `else`). O restante (prediction, metacog, append_memory, mem_index, friction_metrics, self_evolution) roda para todos.  
**Correção:** chamar `corpo.aplicar_emocao("neutro", 0.0)` também no ramo SILENCE para fechar o laço corporal.

---

## Arquivos envolvidos nos laços

| Papel | angela.py | deep_awake.py | Outros |
|-------|-----------|---------------|--------|
| Entrada | user_input | ciclo + memórias | — |
| Corpo | DigitalBody (senses, interoception) | idem | senses.py, interoception.py |
| Drives | DriveSystem | idem | drives.py |
| Memória | MemoryIndex, append_memory | idem | core.append_memory, memory_index |
| Workspace | GlobalWorkspace.broadcast | idem | workspace.py |
| AST | attention_schema.update + get_prompt_header | idem | attention_schema.py |
| HOT | hot_monitor.observe + get_prompt_header | idem | higher_order.py |
| Filtro | governed_generate → NarrativeFilter | evaluate + governed_generate | core.py, narrative_filter.py |
| Pós | analisar_emocao_semantica, friction, survival, aplicar_emocao, save_emotional_snapshot, append_memory, mem_index, reflexão temporal | prediction, metacog, append_memory, mem_index, friction_metrics, repouso/consolidação | core, cognitive_friction, survival_instinct, etc. |

---

## Checklist para novos ramos

Ao adicionar um novo caminho (ex.: novo tipo de ação ou modo):

1. **Geração:** esse ramo chama LLM ou define resposta fixa/silêncio?  
2. **Pós:** esse ramo passa por analisar_emocao_semantica (ou equivalente), atualização de corpo (aplicar_emocao), memória (append_memory + index) e, se aplicável, friction/survival?  
3. **AST/HOT:** o próximo turno/ciclo terá workspace e attention_schema atualizados (já ocorre no início do próximo turno se o estado persistido for o mesmo processo).

Se algum ramo não atualizar corpo ou memória, o laço fica aberto — corrigir antes de merge.
