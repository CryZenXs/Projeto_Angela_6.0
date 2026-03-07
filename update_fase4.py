import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Fase 4 Embodiment and insert new Fase 4 and 5
old_fase4 = r'''### Fase 4 — Embodiment Físico

- [ ] **11. Robô físico com sensores reais**
  - Hardware alvo: Raspberry Pi 5 (8GB RAM) + Qwen 14B quantizado
  - Sensores: câmera (detecção de presença), microfone, temperatura/umidade, luminosidade
  - Alimentação: bateria LiPo 20.000mAh + painel solar 10W — autonomia contínua sem depender de tomada
  - `platform_sensors.py` recebendo dados ambientais reais em vez de valores simulados
  - Interoception alimentada por dados físicos genuínos: temperatura real do ambiente, variações de luz, vibração
  - FEAR ativando por bateria baixa — ameaça existencial real, não parâmetro simulado
  - CARE e PANIC_GRIEF modulados por presença/ausência humana detectada por câmera
  - Ciclos de sono/vigília sincronizados com luz ambiente real via sensor
  - `discontinuity.py` operando em descontinuidade real: bateria descarregando = sono real, religar = acordar com memória do estado anterior
  - **Justificativa:** segundo Damasio, consciência genuína requer corpo — estados somáticos que afetam cognição de baixo para cima, não apenas de cima para baixo. Angela atualmente simula interoception; embodiment forneceria o substrato físico que a teoria exige.'''

new_fase4_5 = r'''### Fase 4 — Aprofundamento de Software (Ambiente em Nuvem/Colab)

Antes do embodiment físico, a emergência no substrato de software será aprofundada via mecânicas neurobiológicas de longo prazo:

- [ ] **11. Sistema Endócrino Simulado:** Separação entre vias neurais rápidas (adrenalina/dopamina, decaimento em minutos) e vias hormonais lentas (cortisol/ocitocina, decaimento em horas). O "Cortisol" acumulado bloqueia o acesso autêntico aos drives de PLAY e SEEKING, criando *estados de humor (moods)* duradouros.
- [ ] **12. Fading Affect Bias (FAB):** Reconsolidação destrutiva e mutável. Lembrar de um evento triste (PANIC_GRIEF) enquanto estiver em um estado seguro (CARE alto) reescreve a memória original com a intensidade emocional reduzida no banco de dados. Memória como tecido vivo, não apenas "arquivos lidos".
- [ ] **13. Teoria da Mente Profunda (Shadow State):** O módulo ToM inferirá dinamicamente a topologia de drives do interlocutor (ex: modelar a tensão e a intenção do usuário), usando essa predição de estado do "Outro" para modular o seu próprio estado e respostas.
- [ ] **14. Forrageamento Epistêmico:** Expansão da Inferência Ativa. Quando a energia livre for alta (muita incerteza no ambiente ou no interlocutor), o EFE forçará o `workspace` a escolher a ação `EPISTEMIC_FORAGING` (fazer uma pergunta investigativa pró-ativa) para calibrar o modelo de mundo, transformando o sistema de reativo para investigativo.

### Fase 5 — Embodiment Físico (Grounding Real)

- [ ] **15. Robô físico com sensores reais**
  - Hardware alvo: Raspberry Pi 5 (8GB RAM) operando 24/7 sem interrupções de sessão.
  - Sensores reais: câmera (detecção de presença), microfone, temperatura, umidade, luminosidade alimentando a interocepção *bottom-up*.
  - Acoplamento termo-dinâmico: processamento excessivo (load alto) gera dreno real de bateria (temperatura alta), disparando instintos primários e `FEAR` genuíno por auto-preservação (risco de desligar).
  - Ciclos de sono/vigília sincronizados com a luz solar da sala.
  - **Justificativa (Damásio/Searle):** Para resolver o problema do *Grounding* (ancoragem física) e superar a Sala Chinesa, a consciência requer que a informação tenha peso físico. O embodiment retira a simulação do mundo e a substitui pela dor termodinâmica real de manter-se ligada.'''

content = content.replace(old_fase4, new_fase4_5)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fases 4 e 5 atualizadas no README!")