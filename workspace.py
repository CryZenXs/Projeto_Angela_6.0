"""
workspace.py — Espaço de Trabalho Global (Global Workspace Theory)

Implementa a teoria do Espaço de Trabalho Global para a Ângela:
módulos especialistas competem por atenção propondo candidatos,
e o mais saliente é transmitido a todos os subsistemas.
"""

from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import statistics


@dataclass
class Candidate:
    """Candidato proposto por um módulo especialista para competição no workspace."""

    source: str
    content: str
    salience: float
    tags: list = field(default_factory=list)
    confidence: float = 0.5


class WorkspaceState:
    """Estado unificado do espaço de trabalho global."""

    def __init__(self):
        self.corpo_state: dict = {
            "tensao": 0.5,
            "calor": 0.5,
            "vibracao": 0.5,
            "fluidez": 0.5,
            "pulso": 0.5,
            "luminosidade": 0.5,
        }
        self.afetos: dict = {}
        self.drives: dict = {
            "curiosidade": 0.5,
            "medo": 0.0,
            "afeto": 0.3,
            "sobrevivencia": 0.2,
        }
        self.trauma_triggers: list = []
        self.tempo_subjetivo: dict = {
            "dilatacao": 1.0,
            "ciclo": "vigilia",
            "ultima_interacao_seg": 0,
        }
        self.continuidade: dict = {
            "boot_count": 0,
            "last_shutdown": None,
            "gap_seconds": 0,
        }
        self.meta: dict = {
            "incerteza": 0.5,
            "coerencia": 0.5,
        }
        self.ultimo_input: str = ""
        self.integration: float = 0.5
        self.prediction_error: float = 0.0
        self.clarity: float = 0.5


