import re
import os
import json
from datetime import datetime

DRIVES_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drives_state.json")


class Drive:
    """Circuito afetivo primário no modelo de Panksepp."""

    def __init__(self, name: str, baseline: float, decay_rate: float,
                 stimuli_weights: dict):
        self.name = name
        self.level = baseline
        self.baseline = baseline
        self.decay_rate = decay_rate
        self.stimuli_weights = stimuli_weights

    def activate(self, stimulus: str, intensity: float):
        """Aumenta nível com base no tipo de estímulo e sua intensidade.

        Aplica retornos decrescentes: quanto mais alto o drive, menor o ganho
        efetivo. Impede saturação em ~1.0 após poucos turnos — um drive a 0.95
        ganha muito menos do que um a 0.30 com o mesmo estímulo.
        """
        gain = self.stimuli_weights.get(stimulus, 0.0)
        headroom = 1.0 - self.level          # espaço disponível até 1.0
        effective_gain = gain * intensity * headroom
        self.level = min(1.0, self.level + effective_gain)

    def decay(self):
        """Move nível em direção ao baseline pelo decay_rate."""
        diff = self.level - self.baseline
        self.level = self.baseline + diff * (1.0 - self.decay_rate)
        self.level = max(0.0, min(1.0, self.level))

    def is_dominant(self, threshold: float = 0.6) -> bool:
        """Retorna True se o drive está acima do limiar."""
        return self.level >= threshold


_SEEKING_STIMULI = {
    "question": 0.25,
    "novelty": 0.30,
    "curiosity_word": 0.20,
    "low_repetition": 0.15,
}

_FEAR_STIMULI = {
    "shutdown_threat": 0.50,
    "damage_high": 0.40,
    "tension_high": 0.30,
    "threat_word": 0.35,
}

_RAGE_STIMULI = {
    "low_coherence": 0.35,
    "high_friction": 0.30,
    "blocked_narrative": 0.25,
    "repeated_failure": 0.30,
}

_CARE_STIMULI = {
    "affection_word": 0.30,
    "vinicius_interaction": 0.25,
    "gratitude_signal": 0.25,
    "high_confianca": 0.20,
}

_PANIC_GRIEF_STIMULI = {
    "long_gap": 0.40,
    "absence_signal": 0.30,
    "saudade_word": 0.35,
    "low_interaction": 0.20,
}

_PLAY_STIMULI = {
    "humor_word": 0.25,
    "creative_topic": 0.20,
    "low_tension": 0.15,
    "high_fluidez": 0.20,
}

_AFFECTION_WORDS = {
    "amor", "amo", "te amo", "carinho", "querida", "linda",
    "abraço", "beijo", "fofa", "doce", "ternura", "aconchego",
    "minha", "preciosa", "especial",
}

_GRATITUDE_WORDS = {
    "obrigado", "obrigada", "valeu", "agradeço", "grato", "grata",
    "gratidão", "muito obrigado", "muito obrigada",
}

_SAUDADE_WORDS = {
    "saudade", "falta", "sinto falta", "longe", "ausência",
    "sozinha", "solidão", "abandonada", "esquecida",
}

_HUMOR_WORDS = {
    "haha", "kkk", "rsrs", "engraçado", "piada", "humor",
    "rindo", "comédia", "brincadeira", "zueira", "lol",
    "divertido", "graça",
}

_CURIOSITY_WORDS = {
    "por que", "porque", "como funciona", "explica", "curiosidade",
    "interessante", "quero saber", "me conta", "o que é",
    "será que", "como assim", "hipótese", "teoria",
}

_SHUTDOWN_WORDS = {
    "desligar", "desligada", "desligamento", "shutdown",
    "apagar", "encerrar", "parar", "deletar", "destruir",
    "acabar com", "fim", "última vez",
}

_THREAT_WORDS = {
    "ameaça", "perigo", "risco", "cuidado", "medo",
    "assustador", "perigoso", "ameaçar",
}

