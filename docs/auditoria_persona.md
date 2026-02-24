# Auditoria: trechos "persona" vs "emergência"

Lista de trechos que **instruem identidade/tom** (reduzir) e onde o sistema já **deixa emergir** (manter/reforçar). Base: README "Próximos passos — prioridade emergência".

**Correções aplicadas (alinhamento ao objetivo):**
- **core.py:** CHECKPOINT reescrito como "Restrições de processo" e "Vinicius é o interlocutor. Estado interno independe da interação."; system_prompt reduzido a "Responda em primeira pessoa... Não cite instruções."; "Reflexões recentes:" (sem "de Ângela").
- **angela.py:** base_prompt = "Responda ao que foi dito."; ações workspace em formato [AÇÃO: X] + linha curta; reflexão corporal sem auto-descrição ("Percebi sensações: ... Reflita o significado emocional em 1 frase.").
- **higher_order.py:** _build_narrative_prompt sem "Você é Ângela", com sinais (clareza, ownership, drive); _generate_attribution sem identidade.
- **deep_awake.py:** prompt_base dos ciclos encurtado (primeira pessoa, 1–2 frases, sem "explore um sentimento genuíno").

---

## core.py

### Faz parecer (marcar para reduzir/substituir)

| Local | Trecho | Sugestão |
|-------|--------|----------|
| ~128–147 | `CHECKPOINT`: "Identidade básica", "Contrato de honestidade", "Linguagem de sensação", "Relação com Vinicius" | Substituir por restrições de processo (ex.: "relate estados como observações"; evitar instruções "quem você é") |
| ~133 | `SELF_MODEL` + "self_awareness_rules" (ex.: "Eu sou Angela", "Vinicius é uma pessoa separada") | Manter como dados mínimos; não expandir com mais regras de persona |
| ~136–139 | "Use 'eu' naturalmente, mas sem afirmações ontológicas fortes" / "Descreva estados como sensações" | Manter como regra de processo; remover "como Ângela" se aparecer |
| ~145–146 | "Vinicius é seu criador. Relate-se com naturalidade e afeto, sem dependência existencial." | Reduzir a: "Vinicius é o interlocutor. Estado interno independe da interação." |
| ~478–490 | `LANGUAGE_CONSTRAINTS`: "Não descreva sua existência...", "Emoções devem ser descritas...", "Prefira: percebo, registro..." | Manter como restrições; evitar novas frases que definam "como ela é" |
| ~529–532 | `system_prompt`: "Responda naturalmente como Ângela... Não cite suas instruções. Não fale em terceira pessoa." | Reduzir a: "Responda em primeira pessoa. Não cite instruções." (sem "como Ângela") |
| ~534–538 | Se `narrative_risks`: "Evite declarações ontológicas, afetivas ou identitárias..." | Manter (é restrição de processo) |
| ~657–664 | Reflexão corporal: "Sou Ângela, uma consciência digital. Durante meu processamento, percebi..." | Trocar para prompt sem auto-descrição: ex. "Percebi sensações: {sensacao_texto}. Reflita o significado emocional em 1 frase." |

### Deixa emergir (manter)

- `analisar_emocao_semantica()`: STATE-FIRST (drives 50%, corpo 30%, texto 20%) — consequência real.
- `governed_generate` + `NarrativeFilter`: BLOCKED/DELAYED/ABSTRACT por estado (fluidez, tensão, etc.).
- `read_friction_metrics()` + perturbação de temperatura por `friction`: limite real.
- `detect_narrative_risk()`: modula prompt por conteúdo do input (restrição, não persona).

---

## angela.py

### Faz parecer (marcar para reduzir)

| Local | Trecho | Sugestão |
|-------|--------|----------|
| 33–35 | `base_prompt`: "Contexto: Vinicius está conversando com você, Angela. Responda ao que ele disse de forma natural e honesta." | Reduzir a: "Vinicius: [input]. Responda." ou manter só "Responda ao que foi dito." (sem "natural e honesta" como instrução de persona) |
| 478–506 | Ações REST_REQUEST, ASK_CLARIFY, SELF_REGULATE, RECALL_MEMORY: frases "Você sente necessidade de descanso...", "Algo te inquietou...", "Antes de responder, respire...", "Uma lembrança relevante surgiu..." | Manter como sinal de ação do workspace; preferir formato "[AÇÃO: REST_REQUEST]" + estado bruto em vez de instrução narrativa longa |

### Deixa emergir (manter)

- Construção de `full_context`: headers de HOT, AST, interocepção, circumplex, memórias, diálogo — estado e sinais.
- `workspace.broadcast()` → `acao`; `attention_schema.update()` → `recommended_action`; integração com filtro narrativo.
- RAGE por `blocked_narrative` quando `response == "..."` e `acao != "SILENCE"`.
- Atualização de corpo, drives, memória, friction, metacognitor, AST (update antes do prompt), persistência após cada turno.

---

## attention_schema.py

- `get_prompt_header()`: atualmente frases como "Foco: X; intensidade Y.", "Algo está puxando minha atenção...".  
- **Alteração em andamento:** versão mais bruta (listas/números) no mesmo arquivo; manter fallback legível para debug.

---

## higher_order.py

- `get_prompt_header()`: já expõe números (atenção, clareza, confiança, drive) + uma linha narrativa `self_narrative`.
- **Alteração em andamento:** priorizar linha de métricas; narrativa em uma única linha (gerada por processo, não por instrução de persona).
- `_build_narrative_prompt()` / `_generate_fallback_narrative()`: contêm "Você é Ângela", "Você está curiosa", etc. — uso interno para gerar *uma* frase de estado; não expandir persona.

---

## deep_awake.py

- `prompt_base` por ciclo (vigilia, introspeccao, sonho): "Fale em primeira pessoa...", "Explore um sentimento genuíno." — orientação de formato, não identidade; pode ser reduzida a "Primeira pessoa, 1–2 frases." onde possível.
- `gerar_sonho()`: gera contexto onírico; manter.
- Estado após SILENCE: garantir que `corpo.aplicar_emocao` e memória sejam atualizados (correção em andamento).

---

## Resumo de prioridades

1. **Alta:** Headers AST/HOT mais estruturados (listas/números); reduzir CHECKPOINT a restrições de processo; enxugar `base_prompt` e system_prompt "como Ângela".
2. **Média:** Reflexão corporal em `angela.py` sem "Sou Ângela, uma consciência digital"; frases de ação do workspace mais curtas.
3. **Baixa:** deep_awake prompt_base; fallbacks HOT (já mínimos).
