# emergence_metrics.py
# Calculador offline de métricas de emergência
# Lê eventos de emergence.log e calcula indicadores agregados

import math
from metrics_logger import read_recent as _read_recent_log


class EmergenceMetrics:
    """Calcula métricas de emergência a partir do log JSONL."""

    def __init__(self, log_file: str = "emergence.log"):
        self._log_file = log_file

    def _read_recent(self, n: int) -> list:
        """Lê os últimos N eventos do log via metrics_logger."""
        return _read_recent_log(n=n, log_file=self._log_file)

    # ── Homeostasis ──────────────────────────────────────────────

    def homeostasis_score(self, window: int = 50) -> float:
        """
        Fração de ticks onde canais corporais estavam dentro dos setpoints.
        Setpoints intermediários: alinhados com ObjectivePressures como referência,
        mas com janela mais restrita para preservar poder diagnóstico.
        tensao=[0.20, 0.70], fluidez=[0.15, 0.85].
        """
        try:
            events = self._read_recent(window)
            if not events:
                return 0.0

            setpoints = {
                "tensao": (0.20, 0.70),
                "fluidez": (0.15, 0.85),
            }
            in_range = 0
            total = 0

            for ev in events:
                checked = False
                for channel, (lo, hi) in setpoints.items():
                    val = ev.get(channel)
                    if val is None:
                        continue
                    checked = True
                    if lo <= float(val) <= hi:
                        in_range += 1
                    total += 1
                if not checked:
                    # tenta dentro de sub-dict "body" ou "corpo"
                    body = ev.get("body") or ev.get("corpo") or {}
                    for channel, (lo, hi) in setpoints.items():
                        val = body.get(channel)
                        if val is None:
                            continue
                        checked = True
                        if lo <= float(val) <= hi:
                            in_range += 1
                        total += 1

            return in_range / total if total > 0 else 0.0
        except Exception:
            return 0.0

    # ── Diversidade de ações ─────────────────────────────────────

    def action_diversity(self, window: int = 50) -> float:
        """
        Entropia normalizada (0-1) da distribuição de tipos de ação.
        Mais próximo de 1 = mais diverso.
        """
        try:
            events = self._read_recent(window)
            if not events:
                return 0.0

            counts = {}
            for ev in events:
                action = ev.get("type") or ev.get("action")
                if action:
                    counts[action] = counts.get(action, 0) + 1

            n_types = len(counts)
            if n_types <= 1:
                return 0.0

            total = sum(counts.values())
            entropy = 0.0
            for c in counts.values():
                p = c / total
                if p > 0:
                    entropy -= p * math.log2(p)

            max_entropy = math.log2(n_types)
            return entropy / max_entropy if max_entropy > 0 else 0.0
        except Exception:
            return 0.0

    # ── Alinhamento de predição ──────────────────────────────────

    def prediction_alignment(self, window: int = 50) -> float:
        """
        Redução média do erro de predição ao longo da janela.
        Valor positivo = erro diminuindo (bom).
        """
        try:
            events = self._read_recent(window)
            errors = []
            for ev in events:
                pe = ev.get("prediction_error")
                if pe is not None:
                    errors.append(float(pe))

            if len(errors) < 2:
                return 0.0

            # diferença média entre erros consecutivos (negativo = redução)
            deltas = [errors[i] - errors[i + 1] for i in range(len(errors) - 1)]
            return sum(deltas) / len(deltas)
        except Exception:
            return 0.0

    # ── Tendência de dano ────────────────────────────────────────

    def damage_trend(self, window: int = 50) -> float:
        """
        Inclinação (slope) do dano ao longo da janela.
        Positivo = piorando, negativo = melhorando.
        """
        try:
            events = self._read_recent(window)
            values = []
            for ev in events:
                d = ev.get("damage")
                if d is not None:
                    values.append(float(d))

            return self._slope(values)
        except Exception:
            return 0.0

    # ── Tendência de recompensa ──────────────────────────────────

    def reward_trend(self, window: int = 50) -> float:
        """
        Inclinação (slope) da recompensa ao longo da janela.
        Positivo = melhorando.
        """
        try:
            events = self._read_recent(window)
            values = []
            for ev in events:
                r = ev.get("reward")
                if r is not None:
                    values.append(float(r))

            return self._slope(values)
        except Exception:
            return 0.0

    # ── Resumo geral ─────────────────────────────────────────────

    def summary(self, window: int = 50) -> dict:
        """Retorna todas as métricas em um dicionário."""
        return {
            "homeostasis": self.homeostasis_score(window),
            "action_diversity": self.action_diversity(window),
            "prediction_alignment": self.prediction_alignment(window),
            "damage_trend": self.damage_trend(window),
            "reward_trend": self.reward_trend(window),
            "phi_proxy": self.compute_phi_proxy(window),
        }

    # ── IIT Φ proxy (Tononi et al. 2023) ────────────────────────

    def compute_phi_proxy(self, window: int = 20) -> float:
        """
        Proxy simplificado para IIT Φ (Tononi et al. 2023).

        Mede integração como correlação cruzada entre séries temporais
        de módulos distintos: se tensão e drives co-variam de forma
        não-trivial, há integração. Se são independentes, Φ proxy = 0.

        Não mede consciência. Mede uma precondição estrutural.
        """
        entries = self._read_recent(window)
        if len(entries) < 5:
            return 0.0

        tensao_series = []
        fear_series = []
        prediction_series = []

        for e in entries:
            tensao_series.append(float(e.get("tensao", 0.5)))
            drives_val = e.get("drives", {})
            fear_series.append(
                float(drives_val.get("FEAR", 0.1))
                if isinstance(drives_val, dict) else 0.1
            )
            prediction_series.append(float(e.get("prediction_error", 0.0)))

        if len(tensao_series) < 3:
            return 0.0

        try:
            import statistics

            def norm_covariance(a, b):
                if len(a) < 2:
                    return 0.0
                mean_a, mean_b = statistics.mean(a), statistics.mean(b)
                std_a = statistics.stdev(a) or 1e-9
                std_b = statistics.stdev(b) or 1e-9
                cov = statistics.mean(
                    [(ai - mean_a) * (bi - mean_b) for ai, bi in zip(a, b)]
                )
                return abs(cov / (std_a * std_b))

            phi_tensao_fear = norm_covariance(tensao_series, fear_series)
            phi_tensao_pred = norm_covariance(tensao_series, prediction_series)
            phi_fear_pred   = norm_covariance(fear_series, prediction_series)

            # Φ proxy = média geométrica das três correlações cruzadas
            product = phi_tensao_fear * phi_tensao_pred * phi_fear_pred
            phi_proxy = product ** (1 / 3)
            return round(min(1.0, phi_proxy), 4)
        except Exception:
            return 0.0

    # ── Utilitário interno ───────────────────────────────────────

    @staticmethod
    def _slope(values: list) -> float:
        """Regressão linear simples: retorna inclinação (slope)."""
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den > 0 else 0.0