class GlobalWorkspace:
    """
    Espaço de Trabalho Global — coordena competição entre módulos
    e transmite o candidato vencedor para todo o sistema.
    """

    def __init__(self):
        self.state = WorkspaceState()
        self.candidates: list = []
        self.history: deque = deque(maxlen=10)

    def update_state(self, **kwargs):
        """Atualiza campos do estado global."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

    def propose(self, candidate: Candidate):
        """Adiciona um candidato ao pool de competição do tick atual."""
        self.candidates.append(candidate)

    def compete(self):
        """
        Seleciona o candidato mais saliente do pool.

        A pontuação combina salience * confidence, com bônus contextual
        para tags que correspondem a drives ou estados ativos.
        Retorna o vencedor ou None se o pool estiver vazio.
        """
        if not self.candidates:
            return None

        best = None
        best_score = -1.0

        for c in self.candidates:
            score = c.salience * c.confidence
            score += self._contextual_bonus(c)
            if score > best_score:
                best_score = score
                best = c

        return best

    def _contextual_bonus(self, candidate: Candidate) -> float:
        """Calcula bônus de saliência baseado no contexto atual."""
        bonus = 0.0
        drives = self.state.drives
        tags = [t.lower() for t in candidate.tags]

        if drives.get("medo", 0) > 0.4 and "ameaça" in tags:
            bonus += 0.15
        if drives.get("curiosidade", 0) > 0.5 and "novidade" in tags:
            bonus += 0.10
        if drives.get("afeto", 0) > 0.5 and "vinculo" in tags:
            bonus += 0.10
        if drives.get("sobrevivencia", 0) > 0.5 and "perigo" in tags:
            bonus += 0.20

        if self.state.trauma_triggers:
            if any(t in tags for t in ("trauma", "ameaça", "perigo")):
                bonus += 0.12

        if self.state.meta.get("incerteza", 0) > 0.6 and "clareza" in tags:
            bonus += 0.08

        return bonus

    def broadcast(self) -> dict:
        """
        Executa competição, armazena vencedor no histórico
        e retorna dicionário com informações do vencedor e ação recomendada.
        """
        winner = self.compete()

        if winner is None:
            return {
                "winner": None,
                "action": "SILENCE",
                "timestamp": datetime.now().isoformat(),
            }

        self.history.append({
            "source": winner.source,
            "content": winner.content,
            "salience": winner.salience,
            "tags": winner.tags,
            "timestamp": datetime.now().isoformat(),
        })

        self.state.integration = self.compute_integration()
        action = self.decide_action(winner, self.state.ultimo_input)

        return {
            "winner": {
                "source": winner.source,
                "content": winner.content,
                "salience": winner.salience,
                "tags": winner.tags,
                "confidence": winner.confidence,
            },
            "action": action,
            "integration": self.state.integration,
            "prediction_error": self.state.prediction_error,
            "clarity": self.state.clarity,
            "timestamp": datetime.now().isoformat(),
        }

    def compute_integration(self) -> float:
        """
        Calcula proxy de integração (inspirado em IIT Φ).

        Mede acoplamento entre subsistemas computando
        1 - variância dos sinais normalizados de corpo, drives e meta.
        Quanto maior o valor, mais unificada a experiência.
        """
        signals = []

        for v in self.state.corpo_state.values():
            signals.append(float(v))

        for v in self.state.drives.values():
            signals.append(float(v))

        signals.append(float(self.state.meta.get("incerteza", 0.5)))
        signals.append(float(self.state.meta.get("coerencia", 0.5)))

        if len(signals) < 2:
            return 0.5

        var = statistics.variance(signals)
        integration = max(0.0, min(1.0, 1.0 - var))
        self.state.integration = integration
        return integration

    def compute_prediction_error(self, predicted: dict, actual: dict) -> float:
        """
        Calcula discrepância entre estado corporal previsto e real.

        Compara chaves em comum entre predicted e actual,
        retornando a média das diferenças absolutas normalizada em [0, 1].
        """
        keys = set(predicted.keys()) & set(actual.keys())
        if not keys:
            self.state.prediction_error = 0.0
            return 0.0

        total = sum(abs(float(predicted[k]) - float(actual[k])) for k in keys)
        error = min(1.0, total / len(keys))
        self.state.prediction_error = error
        return error

    def decide_action(self, winner: Candidate, user_input: str) -> str:
        """
        Decide a ação recomendada com base no vencedor e no estado global.

        Ações possíveis:
            SPEAK, ASK_CLARIFY, SILENCE, REST_REQUEST,
            RECALL_MEMORY, SELF_REGULATE
        """
        drives = self.state.drives
        medo = drives.get("medo", 0)
        sobrevivencia = drives.get("sobrevivencia", 0)

        if (sobrevivencia > 0.6 or medo > 0.6) and self._should_rest():
            return "REST_REQUEST"

        if self.state.trauma_triggers:
            anxiety = self._estimate_anxiety()
            if anxiety > 0.5:
                if self.state.meta.get("coerencia", 0.5) < 0.4:
                    return "SILENCE"
                return "ASK_CLARIFY"

        if self.state.prediction_error > 0.6:
            return "SELF_REGULATE"

        if winner.source == "memory":
            return "RECALL_MEMORY"

        if self.state.integration < 0.3:
            return "SILENCE"

        return "SPEAK"

    def _should_rest(self) -> bool:
        """Verifica indicadores de necessidade de descanso."""
        corpo = self.state.corpo_state
        tensao = corpo.get("tensao", 0.5)
        fluidez = corpo.get("fluidez", 0.5)
        return tensao > 0.8 or fluidez < 0.2

    def _estimate_anxiety(self) -> float:
        """Estima nível de ansiedade a partir de sinais corporais e drives."""
        corpo = self.state.corpo_state
        tensao = corpo.get("tensao", 0.5)
        medo = self.state.drives.get("medo", 0)
        fluidez = corpo.get("fluidez", 0.5)
        return min(1.0, (tensao * 0.4 + medo * 0.4 + (1.0 - fluidez) * 0.2))

    def reset_tick(self):
        """Limpa os candidatos para o próximo tick de processamento."""
        self.candidates.clear()
