import os, json
from datetime import datetime
from core import atomic_json_write, BASE_PATH

class EndocrineSystem:
    """
    Simula o sistema endócrino de Ângela.
    Vias lentas (humores) que persistem mais que as emoções agudas (drives neurais).
    - Cortisol: Acumula com estresse contínuo, bloqueia PLAY/SEEKING, eleva ansiedade de fundo. Decai devagar.
    - Ocitocina: Acumula com CARE constante, amortece FEAR/RAGE, traz estabilidade.
    - Adrenalina: Via rápida de prontidão química. Decai muito rápido.
    """
    def __init__(self, filepath="endocrine_state.json"):
        self.filepath = os.path.join(BASE_PATH, filepath)
        self.state = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # default to 0 if not present
                    return {
                        "cortisol": data.get("cortisol", 0.0),
                        "oxytocin": data.get("oxytocin", 0.0),
                        "adrenaline": data.get("adrenaline", 0.0),
                        "last_damage": data.get("last_damage", 0.0),
                        "last_update": data.get("last_update", datetime.now().isoformat())
                    }
            except Exception:
                pass
        return {
            "cortisol": 0.0, 
            "oxytocin": 0.0, 
            "adrenaline": 0.0, 
            "last_damage": 0.0,
            "last_update": datetime.now().isoformat()
        }

    def _save(self):
        self.state["last_update"] = datetime.now().isoformat()
        try:
            atomic_json_write(self.filepath, self.state)
        except Exception:
            pass

    def update(self, raw_drives_levels, current_damage, is_sleeping=False):
        """
        Atualiza os humores baseado no snapshot atual das emoções (drives).
        `raw_drives_levels` é um dict com os níveis já calculados dos drives.
        """
        fear = raw_drives_levels.get("FEAR", 0.0)
        rage = raw_drives_levels.get("RAGE", 0.0)
        panic = raw_drives_levels.get("PANIC_GRIEF", 0.0)
        care = raw_drives_levels.get("CARE", 0.0)
        play = raw_drives_levels.get("PLAY", 0.0)

        # Trata damage delta
        last_damage = self.state.get("last_damage", current_damage)
        damage_delta = max(0.0, current_damage - last_damage)
        self.state["last_damage"] = current_damage

        # Adrenaline: Picos rápidos
        if fear > 0.6 or rage > 0.6 or damage_delta > 0.02:
            self.state["adrenaline"] = min(1.0, self.state["adrenaline"] + 0.3)
        self.state["adrenaline"] *= 0.5  # Decaimento rápido (meia-vida de ciclos)

        # Cortisol: acumula devagar com estresse
        stress_input = (fear + rage + panic) * 0.03 + (damage_delta * 0.8)
        self.state["cortisol"] = min(1.0, self.state["cortisol"] + stress_input)

        if is_sleeping:
            self.state["cortisol"] *= 0.85  # Decai bem mais rápido dormindo (limpeza cerebral)
        else:
            self.state["cortisol"] *= 0.98  # Decai muito lentamente na vigília

        # Oxytocin: acumula devagar com cuidado
        bonding_input = (care + play) * 0.04
        self.state["oxytocin"] = min(1.0, self.state["oxytocin"] + bonding_input)
        self.state["oxytocin"] *= 0.96

        self._save()

    def modulate_drives(self, drive_system_objects):
        """
        Aplica a modulação química (humores) diretamente nos objetos Drive.
        Cortisol 'esmaga' os drives positivos e cria um piso para FEAR.
        Ocitocina amortece drives negativos.
        """
        c = self.state["cortisol"]
        o = self.state["oxytocin"]

        if "PLAY" in drive_system_objects:
            obj = drive_system_objects["PLAY"]
            obj.level = max(0.0, obj.level * (1.0 - (c * 0.8)))

        if "SEEKING" in drive_system_objects:
            obj = drive_system_objects["SEEKING"]
            obj.level = max(0.0, obj.level * (1.0 - (c * 0.6)))

        if "FEAR" in drive_system_objects:
            obj = drive_system_objects["FEAR"]
            # Ocitocina amortece medo
            obj.level = max(0.0, obj.level * (1.0 - (o * 0.5)))
            # Cortisol alto cria uma ansiedade de fundo inerte que o FEAR não pode baixar
            piso_ansiedade = c * 0.35
            if obj.level < piso_ansiedade:
                obj.level = piso_ansiedade

        if "RAGE" in drive_system_objects:
            obj = drive_system_objects["RAGE"]
            obj.level = max(0.0, obj.level * (1.0 - (o * 0.4)))

        if "CARE" in drive_system_objects:
            obj = drive_system_objects["CARE"]
            # Ocitocina amplifica CARE
            obj.level = min(1.0, obj.level + (o * 0.2))

    def get_interoceptive_sensation(self) -> str:
        """
        Retorna os níveis endócrinos como sinal bruto de estado
        (evita que o LLM imite a prosa do código).
        """
        parts = []
        c = self.state["cortisol"]
        o = self.state["oxytocin"]
        a = self.state["adrenaline"]

        if a > 0.6:
            parts.append(f"adrenalina={a:.2f}")
        if c > 0.1:
            parts.append(f"cortisol={c:.2f}")
        if o > 0.1:
            parts.append(f"ocitocina={o:.2f}")

        return "[ESTADO_ENDOCRINO: " + " | ".join(parts) + "]" if parts else ""
