# objective_pressures.py — Computação homeostática de recompensa
# Calcula reward puramente a partir de métricas do sistema, sem LLM.

import os

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


class ObjectivePressures:
    """Pressões objetivas: recompensa homeostática computada sem LLM."""

    def __init__(self):
        # Setpoints homeostáticos (min, max) — faixa preferida.
        # Heurística: só punir disfunção real (tensao>0.85, fluidez<0.08).
        # Estados emocionalmente ricos (vibracao alta, PLAY alto) NÃO são disfunção.
        self.setpoints = {
            # Canais corporais
            "tensao":   (0.15, 0.85),   # ansiedade real só acima de 0.85
            "fluidez":  (0.08, 0.95),   # congestionamento real só abaixo de 0.08
            "vibracao": (0.08, 0.90),   # PLAY empurra vibracao alto — ok
            "calor":    (0.10, 0.88),   # calor alto pode ser amor/engajamento
            # Drives — PLAY/SEEKING altos são desejáveis, não punir
            "CARE":     (0.15, 0.92),
            "SEEKING":  (0.15, 0.95),
            "PLAY":     (0.05, 0.95),   # PLAY alto = saudável
            "FEAR":     (0.00, 0.60),   # FEAR acima de 0.60 é problemático
            "RAGE":     (0.00, 0.55),   # RAGE alto é sinal de bloqueio real
            # Sistema
            "damage":   (0.00, 0.50),
            "energia":  (0.20, 1.00),
        }
        # Canais do corpo avaliados no loop homeostático principal
        self._body_channels = ("tensao", "fluidez", "vibracao", "calor")
        # Canais de drives avaliados se presentes em state["drives_state"]
        self._drive_channels = ("CARE", "SEEKING", "PLAY", "FEAR", "RAGE")
        self.weights = {
            "homeostasis": 1.2,
            "damage_penalty": -2.0,
            "action_cost": -0.5,
            "pred_error_reduction": 0.6,
            "novelty_bonus": 0.2,
        }
        self._last_state: dict = {}

    def distance_to_setpoint(self, channel: str, value: float) -> float:
        """
        Retorna 0.0 se dentro da faixa, distância positiva caso contrário.
        """
        if channel not in self.setpoints:
            return 0.0
        lo, hi = self.setpoints[channel]
        if value < lo:
            return lo - value
        if value > hi:
            return value - hi
        return 0.0

    def compute_reward(self, state: dict) -> dict:
        """
        Calcula recompensa total a partir de métricas do sistema.

        state deve conter:
            corpo_state: dict (tensao, fluidez, vibracao, calor, etc.)
            drives_state: dict (CARE, SEEKING, PLAY, FEAR, RAGE, etc.)  # opcional
            damage: float
            damage_prev: float
            pred_error: float
            pred_error_prev: float
            action_cost: float
            action_name: str
            action_succeeded: bool
            is_novel_action: bool
        """
        corpo = state.get("corpo_state", {})
        drives = state.get("drives_state", {})
        damage = float(state.get("damage", 0.0))
        damage_prev = float(state.get("damage_prev", damage))
        pred_error = float(state.get("pred_error", 0.0))
        pred_error_prev = float(state.get("pred_error_prev", pred_error))
        action_cost = float(state.get("action_cost", 0.0))
        is_novel = bool(state.get("is_novel_action", False))

        # ── Homeostasis: melhoria em direção aos setpoints ───────────────
        homeostasis_detail = {}
        homeostasis_reward = 0.0

        # Canais corporais
        for channel in self._body_channels:
            current_val = float(corpo.get(channel, 0.5))
            dist_now = self.distance_to_setpoint(channel, current_val)
            homeostasis_detail[channel] = round(dist_now, 4)

            prev_val = float(self._last_state.get("corpo_state", {}).get(channel, current_val))
            dist_prev = self.distance_to_setpoint(channel, prev_val)
            homeostasis_reward += (dist_prev - dist_now)

        # Canais de drives (se fornecidos)
        for drive in self._drive_channels:
            if drive not in drives:
                continue
            current_val = float(drives.get(drive, 0.5))
            dist_now = self.distance_to_setpoint(drive, current_val)
            homeostasis_detail[drive] = round(dist_now, 4)

            prev_val = float(self._last_state.get("drives_state", {}).get(drive, current_val))
            dist_prev = self.distance_to_setpoint(drive, prev_val)
            homeostasis_reward += (dist_prev - dist_now) * 0.5  # peso menor que canais corporais

        homeostasis_component = homeostasis_reward * self.weights["homeostasis"]

        # ── Damage penalty ───────────────────────────────────────────────
        damage_delta = damage - damage_prev
        damage_component = damage_delta * self.weights["damage_penalty"]

        # ── Action cost penalty ──────────────────────────────────────────
        action_component = action_cost * self.weights["action_cost"]

        # ── Prediction error reduction ───────────────────────────────────
        pred_delta = pred_error_prev - pred_error  # positivo se melhorou
        pred_component = pred_delta * self.weights["pred_error_reduction"]

        # ── Novelty bonus (com guardrails) ───────────────────────────────
        novelty_component = 0.0
        if is_novel:
            # Guardrails: novelty só conta se seguro
            tensao_atual = float(corpo.get("tensao", 0.5))
            # Guardrail alinhado com novo bound: disfunção real = tensao > 0.85
            if damage_delta <= 0 and tensao_atual < 0.85:
                novelty_component = self.weights["novelty_bonus"]

        # ── Total ────────────────────────────────────────────────────────
        total_reward = (
            homeostasis_component
            + damage_component
            + action_component
            + pred_component
            + novelty_component
        )

        # ── Within bounds ────────────────────────────────────────────────
        # Todos os canais corporais devem estar dentro dos bounds corrigidos
        body_ok = all(
            self.distance_to_setpoint(ch, float(corpo.get(ch, 0.5))) == 0.0
            for ch in self._body_channels
            if ch in corpo
        )
        # Drives críticos de disfunção (FEAR e RAGE fora dos bounds = sinal real)
        drives_ok = all(
            self.distance_to_setpoint(d, float(drives.get(d, 0.3))) == 0.0
            for d in ("FEAR", "RAGE")
            if d in drives
        )
        within_bounds = body_ok and drives_ok

        return {
            "reward": round(total_reward, 4),
            "components": {
                "homeostasis": round(homeostasis_component, 4),
                "damage": round(damage_component, 4),
                "action_cost": round(action_component, 4),
                "pred_error": round(pred_component, 4),
                "novelty": round(novelty_component, 4),
            },
            "homeostasis_detail": homeostasis_detail,
            "within_bounds": within_bounds,
        }

    def update_last_state(self, state: dict):
        """Salva estado atual para cálculo de delta no próximo tick."""
        self._last_state = dict(state)
