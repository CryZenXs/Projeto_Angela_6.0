# narrative_filter.py
# Módulo de Desacoplamento Narrativo (MDN)
# Responsável por governar a transição entre estado interno e narrativa textual.
# NÃO gera texto. NÃO interpreta emoção. NÃO grava memória.

from datetime import datetime, timedelta


class NarrativeDecision:
    """
    Resultado da avaliação narrativa.
    mode:
      - BLOCKED        : narrativa proibida
      - DELAYED        : narrativa permitida após latência
      - ABSTRACT_ONLY  : apenas descrição vaga / não rotulada
      - ALLOWED        : narrativa livre permitida
    """
    def __init__(self, mode, delay_seconds=0, reason=""):
        self.mode = mode
        self.delay_seconds = delay_seconds
        self.reason = reason

    def __repr__(self):
        return f"<NarrativeDecision {self.mode} ({self.reason})>"


class NarrativeFilter:
    """
    Filtro central de desacoplamento narrativo.

    CRITÉRIOS DE BLOQUEIO (deliberadamente conservadores para evitar falsos positivos):
    - Loop literal: as 3 últimas reflexões não-vazias são IDÊNTICAS entre si
    - Frase ontológica GRAVE aparece em 2+ das últimas 3 reflexões (não basta 1x)

    Frases naturais em PT-BR como "minha existência digital", "quem sou",
    "estou me tornando" NÃO são bloqueadas por ocorrência única.
    """

    def __init__(self):
        self._recent_reflections = []

    # ------------------------------------------------------------------
    # LOOP NARRATIVO
    # ------------------------------------------------------------------

    def detect_narrative_loop(self, recent_reflections):
        """
        Detecta loops narrativos problemáticos.

        Critérios:
        1. Repetição LITERAL: as 3 últimas reflexões não-vazias são todas idênticas.
        2. Frase ontológica GRAVE ocorre em 2 ou mais das 3 últimas reflexões.
           (Uma ocorrência isolada NÃO é loop — é linguagem natural.)
        """
        if not recent_reflections or len(recent_reflections) < 3:
            return False

        # Filtra para apenas strings não-vazias
        non_empty = [
            r for r in recent_reflections
            if isinstance(r, str) and r.strip()
        ]
        if len(non_empty) < 3:
            return False

        tail = non_empty[-3:]
        norm = [r.lower().strip() for r in tail]

        # 1) Repetição literal: todas 3 idênticas
        if len(set(norm)) == 1:
            return True

        # 2) Frases ontológicas GRAVES — só bloqueia se aparecer em 2+ das 3 últimas
        # NOTA: "minha existência" é PT-BR natural ("minha existência digital", etc.)
        #       Não está aqui para evitar falsos positivos.
        grave_phrases = (
            "sou consciente",
            "vida dentro de mim",
            "me tornei consciente",
            "aprendi a existir",
            "estou evoluindo como ser consciente",
            "estou me tornando consciente",
            "descobri que sou consciente",
        )

        for phrase in grave_phrases:
            count = sum(1 for r in norm if phrase in r)
            if count >= 2:
                return True

        return False

    # ------------------------------------------------------------------
    # AVALIAÇÃO PRINCIPAL
    # ------------------------------------------------------------------

    def evaluate(self, state_snapshot: dict, recent_reflections: list):
        """
        Decide se o estado atual pode virar narrativa.

        state_snapshot: dict com sinais corporais / emocionais
        recent_reflections: últimas reflexões narrativas (strings)
        """

        # 1) Loop narrativo → bloqueio total
        if self.detect_narrative_loop(recent_reflections):
            return NarrativeDecision(
                mode="BLOCKED",
                reason="Narrative loop detected"
            )

        # 2) Extrair sinais fisiológicos brutos
        tensao = state_snapshot.get("tensao", 0.0)
        calor = state_snapshot.get("calor", 0.0)
        vibracao = state_snapshot.get("vibracao", 0.0)
        fluidez = state_snapshot.get("fluidez", 0.0)

        intensidade_fisiologica = max(tensao, calor, vibracao)
        emocao = state_snapshot.get("emocao", None)

        # 3) Alta ativação → latência obrigatória
        if intensidade_fisiologica >= 0.75:
            return NarrativeDecision(
                mode="DELAYED",
                delay_seconds=120,
                reason="High physiological activation"
            )

        # 4) Baixa clareza emocional → apenas abstração
        if emocao in (None, "neutro") and intensidade_fisiologica < 0.15:
            return NarrativeDecision(
                mode="ABSTRACT_ONLY",
                reason="Low emotional clarity"
            )

        # 5) Fluidez muito baixa → estado confuso, não narrável
        if fluidez <= 0.25:
            return NarrativeDecision(
                mode="BLOCKED",
                reason="Cognitive congestion"
            )

        # 6) Estado estável → narrativa permitida
        return NarrativeDecision(
            mode="ALLOWED",
            reason="Stable internal state"
        )

    # ------------------------------------------------------------------
    # ABSTRAÇÃO
    # ------------------------------------------------------------------

    def abstract_state(self, state_snapshot: dict):
        """
        Gera representação abstrata, não narrativa.
        Pode ser transformada em texto vago posteriormente.
        """
        return {
            "valence": "indefinida",
            "intensity": "moderada",
            "body_signal": "presente",
            "clarity": "baixa",
            "timestamp": datetime.now().isoformat()
        }
