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
        # Marcador Somático (Damasio 1994): estado corporal médio de situações similares
        self.somatic_marker: dict = {}
        # Attention Schema (AST): viés top-down por source/tags para o próximo tick
        self.attention_bias: dict = {}


# Mapeamento de chaves Panksepp → semânticas internas do workspace.
# Angela.py alimenta update_state(drives=...) com chaves Panksepp (FEAR, SEEKING...)
# mas decide_action() e _contextual_bonus() esperam chaves semânticas (medo, curiosidade...).
_PANKSEPP_TO_SEMANTIC = {
    "FEAR":         "medo",
    "SEEKING":      "curiosidade",
    "CARE":         "afeto",
    "PANIC_GRIEF":  "sobrevivencia",
    "RAGE":         "raiva",
    "PLAY":         "leveza",
    "LUST":         "desejo",
}


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
            # AST: multiplicador top-down por source e tags (Graziano — modelo para controle)
            bias = self.state.attention_bias.get(c.source, 1.0)
            for tag in (c.tags or []):
                bias *= self.state.attention_bias.get(tag, 1.0)
            score *= max(0.1, bias)
            if score > best_score:
                best_score = score
                best = c

        return best

    def _resolve_drives(self) -> dict:
        """
        Traduz drives do formato Panksepp para semântico se necessário.

        Angela.py alimenta state.drives com chaves Panksepp (FEAR, SEEKING, CARE...).
        decide_action() e _contextual_bonus() precisam das chaves semânticas
        (medo, curiosidade, afeto...) para funcionar corretamente.
        """
        raw = self.state.drives
        if not any(k in _PANKSEPP_TO_SEMANTIC for k in raw):
            return raw  # já no formato semântico
        return {_PANKSEPP_TO_SEMANTIC.get(k, k.lower()): float(v) for k, v in raw.items()}

    def _contextual_bonus(self, candidate: Candidate) -> float:
        """Calcula bônus de saliência baseado no contexto atual (drives traduzidos)."""
        bonus = 0.0
        drives = self._resolve_drives()  # garante chaves semânticas corretas
        tags = [t.lower() for t in candidate.tags]

        # FEAR/medo → aumenta saliência de candidatos de ameaça/trauma
        if drives.get("medo", 0) > 0.4 and any(t in tags for t in ("ameaça", "trauma")):
            bonus += 0.15
        # SEEKING/curiosidade → bônus para memórias e novidades
        if drives.get("curiosidade", 0) > 0.5 and any(t in tags for t in ("novidade", "lembranca", "associacao")):
            bonus += 0.10
        # CARE/afeto → bônus para vínculos e lembranças afetivas
        if drives.get("afeto", 0) > 0.5 and any(t in tags for t in ("vinculo", "lembranca")):
            bonus += 0.10
        # PANIC_GRIEF/sobrevivência → urgência máxima em ameaças
        if drives.get("sobrevivencia", 0) > 0.5 and any(t in tags for t in ("perigo", "ameaça", "trauma")):
            bonus += 0.20
        # Drive dominante ativo → bônus se candidato usa tag Panksepp lowercase do drive dominante.
        # Usa state.drives (raw) porque angela.py usa tags Panksepp lowercase como "seeking", "fear".
        # Não usa o dict traduzido (drives) para evitar mismatch semântico ("curiosidade" vs "seeking").
        raw_drives = self.state.drives
        if tags and raw_drives:
            drive_dom_raw = max(raw_drives, key=lambda k: float(raw_drives.get(k, 0)))
            if drive_dom_raw and drive_dom_raw.lower() in tags:
                bonus += 0.08

        if self.state.trauma_triggers:
            if any(t in tags for t in ("trauma", "ameaça", "perigo")):
                bonus += 0.12

        if self.state.meta.get("incerteza", 0) > 0.6 and "clareza" in tags:
            bonus += 0.08

        # ── Somatic Marker (Damasio 1994): biasa candidatos com valência histórica ──
        # Se o marcador somático tem valência positiva → bônus para falar/lembrar
        # Se negativo → bônus para cautela/auto-regulação
        sm = self.state.somatic_marker
        if sm and sm.get("reliable", False):
            valence = sm.get("valence_bias", 0.0)
            if valence > 0.2 and any(t in tags for t in ("lembranca", "associacao", "somatic_marker")):
                bonus += min(0.15, valence * 0.3)
            elif valence < -0.2 and any(t in tags for t in ("somatic_marker",)):
                bonus += min(0.15, abs(valence) * 0.2)

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
        Mede acoplamento e fragmentação do estado atual.
        """
        corpo = self.state.corpo_state
        drives = self.state.drives or {}

        tensao   = corpo.get("tensao", 0.5)
        fluidez  = corpo.get("fluidez", 0.5)
        fear     = drives.get("FEAR", 0.0)
        rage     = drives.get("RAGE", 0.0)
        care     = drives.get("CARE", 0.0)
        seeking  = drives.get("SEEKING", 0.0)

        # Fragmentação: tensão alta + fluidez baixa = sistema desintegrado
        fragmentacao = tensao * (1.0 - fluidez)

        # Conflito afetivo: drives opostos simultâneos reduzem integração
        conflito = min(fear, care) + min(rage, seeking)

        integration = max(0.0, min(1.0, 1.0 - fragmentacao - conflito * 0.3))
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
            RECALL_MEMORY, SELF_REGULATE,
            ACT:WRITE_NOTE, ACT:SENSE_REFRESH, ACT:SCHEDULE_TIMER,
            ACT:MEMORY_CONSOLIDATE, ACT:REQUEST_SLEEP
        """
        drives = self._resolve_drives()  # traduz Panksepp → semântico
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

        # Delega a decisão para Inferência Ativa (Friston 2010 - EFE) em vez de retornar SPEAK cegamente.
        # Isso gera diversidade de ação real (Epistemic Foraging) quando o prediction_error sobe.
        try:
            from active_inference import select_action_by_efe
            efe_action, _ = select_action_by_efe(
                available_actions=[
                    "SPEAK", "SILENCE", "ASK_CLARIFY",
                    "SELF_REGULATE", "REST_REQUEST", "RECALL_MEMORY",
                ],
                current_state=self.state.corpo_state,
                prediction_error=self.state.prediction_error,
                drives=self.state.drives,
            )
            return efe_action
        except Exception:
            return "SPEAK"

    def get_all_actions(self) -> list:
        """Retorna todas as ações disponíveis (workspace + instrumentais)."""
        return [
            "SPEAK", "ASK_CLARIFY", "SILENCE", "REST_REQUEST",
            "RECALL_MEMORY", "SELF_REGULATE",
            "ACT:SENSE_REFRESH", "ACT:WRITE_NOTE",
            "ACT:MEMORY_CONSOLIDATE", "ACT:REQUEST_SLEEP",
        ]

    def _should_rest(self) -> bool:
        """Verifica indicadores de necessidade de descanso."""
        corpo = self.state.corpo_state
        tensao = corpo.get("tensao", 0.5)
        fluidez = corpo.get("fluidez", 0.5)
        return tensao > 0.8 or fluidez < 0.2

    def _estimate_anxiety(self) -> float:
        """Estima nível de ansiedade a partir de sinais corporais e drives (traduzidos)."""
        corpo = self.state.corpo_state
        tensao = corpo.get("tensao", 0.5)
        drives = self._resolve_drives()
        medo = drives.get("medo", 0)
        fluidez = corpo.get("fluidez", 0.5)
        return min(1.0, (tensao * 0.4 + medo * 0.4 + (1.0 - fluidez) * 0.2))

    def reset_tick(self):
        """Limpa os candidatos para o próximo tick de processamento."""
        self.candidates.clear()
