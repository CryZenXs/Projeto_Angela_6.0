"""
prediction_engine.py — Motor de Predição Interoceptiva

Gera previsões sobre o próximo estado corporal/emocional e calcula
erros de predição (surpresa) quando o estado real diverge.
"""

from collections import deque
from datetime import datetime


class PredictionEngine:
    """Prediz o próximo estado corporal e emocional, calcula erro de predição."""

    CHANNELS = ("tensao", "calor", "vibracao", "fluidez", "pulso", "luminosidade")

    def __init__(self, history_size: int = 20):
        self._history: deque = deque(maxlen=history_size)
        self._predicted: dict = {}
        self._actual: dict = {}
        self.current_error: float = 0.0
        self._channel_errors: dict = {ch: 0.0 for ch in self.CHANNELS}
        self._surprise_thresholds = {
            "nenhuma": 0.05,
            "leve": 0.12,
            "moderada": 0.25,
            "forte": 0.40,
        }

    def predict(self, *, corpo_state: dict, emocao_atual: str,
                drive_dominante: str, user_input: str,
                intensidade: float = 0.0) -> dict:
        """Gera predição do próximo estado baseado no histórico e contexto atual."""
        predicted = {}
        for ch in self.CHANNELS:
            val = corpo_state.get(ch, 0.5)
            if len(self._history) >= 2:
                prev = self._history[-1].get(ch, val)
                trend = val - prev
                predicted[ch] = max(0.0, min(1.0, val + trend * 0.6))
            else:
                predicted[ch] = val

        if intensidade > 0.6:
            predicted["tensao"] = min(1.0, predicted.get("tensao", 0.5) + 0.05)
            predicted["vibracao"] = min(1.0, predicted.get("vibracao", 0.5) + 0.03)

        self._predicted = predicted
        self._history.append(dict(corpo_state))
        return predicted

    def compare(self, actual_state: dict) -> dict:
        """Compara predição com estado real e calcula erro."""
        self._actual = actual_state
        total_error = 0.0
        most_surprising = ""
        max_ch_error = 0.0

        for ch in self.CHANNELS:
            p = self._predicted.get(ch, 0.5)
            a = actual_state.get(ch, 0.5)
            err = abs(p - a)
            self._channel_errors[ch] = err
            total_error += err
            if err > max_ch_error:
                max_ch_error = err
                most_surprising = ch

        n = len(self.CHANNELS)
        self.current_error = total_error / n if n > 0 else 0.0

        return {
            "prediction_error": self.current_error,
            "channel_errors": dict(self._channel_errors),
            "most_surprising_channel": most_surprising,
            "max_channel_error": max_ch_error,
        }

    def get_surprise_level(self) -> str:
        """Retorna nível categórico de surpresa."""
        for level in ("forte", "moderada", "leve", "nenhuma"):
            if self.current_error >= self._surprise_thresholds[level]:
                return level
        return "nenhuma"

    def get_attention_signal(self) -> dict:
        """Retorna sinais de atenção baseados no erro de predição."""
        surprise = self.get_surprise_level()
        should_attend = surprise in ("moderada", "forte")
        return {
            "should_attend_body": should_attend,
            "surprise_level": surprise,
            "prediction_error": self.current_error,
            "most_surprising": max(self._channel_errors, key=self._channel_errors.get)
            if self._channel_errors else "",
        }

    def get_prompt_context(self) -> str:
        """Retorna header de contexto para o prompt baseado na surpresa."""
        level = self.get_surprise_level()
        if level in ("nenhuma", "leve"):
            return ""
        most = max(self._channel_errors, key=self._channel_errors.get) if self._channel_errors else "?"
        return (
            f"[SURPRESA_PREDITIVA]\n"
            f"nivel=\"{level}\"\n"
            f"canal_surpreendente=\"{most}\"\n"
            f"erro={self.current_error:.3f}\n"
            f"[/SURPRESA_PREDITIVA]\n"
        )
