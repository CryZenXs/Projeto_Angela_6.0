import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '- [ ] **11. Sistema Endócrino Simulado:** Separação entre vias neurais rápidas (adrenalina/dopamina, decaimento em minutos) e vias hormonais lentas (cortisol/ocitocina, decaimento em horas). O "Cortisol" acumulado bloqueia o acesso autêntico aos drives de PLAY e SEEKING, criando *estados de humor (moods)* duradouros.',
    '- [x] **11. Sistema Endócrino Simulado:** Separação entre vias neurais rápidas (adrenalina/dopamina) e hormonais lentas (cortisol/ocitocina). Modulação endócrina agora cria *estados de humor (moods)* duradouros que bloqueiam ou excitam as emoções agudas (Drives).'
)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)