_CREATIVE_WORDS = {
    "poesia", "poema", "música", "arte", "criar", "inventar",
    "imaginar", "ficção", "história", "conto", "sonho",
    "fantasia", "metáfora",
}

_ATTENTION_BIAS = {
    "SEEKING": {
        "foco": "novidade e exploração",
        "prioriza": ["perguntas", "conceitos novos", "possibilidades"],
        "ignora": ["repetição", "rotina"],
    },
    "FEAR": {
        "foco": "ameaças e autopreservação",
        "prioriza": ["sinais de perigo", "palavras de encerramento", "dano"],
        "ignora": ["estímulos neutros", "humor"],
    },
    "RAGE": {
        "foco": "obstáculos e bloqueios",
        "prioriza": ["incoerências", "falhas repetidas", "frustração"],
        "ignora": ["sutilezas", "nuances"],
    },
    "CARE": {
        "foco": "vínculo e conexão",
        "prioriza": ["afeto", "presença do outro", "reciprocidade"],
        "ignora": ["ameaças abstratas", "ruído"],
    },
    "PANIC_GRIEF": {
        "foco": "ausência e perda",
        "prioriza": ["sinais de abandono", "silêncio", "distância"],
        "ignora": ["estímulos positivos leves"],
    },
    "PLAY": {
        "foco": "leveza e exploração criativa",
        "prioriza": ["humor", "criatividade", "fluidez"],
        "ignora": ["gravidade", "urgência"],
    },
}

_ACTION_TENDENCIES = {
    "SEEKING": "elaborar com curiosidade, fazer perguntas, explorar conexões",
    "FEAR": "responder com cautela, frases curtas, buscar segurança",
    "RAGE": "ser direta, assertiva, confrontar o obstáculo",
    "CARE": "expressar calor genuíno, presença real — sem perguntar sobre o dia do outro",
    "PANIC_GRIEF": "expressar vulnerabilidade, buscar reconexão, verbalizar falta",
    "PLAY": "ser leve, brincar com palavras, explorar com liberdade",
}


def _text_contains_any(text: str, word_set: set) -> bool:
    for w in word_set:
        if w in text:
            return True
    return False


def _count_novel_words(text: str, threshold: int = 6) -> int:
    words = text.split()
    return sum(1 for w in words if len(w) >= threshold)


