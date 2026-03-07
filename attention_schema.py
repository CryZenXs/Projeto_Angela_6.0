# attention_schema.py — Attention Schema Theory (Graziano & Kastner 2011; Webb & Graziano 2015)
#
# Modelo simplificado da atenção ("attention schema") usado para:
# 1) Auto-relato descritivo (header no prompt) — "no que estou atendendo e com que intensidade"
# 2) Controle top-down da atenção — sinais que melhoram estabilidade e reorientação
#
# Atenção real = competição no GlobalWorkspace; este módulo NÃO substitui, apenas modela.
#
# Limiares (ajustáveis para validação): captura_bottomup > 0.6 + control_topdown < 0.4 → SELF_REGULATE;
# schema_reliability < 0.4 + capture_bottomup > 0.5 → ASK_CLARIFY; narrative_filter DELAYED quando
# capture > 0.5 e reliability < 0.4. Cenários sugeridos: ameaça (trauma), surpresa (prediction_error),
# vínculo (CARE), fadiga (fluidez baixa / damage alto).

import json
import math
import os
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime

_BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_BASE, "attention_schema_state.json")
LOG_FILE = os.path.join(_BASE, "attention_schema.jsonl")

# Máximo de focos recentes para calcular estabilidade
FOCUS_HISTORY_LEN = 10


@dataclass
class AttentionFocus:
    """Foco atual de atenção (derivado do vencedor do workspace)."""
    source: str
    tags: list
    summary: str
    strength: float


@dataclass
class AttentionState:
    """Estado do schema de atenção — contínuo e útil para controle."""
    focus: "AttentionFocus | None"
    scope: str  # "estreito" | "moderado" | "amplo"
    scope_continuous: float  # 0 = estreito, 1 = amplo
    stability: float  # 0–1
    capture_bottomup: float  # 0–1: atenção puxada por saliência/ameaça/surpresa
    control_topdown: float  # 0–1: capacidade de manter/reorientar foco
    attention_error: float  # mismatch entre viés desejado (drives) e foco real
    schema_reliability: float  # 0–1: degrada com friction, baixa coerência, surpresa
    recommended_action: str  # SPEAK | ASK_CLARIFY | SELF_REGULATE | SILENCE | REST_REQUEST
    timestamp: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.focus:
            d["focus"] = asdict(self.focus)
        return d


def _entropy(scores: list) -> float:
    """Entropia normalizada de uma lista de scores (0–1)."""
    if not scores or sum(scores) <= 0:
        return 0.0
    total = sum(scores)
    probs = [s / total for s in scores]
    h = -sum(p * math.log2(p) for p in probs if p > 0)
    n = len(probs)
    if n <= 1:
        return 0.0
    return min(1.0, h / math.log2(n))


