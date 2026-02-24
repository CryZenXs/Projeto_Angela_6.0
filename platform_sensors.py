# platform_sensors.py — Sensores de plataforma para Ângela
# Abstrai leitura de bateria, rede, luz ambiente e temperatura
# para Termux/Android e Windows, com fallback silencioso.

import subprocess
import json
import socket
import platform

_IS_WINDOWS = platform.system() == "Windows"


def read_battery() -> dict:
    """Lê nível de bateria e estado de carregamento.
    Retorna {"battery_pct": float|None, "charging": bool|None}"""
    try:
        if not _IS_WINDOWS:
            # Termux/Android
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True, text=True, timeout=3
            )
            data = json.loads(result.stdout)
            pct = float(data.get("percentage", 0)) / 100.0
            status = data.get("status", "").upper()
            charging = status in ("CHARGING", "FULL")
            return {"battery_pct": pct, "charging": charging}
        else:
            # Windows via psutil
            import psutil
            bat = psutil.sensors_battery()
            if bat is not None:
                return {
                    "battery_pct": bat.percent / 100.0,
                    "charging": bat.power_plugged,
                }
    except Exception:
        pass
    return {"battery_pct": None, "charging": None}


def read_network() -> dict:
    """Verifica conectividade de rede.
    Retorna {"connected": bool|None, "type": str|None}"""
    try:
        if not _IS_WINDOWS:
            # Termux/Android — wifi info
            result = subprocess.run(
                ["termux-wifi-connectioninfo"],
                capture_output=True, text=True, timeout=3
            )
            data = json.loads(result.stdout)
            ssid = data.get("ssid", "")
            connected = ssid not in ("", "<unknown ssid>", None)
            net_type = "wifi" if connected else None
            return {"connected": connected, "type": net_type}
        else:
            # Windows — tenta conexão rápida a DNS público
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
            s.close()
            return {"connected": True, "type": "network"}
    except Exception:
        pass
    return {"connected": None, "type": None}


def read_ambient_light() -> dict:
    """Lê sensor de luz ambiente (apenas Termux, opcional).
    Retorna {"light_level": float|None}"""
    try:
        if not _IS_WINDOWS:
            result = subprocess.run(
                ["termux-sensor", "-s", "light", "-n", "1"],
                capture_output=True, text=True, timeout=3
            )
            data = json.loads(result.stdout)
            # Formato esperado: {"light": {"values": [lux]}}
            values = data.get("light", {}).get("values", [])
            if values:
                return {"light_level": float(values[0])}
    except Exception:
        pass
    return {"light_level": None}


def read_device_temperature() -> dict:
    """Lê temperatura do dispositivo (via bateria no Termux).
    Retorna {"temperature_c": float|None}"""
    try:
        if not _IS_WINDOWS:
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True, text=True, timeout=3
            )
            data = json.loads(result.stdout)
            temp = data.get("temperature")
            if temp is not None:
                return {"temperature_c": float(temp)}
    except Exception:
        pass
    return {"temperature_c": None}
