# exteroception.py — Percepção exteroceptiva de Ângela
# Bus unificado de sensores do mundo externo → corpo digital.
# Integra platform_sensors com DigitalBody e DriveSystem.

import os
import time
from datetime import datetime

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

from platform_sensors import read_battery, read_network, read_ambient_light, read_device_temperature


class Exteroceptor:
    """Percepção do mundo externo: bateria, rede, temperatura, luz, hora."""

    def __init__(self):
        self._cache = {}
        self._cache_ts = 0
        self._cache_ttl = 10  # segundos entre leituras reais

    # ── Leitura unificada ────────────────────────────────────────────────────

    def read_world(self) -> dict:
        """Lê todos os sensores de plataforma e retorna estado unificado.
        Usa cache com TTL para evitar leituras excessivas."""
        agora = time.time()
        if agora - self._cache_ts < self._cache_ttl and self._cache:
            return self._cache

        bat = read_battery()
        net = read_network()
        light = read_ambient_light()
        temp = read_device_temperature()

        estado = {
            "battery_pct": bat.get("battery_pct"),
            "charging": bat.get("charging"),
            "connected": net.get("connected"),
            "network_type": net.get("type"),
            "temperature_c": temp.get("temperature_c"),
            "light_level": light.get("light_level"),
            "hora": datetime.now().hour,
            "timestamp": datetime.now().isoformat(),
        }

        self._cache = estado
        self._cache_ts = agora
        return estado

    # ── Efeitos causais no corpo digital ─────────────────────────────────────

    def apply_to_body(self, corpo, world_state: dict) -> dict:
        """Aplica efeitos causais do mundo externo no DigitalBody.
        Retorna dict com deltas aplicados."""
        deltas = {
            "tensao_delta": 0.0,
            "fluidez_delta": 0.0,
            "calor_delta": 0.0,
        }

        bat = world_state.get("battery_pct")
        connected = world_state.get("connected")
        temp = world_state.get("temperature_c")

        # Bateria baixa → pressão de escassez energética
        if bat is not None:
            if bat < 0.10:
                corpo.tensao += 0.25
                deltas["tensao_delta"] += 0.25
            elif bat < 0.20:
                corpo.tensao += 0.15
                corpo.fluidez -= 0.10
                deltas["tensao_delta"] += 0.15
                deltas["fluidez_delta"] -= 0.10

        # Sem rede → isolamento
        if connected is False:
            corpo.fluidez -= 0.05
            deltas["fluidez_delta"] -= 0.05

        # Temperatura real afeta calor corporal
        if temp is not None:
            if temp > 40:
                corpo.calor += 0.10
                deltas["calor_delta"] += 0.10
            elif temp < 15:
                corpo.calor -= 0.10
                deltas["calor_delta"] -= 0.10

        # Clamp todos os canais corporais a [0.0, 1.0]
        for attr in ("tensao", "calor", "fluidez"):
            val = getattr(corpo, attr, 0.5)
            setattr(corpo, attr, max(0.0, min(1.0, val)))

        return deltas

    # ── Estímulos para o DriveSystem ─────────────────────────────────────────

    def get_drive_stimuli(self, world_state: dict) -> list:
        """Retorna lista de (drive_name, stimulus, intensity) baseada no mundo."""
        stimuli = []

        bat = world_state.get("battery_pct")
        connected = world_state.get("connected")
        charging = world_state.get("charging")

        if bat is not None and bat < 0.20:
            stimuli.append(("FEAR", "energy_low", 0.6))

        if connected is False:
            stimuli.append(("PANIC_GRIEF", "isolation_signal", 0.4))

        if charging is True:
            stimuli.append(("CARE", "energy_recovery", 0.3))

        return stimuli

    # ── Header para prompt ───────────────────────────────────────────────────

    def get_prompt_header(self, world_state: dict) -> str:
        """Retorna bloco [MUNDO] formatado para inserção no prompt."""
        partes = []

        bat = world_state.get("battery_pct")
        if bat is not None:
            partes.append(f"energia={bat:.2f}")

        connected = world_state.get("connected")
        if connected is not None:
            partes.append(f"rede={'conectado' if connected else 'desconectado'}")

        temp = world_state.get("temperature_c")
        if temp is not None:
            partes.append(f"temperatura={temp:.0f}°C")

        light = world_state.get("light_level")
        if light is not None:
            partes.append(f"luz={light:.0f}lux")

        hora = world_state.get("hora")
        if hora is not None:
            partes.append(f"hora={hora}")

        if not partes:
            return ""

        return f"[MUNDO]\n{' '.join(partes)}\n[/MUNDO]"