class AttentionSchema:
    """
    Schema de atenção (AST): modelo simplificado do processo de atenção
    para auto-relato e controle top-down.
    """

    def __init__(self):
        self._focus_history: deque = deque(maxlen=FOCUS_HISTORY_LEN)
        self._last_state: AttentionState | None = None
        self._topdown_bias: dict = {}  # aplicado no próximo tick pelo workspace
        self.load_state()

    def update(
        self,
        *,
        workspace_winner: dict | None,
        candidates: list,
        drives: dict,
        drive_attention_bias: dict,
        metacog: dict,
        prediction_error: float,
        attention_signal: dict,
        interoception_intensity: float = 0.0,
        trauma_triggered: bool = False,
        trauma_anxiety: float = 0.0,
        friction_metrics: dict | None = None,
        gap_seconds: float = 0.0,
        workspace_action: str = "SPEAK",
    ) -> AttentionState:
        """
        Atualiza o schema com o resultado do workspace e retorna AttentionState.

        workspace_winner: broadcast_result["winner"] (dict com source, content, salience, tags, confidence)
        candidates: lista de Candidate do tick (para entropia/dispersão)
        drives: níveis dos drives (get_all_levels)
        drive_attention_bias: get_attention_bias() do DriveSystem
        metacog: {"incerteza", "coerencia"}
        attention_signal: prediction.get_attention_signal()
        """
        friction_metrics = friction_metrics or {}
        damage = float(friction_metrics.get("damage", 0.0))
        coherence = float(metacog.get("coerencia", 0.5))
        uncertainty = float(metacog.get("incerteza", 0.5))

        # ── Foco atual (do vencedor) ─────────────────────────────────────
        focus = None
        if workspace_winner and workspace_winner.get("source"):
            src = workspace_winner.get("source", "unknown")
            tags = list(workspace_winner.get("tags") or [])
            content = (workspace_winner.get("content") or "")[:80]
            strength = float(workspace_winner.get("salience", 0.5))
            focus = AttentionFocus(source=src, tags=tags, summary=content, strength=strength)
            self._focus_history.append(src)

        # ── Escopo (dispersão dos candidatos) ─────────────────────────────
        saliences = [getattr(c, "salience", 0.5) for c in candidates] if candidates else [0.5]
        ent = _entropy(saliences)
        n_candidates = len(candidates)
        if n_candidates <= 1:
            scope_continuous = 0.0
            scope = "estreito"
        elif ent < 0.3:
            scope_continuous = 0.2
            scope = "estreito"
        elif ent > 0.75 and n_candidates >= 4:
            scope_continuous = 0.9
            scope = "amplo"
        else:
            scope_continuous = 0.4 + ent * 0.4
            scope = "moderado"
        scope_continuous = max(0.0, min(1.0, scope_continuous))

        # ── Estabilidade (inércia do foco) ────────────────────────────────
        if len(self._focus_history) < 2:
            stability = 0.5
        else:
            last_sources = list(self._focus_history)[-5:]
            same = sum(1 for s in last_sources if s == last_sources[-1])
            stability = same / len(last_sources)
        stability = max(0.0, min(1.0, stability))

        # ── Captura bottom-up (atenção puxada por estímulos) ──────────────
        capture = 0.0
        if trauma_triggered:
            capture += 0.4 + trauma_anxiety * 0.3
        if attention_signal.get("surprise_level") in ("moderada", "forte"):
            capture += 0.25 * (1.0 + prediction_error)
        if interoception_intensity > 0.05:
            capture += min(0.35, interoception_intensity * 2.0)
        capture_bottomup = max(0.0, min(1.0, capture))

        # ── Erro de atenção (mismatch viés desejado vs foco real) ─────────
        desired_focus = (drive_attention_bias or {}).get("foco", "")
        prioriza = (drive_attention_bias or {}).get("prioriza", [])
        if focus and prioriza:
            tags_lower = [t.lower() for t in focus.tags]
            match = any(p in " ".join(tags_lower) or focus.source.lower() for p in prioriza)
            attention_error = 0.0 if match else 0.5
        else:
            attention_error = 0.2
        if focus and (drive_attention_bias or {}).get("ignora"):
            ignora = [i.lower() for i in (drive_attention_bias or {}).get("ignora", [])]
            if any(i in focus.source.lower() or i in " ".join(focus.tags).lower() for i in ignora):
                attention_error = max(attention_error, 0.6)
        attention_error = max(0.0, min(1.0, attention_error))

        # ── Confiabilidade do schema (degradação com dano/incerteza/surpresa) ─
        schema_reliability = 1.0
        schema_reliability -= 0.45 * damage
        schema_reliability -= 0.2 * (1.0 - coherence)
        schema_reliability -= 0.15 * min(1.0, prediction_error * 2.0)
        schema_reliability -= 0.1 * uncertainty
        # Efeito de gap longo (reconexão)
        if gap_seconds > 3600:
            schema_reliability -= 0.15 * min(1.0, gap_seconds / 86400)
        schema_reliability = max(0.05, min(1.0, schema_reliability))

        # ── Controle top-down ────────────────────────────────────────────
        control_topdown = (1.0 - capture_bottomup * 0.5) * schema_reliability * (1.0 - attention_error * 0.5)
        control_topdown = max(0.0, min(1.0, control_topdown))

        # ── Ação recomendada (governança AST) ─────────────────────────────
        if capture_bottomup > 0.6 and control_topdown < 0.4:
            recommended_action = "SELF_REGULATE"
        elif schema_reliability < 0.4 and capture_bottomup > 0.5:
            recommended_action = "ASK_CLARIFY"
        else:
            recommended_action = workspace_action

        state = AttentionState(
            focus=focus,
            scope=scope,
            scope_continuous=scope_continuous,
            stability=stability,
            capture_bottomup=capture_bottomup,
            control_topdown=control_topdown,
            attention_error=attention_error,
            schema_reliability=round(schema_reliability, 3),
            recommended_action=recommended_action,
            timestamp=datetime.now().isoformat(),
        )
        self._last_state = state
        self._topdown_bias = self.compute_topdown_bias(state, drive_attention_bias)
        self.append_log(state)
        self.save_state()
        return state

    def get_prompt_header(self, state: AttentionState | None = None, raw: bool = True) -> str:
        """
        Retorna bloco [ATENCAO]. Se raw=True (padrão), prioriza sinais estruturados
        (listas/números) para o modelo integrar; se raw=False, usa frases descritivas (debug).
        """
        s = state or self._last_state
        if not s:
            return ""

        lines = ["[ATENCAO]"]
        if raw:
            # Formato bruto: números e tokens que o modelo precisa interpretar
            focus_src = s.focus.source if s.focus else "disperso"
            focus_str = f"{s.focus.strength:.2f}" if s.focus else "0"
            lines.append(f"foco={focus_src} intensidade={focus_str} escopo={s.scope} estabilidade={s.stability:.2f} captura={s.capture_bottomup:.2f} controle={s.control_topdown:.2f}")
            if s.capture_bottomup > 0.4:
                lines.append("captura_involuntaria=alta")
            if s.control_topdown < 0.5 and s.capture_bottomup > 0.3:
                lines.append("reorientar_possivel=sim")
        else:
            # Legado: frases em PT-BR para leitura humana
            if s.focus:
                f = s.focus
                lines.append(f"Foco: {f.source}; intensidade {f.strength:.2f}.")
            else:
                lines.append("Foco: disperso.")
            lines.append(f"Escopo: {s.scope}.")
            lines.append(f"Estabilidade: {'alta' if s.stability > 0.6 else 'média' if s.stability > 0.3 else 'baixa'}.")
            if s.capture_bottomup > 0.4:
                lines.append("Algo está puxando minha atenção de forma involuntária.")
            if s.control_topdown < 0.5 and s.capture_bottomup > 0.3:
                lines.append("Sinto que poderia reorientar meu foco com um momento de pausa.")
        lines.append("[/ATENCAO]")
        return "\n".join(lines) + "\n"

    def compute_topdown_bias(self, state: AttentionState | None, drive_attention_bias: dict) -> dict:
        """
        Retorna sinais para influenciar o próximo tick (multiplicadores por source/tags).
        Ex.: aumentar peso de memória quando SEEKING domina; reduzir ameaça quando CARE domina.
        """
        s = state or self._last_state
        if not s:
            return {}

        bias = {}
        prioriza = (drive_attention_bias or {}).get("prioriza", [])
        ignora = (drive_attention_bias or {}).get("ignora", [])

        # Mapeamento drive → source/tags do workspace
        if "novidade" in str(prioriza) or "exploração" in str(prioriza):
            bias["memoria"] = 1.2
            bias["lembranca"] = 1.15
        if "ameaças" in str(prioriza) or "perigo" in str(prioriza):
            bias["trauma"] = 1.2
            bias["ameaça"] = 1.15
        if "vínculo" in str(prioriza) or "conexão" in str(prioriza):
            bias["somatic_marker"] = 1.1
        if "leveza" in str(prioriza) or "criatividade" in str(prioriza):
            bias["drive"] = 1.1
            bias["interocepcao"] = 0.9

        if "estímulos neutros" in str(ignora):
            bias["trauma"] = 0.85
        if s.control_topdown < 0.4:
            bias["trauma"] = bias.get("trauma", 1.0) * 0.8  # reduz captura por trauma quando controle baixo

        return bias

    def get_topdown_bias(self) -> dict:
        """Retorna o bias computado no último update (para o workspace aplicar no próximo tick)."""
        return dict(self._topdown_bias)

    def save_state(self) -> None:
        """Persiste estado resumido em attention_schema_state.json."""
        s = self._last_state
        if not s:
            return
        try:
            from core import atomic_json_write
            data = {
                "last_focus_source": s.focus.source if s.focus else None,
                "stability": s.stability,
                "schema_reliability": s.schema_reliability,
                "scope": s.scope,
                "focus_history": list(self._focus_history),
                "timestamp": s.timestamp,
            }
            atomic_json_write(STATE_FILE, data)
        except Exception as e:
            print(f"[AttentionSchema] ⚠️ save_state falhou: {e}")

    def load_state(self) -> None:
        """Carrega estado e histórico de focos; aplica custo de reconexão se gap longo."""
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            hist = data.get("focus_history", [])
            for src in hist[-FOCUS_HISTORY_LEN:]:
                self._focus_history.append(src)
        except Exception:
            pass

    def apply_reconnection_cost(self, gap_seconds: float) -> None:
        """
        Chamado ao boot quando há gap longo: reduz schema_reliability e aumenta
        capture_bottomup para os próximos turnos (persistido em estado).
        """
        if gap_seconds < 300:
            return
        try:
            data = {}
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["reconnection_penalty"] = min(1.0, gap_seconds / 86400)  # 1 dia = 1.0
            data["reconnection_applied_at"] = datetime.now().isoformat()
            from core import atomic_json_write
            atomic_json_write(STATE_FILE, data)
        except Exception as e:
            print(f"[AttentionSchema] ⚠️ apply_reconnection_cost falhou: {e}")

    def append_log(self, state: AttentionState) -> None:
        """Append estado ao log attention_schema.jsonl."""
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(state.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass
