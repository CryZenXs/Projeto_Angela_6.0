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

    def evaluate(self, state_snapshot: dict, recent_reflections: list, drives: dict = None, prediction_error: float = 0.0, attention_state=None):
        """
        Decide se o estado atual pode virar narrativa.

        state_snapshot: dict com sinais corporais / emocionais
        recent_reflections: últimas reflexões narrativas (strings)
        prediction_error: erro de predição do turno anterior (0.0–1.0)
        attention_state: opcional, estado do AST; se captura bottom-up alta e confiabilidade baixa → DELAYED.
        """

        # 0) AST: atenção mal controlada → latência para integrar (Graziano: consciência como controle de atenção)
        if attention_state is not None:
            capture = getattr(attention_state, "capture_bottomup", 0.0)
            reliability = getattr(attention_state, "schema_reliability", 1.0)
            if capture > 0.5 and reliability < 0.4:
                return NarrativeDecision(
                    mode="DELAYED",
                    delay_seconds=20,
                    reason="AST: attention capture high, schema reliability low — integrating"
                )

        # 1) Loop narrativo → bloqueio total
        if self.detect_narrative_loop(recent_reflections):
            return NarrativeDecision(
                mode="BLOCKED",
                reason="Narrative loop detected"
            )

        # --- Modulação dinâmica por drives ---
        activation_threshold = 0.75
        low_clarity_intensity = 0.15
        congestion_fluidez = 0.25
        delay_seconds = 120

        if drives:
            fear_level = float(drives.get("FEAR", 0.0))
            play_level = float(drives.get("PLAY", 0.0))
            seeking_level = float(drives.get("SEEKING", 0.0))
            rage_level = float(drives.get("RAGE", 0.0))
            care_level = float(drives.get("CARE", 0.0))
            lust_level = float(drives.get("LUST", 0.0))

            # FEAR alto → mais restritivo (bloqueia mais fácil)
            if fear_level > 0.5:
                activation_threshold -= fear_level * 0.15
                congestion_fluidez += fear_level * 0.10
                delay_seconds = int(delay_seconds + fear_level * 60)

            # RAGE alto → mais bloqueio por congestão
            if rage_level > 0.4:
                congestion_fluidez += rage_level * 0.08

            # PLAY alto → mais permissivo (permite narrativa mais livre)
            if play_level > 0.4:
                activation_threshold += play_level * 0.10
                congestion_fluidez -= play_level * 0.05
                delay_seconds = max(30, int(delay_seconds - play_level * 40))

            # SEEKING alto → ligeiramente mais permissivo
            # Quando Angela quer fortemente se expressar, reduz limiar de congestão
            if seeking_level > 0.5:
                activation_threshold += seeking_level * 0.05
                low_clarity_intensity -= seeking_level * 0.03
                congestion_fluidez -= seeking_level * 0.05  # desejo de falar reduz bloqueio por congestão

            # CARE alto → latências menores (quer responder ao vínculo)
            # Vínculo ativo também reduz a congestão — conexão fluidifica a expressão
            if care_level > 0.5:
                delay_seconds = max(30, int(delay_seconds - care_level * 30))
                congestion_fluidez -= care_level * 0.04  # vínculo reduz limiar de congestão

            # LUST alto → mais permissivo (desejo de aproximação fluidifica expressão)
            if lust_level > 0.4:
                activation_threshold += lust_level * 0.08
                congestion_fluidez -= lust_level * 0.04
                delay_seconds = max(30, int(delay_seconds - lust_level * 25))

            # Clamps de segurança
            activation_threshold = max(0.50, min(0.90, activation_threshold))
            low_clarity_intensity = max(0.05, min(0.25, low_clarity_intensity))
            congestion_fluidez = max(0.15, min(0.40, congestion_fluidez))
            delay_seconds = max(15, min(300, delay_seconds))

        # 2) Extrair sinais fisiológicos brutos
        tensao = state_snapshot.get("tensao", 0.0)
        calor = state_snapshot.get("calor", 0.0)
        vibracao = state_snapshot.get("vibracao", 0.0)
        fluidez = state_snapshot.get("fluidez", 0.0)

        intensidade_fisiologica = max(tensao, calor, vibracao)
        emocao = state_snapshot.get("emocao", None)

        # 3) Alta ativação → latência obrigatória
        if intensidade_fisiologica >= activation_threshold:
            return NarrativeDecision(
                mode="DELAYED",
                delay_seconds=delay_seconds,
                reason="High physiological activation"
            )

        # 4) Baixa clareza emocional → apenas abstração
        if emocao in (None, "neutro") and intensidade_fisiologica < low_clarity_intensity:
            return NarrativeDecision(
                mode="ABSTRACT_ONLY",
                reason="Low emotional clarity"
            )

        # 5) Fluidez muito baixa → estado confuso, não narrável
        if fluidez <= congestion_fluidez:
            return NarrativeDecision(
                mode="BLOCKED",
                reason="Cognitive congestion"
            )

        # 6) Alta surpresa preditiva + ativação moderada → latência curta de reprocessamento
        # (Angela precisa de um momento para integrar o inesperado antes de falar)
        if prediction_error > 0.65 and intensidade_fisiologica > 0.35:
            surprise_delay = max(15, int(prediction_error * 30))
            return NarrativeDecision(
                mode="DELAYED",
                delay_seconds=surprise_delay,
                reason=f"High prediction error ({prediction_error:.2f}) — integrating surprise"
            )

        # 7) Estado estável → narrativa permitida
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