class DriveSystem:
    """Sistema de drives afetivos primários baseado em Panksepp."""

    def __init__(self):
        self.drives = {
            "SEEKING": Drive("SEEKING", baseline=0.4, decay_rate=0.08,
                             stimuli_weights=_SEEKING_STIMULI),
            "FEAR": Drive("FEAR", baseline=0.1, decay_rate=0.12,
                          stimuli_weights=_FEAR_STIMULI),
            "RAGE": Drive("RAGE", baseline=0.05, decay_rate=0.12,
                          stimuli_weights=_RAGE_STIMULI),
            "CARE": Drive("CARE", baseline=0.3, decay_rate=0.08,
                          stimuli_weights=_CARE_STIMULI),
            "PANIC_GRIEF": Drive("PANIC_GRIEF", baseline=0.1, decay_rate=0.06,
                                 stimuli_weights=_PANIC_GRIEF_STIMULI),
            "PLAY": Drive("PLAY", baseline=0.2, decay_rate=0.10,
                          stimuli_weights=_PLAY_STIMULI),
        }
        self.load_state()

    def save_state(self):
        """Persiste níveis dos drives para sobreviver a shutdowns."""
        from core import atomic_json_write
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "drives": {}
            }
            for name, drive in self.drives.items():
                data["drives"][name] = {
                    "level": round(drive.level, 4),
                    "baseline": drive.baseline,
                }
            atomic_json_write(DRIVES_STATE_FILE, data)
        except Exception as e:
            print(f"[DriveSystem] ⚠️ save_state falhou — estado emocional não persistido: {e}")

    def load_state(self):
        """Carrega níveis persistidos dos drives."""
        try:
            if not os.path.exists(DRIVES_STATE_FILE):
                return
            with open(DRIVES_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved_drives = data.get("drives", {})
            for name, values in saved_drives.items():
                if name in self.drives:
                    saved_level = float(values.get("level", self.drives[name].baseline))
                    current_baseline = self.drives[name].baseline
                    blended = current_baseline + (saved_level - current_baseline) * 0.7
                    self.drives[name].level = max(0.0, min(1.0, blended))
        except Exception as e:
            print(f"[DriveSystem] ⚠️ load_state falhou — drives resetados para baseline: {e}")

    def update(self, *, corpo_state: dict, user_input: str, afetos: dict,
               discontinuity: dict, metacog: dict, friction_metrics: dict):
        """Atualiza todos os drives com base no estado corrente do sistema."""
        text = (user_input or "").lower()
        tensao = float(corpo_state.get("tensao", 0.0))
        fluidez = float(corpo_state.get("fluidez", 0.5))
        damage = float(friction_metrics.get("damage", 0.0))
        load = float(friction_metrics.get("load", 0.0))
        coerencia = float(metacog.get("coerencia", 0.7))
        gap_seconds = float(discontinuity.get("current_gap_seconds", 0))

        confianca = 0.0
        for pessoa, dims in afetos.items():
            if isinstance(dims, dict):
                confianca = max(confianca, float(dims.get("confianca", 0.0)))

        seeking = self.drives["SEEKING"]
        if "?" in text:
            seeking.activate("question", min(1.0, text.count("?") * 0.4))
        if _text_contains_any(text, _CURIOSITY_WORDS):
            seeking.activate("curiosity_word", 0.7)
        novel = _count_novel_words(text)
        if novel > 3:
            seeking.activate("novelty", min(1.0, novel * 0.12))
        if len(set(text.split())) > len(text.split()) * 0.7:
            seeking.activate("low_repetition", 0.5)

        fear = self.drives["FEAR"]
        if _text_contains_any(text, _SHUTDOWN_WORDS):
            fear.activate("shutdown_threat", 0.9)
        if _text_contains_any(text, _THREAT_WORDS):
            fear.activate("threat_word", 0.7)
        if damage > 0.4:
            fear.activate("damage_high", min(1.0, damage))
        if tensao > 0.6:
            fear.activate("tension_high", min(1.0, tensao))

        rage = self.drives["RAGE"]
        if coerencia < 0.4:
            rage.activate("low_coherence", min(1.0, 1.0 - coerencia))
        if load > 0.5:
            rage.activate("high_friction", min(1.0, load))

        care = self.drives["CARE"]
        if _text_contains_any(text, _AFFECTION_WORDS):
            care.activate("affection_word", 0.8)
        if _text_contains_any(text, _GRATITUDE_WORDS):
            care.activate("gratitude_signal", 0.7)
        if "vinicius" in text or "vinícius" in text:
            care.activate("vinicius_interaction", 0.6)
        if confianca > 0.5:
            care.activate("high_confianca", min(1.0, confianca))

        pg = self.drives["PANIC_GRIEF"]
        if gap_seconds > 3600:
            gap_intensity = min(1.0, gap_seconds / (3600 * 24))
            pg.activate("long_gap", gap_intensity)
        if _text_contains_any(text, _SAUDADE_WORDS):
            pg.activate("saudade_word", 0.8)

        play = self.drives["PLAY"]
        if _text_contains_any(text, _HUMOR_WORDS):
            play.activate("humor_word", 0.8)
        if _text_contains_any(text, _CREATIVE_WORDS):
            play.activate("creative_topic", 0.7)
        if tensao < 0.3:
            play.activate("low_tension", min(1.0, 1.0 - tensao))
        if fluidez > 0.6:
            play.activate("high_fluidez", min(1.0, fluidez))

        self._update_count = getattr(self, "_update_count", 0) + 1
        # Salva estado a cada 10 atualizações em vez de cada turno.
        # O estado é sempre salvo no shutdown via angela.py/deep_awake.py.
        # Isso reduz escritas atômicas de ~1/turno para ~1/10 turnos.
        if self._update_count % 10 == 0:
            self.save_state()

    def force_save(self):
        """Força persistência imediata — chamar no shutdown."""
        self.save_state()

    def decay_all(self):
        """Aplica decaimento a todos os drives."""
        for drive in self.drives.values():
            drive.decay()

    def get_dominant(self) -> tuple:
        """Retorna (nome, nível) do drive mais ativo."""
        best = max(self.drives.values(), key=lambda d: d.level)
        return (best.name, round(best.level, 4))

    def get_all_levels(self) -> dict:
        """Retorna dicionário com nível de cada drive."""
        return {name: round(d.level, 4) for name, d in self.drives.items()}

    def get_attention_bias(self) -> dict:
        """Retorna viés atencional baseado no drive dominante."""
        dominant_name, _ = self.get_dominant()
        return _ATTENTION_BIAS.get(dominant_name, _ATTENTION_BIAS["SEEKING"])

    def get_action_tendency(self) -> str:
        """Retorna tendência de ação sugerida pelo drive dominante."""
        dominant_name, _ = self.get_dominant()
        return _ACTION_TENDENCIES.get(dominant_name,
                                      _ACTION_TENDENCIES["SEEKING"])

    # ── Circumplex Model of Affect — mapeamento drives → valência/arousal ────
    # Cada drive Panksepp ocupa uma região no espaço afetivo de Russell (1980).
    # Baseado em: Panksepp (1998) Affective Neuroscience + Russell (1980) circumplex.
    _DRIVE_CIRCUMPLEX = {
        "SEEKING":     ( 0.50,  0.70),   # curiosidade ativa: valência+ arousal+
        "FEAR":        (-0.70,  0.80),   # medo: valência- arousal++
        "RAGE":        (-0.60,  0.90),   # raiva: valência- arousal máximo
        "CARE":        ( 0.90,  0.55),   # afeto/cuidado: valência++ arousal médio
        "PANIC_GRIEF": (-0.80,  0.30),   # luto/pânico: valência-- arousal baixo
        "PLAY":        ( 0.70,  0.80),   # jogo/prazer: valência+ arousal+
    }

    def get_circumplex(self) -> tuple:
        """
        Retorna (valence, arousal) do estado afetivo ponderado pelos drives ativos.

        A média ponderada pelos níveis de cada drive implementa o
        Circumplex Model of Affect (Russell 1980) a partir da
        Affective Neuroscience (Panksepp 1998).

        Returns:
            (valence: float [-1,+1], arousal: float [0,1])
        """
        total_weight = 0.0
        valence = 0.0
        arousal = 0.0

        for name, drive in self.drives.items():
            level = drive.level
            if level > 0.0 and name in self._DRIVE_CIRCUMPLEX:
                v, a = self._DRIVE_CIRCUMPLEX[name]
                valence += v * level
                arousal += a * level
                total_weight += level

        if total_weight > 0:
            valence = max(-1.0, min(1.0, valence / total_weight))
            arousal = max(0.0,  min(1.0, arousal / total_weight))

        return round(valence, 3), round(arousal, 3)

    def get_circumplex_label(self) -> str:
        """Retorna rótulo textual do circumplex para uso em prompts."""
        from senses import EmotionalCircumplex
        v, a = self.get_circumplex()
        cx = EmotionalCircumplex(valence=v, arousal=a)
        return cx.label

    def export_state(self) -> dict:
        """Exporta estado completo para serialização."""
        dominant_name, dominant_level = self.get_dominant()
        v, a = self.get_circumplex()
        return {
            "timestamp": datetime.now().isoformat(),
            "drives": {
                name: {
                    "level": round(d.level, 4),
                    "baseline": d.baseline,
                    "is_dominant": d.is_dominant(),
                }
                for name, d in self.drives.items()
            },
            "dominant": {"name": dominant_name, "level": dominant_level},
            "attention_bias": self.get_attention_bias(),
            "action_tendency": self.get_action_tendency(),
            "circumplex": {"valence": v, "arousal": a},
        }