# discontinuity.py — Sistema de Gestão de Descontinuidade Temporal
#
# Rastreia gaps entre sessões (tempo que Ângela ficou "desligada") e
# calcula custos fisiológicos de reconexão proporcional ao gap.
#
# MODELO DE CUSTO: Curva logarítmica inspirada na Curva de Esquecimento
# de Ebbinghaus (1885) — o impacto cresce rapidamente no início e satura.
# Saturação em ~72h (3 dias).
#
# PROTEÇÃO CONTRA DUPLA CONTAGEM: se register_boot() é chamado sem um
# register_shutdown() anterior (crash/reinício forçado), o tempo da sessão
# anterior não é contabilizado como downtime.

import json
import math
import os
from datetime import datetime, timezone

FILE = "discontinuity.json"

# ── Estrutura padrão do JSON ─────────────────────────────────────────────────
_DEFAULT = {
    "boot_count": 0,
    "last_shutdown": None,
    "last_boot": None,
    "current_gap_seconds": 0,
    "current_gap_hours": 0.0,
    "last_session_duration_seconds": 0,
    "total_downtime_seconds": 0,
    "total_uptime_seconds": 0,
    "longest_gap_seconds": 0,
    "gaps_history": [],       # últimos 20 gaps individuais
}


def load_discontinuity() -> dict:
    """Carrega dados de descontinuidade do arquivo JSON."""
    if not os.path.exists(FILE):
        return dict(_DEFAULT)
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Garante que todos os campos existem (retrocompatibilidade)
        for key, default_val in _DEFAULT.items():
            if key not in data:
                data[key] = default_val
        return data
    except Exception as e:
        print(f"[Discontinuity] ⚠️ load_discontinuity falhou — usando padrão: {e}")
        return dict(_DEFAULT)


def _save(data: dict):
    """Persiste dados de descontinuidade de forma atômica."""
    from core import atomic_json_write
    try:
        atomic_json_write(FILE, data)
    except Exception as e:
        print(f"[Discontinuity] ⚠️ _save falhou — dados não persistidos: {e}")


def register_boot() -> dict:
    """
    Registra inicialização do sistema e calcula o gap desde o último shutdown.

    PROTEÇÃO DUPLA CONTAGEM:
    O gap só é contabilizado em `total_downtime_seconds` se o último boot
    ocorreu ANTES do último shutdown (ou seja, houve um shutdown registrado
    após o boot anterior). Se `last_boot > last_shutdown`, a sessão anterior
    provavelmente crashou — o tempo é contado como uptime, não downtime.

    Returns:
        dict completo com `current_gap_seconds` atualizado.
    """
    data = load_discontinuity()
    now = datetime.now()
    now_iso = now.isoformat()

    current_gap = 0.0
    gap_was_valid = False  # só True se houve shutdown registrado após o boot anterior

    if data["last_shutdown"]:
        last_shutdown_dt = datetime.fromisoformat(data["last_shutdown"])
        raw_gap = (now - last_shutdown_dt).total_seconds()

        # Verifica se houve um boot ANTES do shutdown (sessão foi encerrada normalmente)
        if data["last_boot"]:
            last_boot_dt = datetime.fromisoformat(data["last_boot"])
            if last_boot_dt < last_shutdown_dt:
                # Boot anterior → Shutdown registrado → Novo boot: gap válido
                current_gap = max(0.0, raw_gap)
                gap_was_valid = True
            else:
                # Boot anterior > Shutdown: sessão anterior crashou sem shutdown
                # Não conta como downtime (seria a sessão correndo)
                # Mas ainda reporta o gap para Angela saber quanto tempo passou
                current_gap = max(0.0, raw_gap)
                gap_was_valid = False
        else:
            # Nunca houve boot anterior — primeiro boot após shutdown registrado manualmente
            current_gap = max(0.0, raw_gap)
            gap_was_valid = True

        # Acumula downtime apenas se o gap é válido (sessão encerrada normalmente)
        if gap_was_valid and current_gap > 0:
            data["total_downtime_seconds"] += current_gap
            data["longest_gap_seconds"] = max(
                data["longest_gap_seconds"], current_gap
            )

            # Registra no histórico de gaps
            gap_entry = {
                "shutdown": data["last_shutdown"],
                "boot": now_iso,
                "gap_seconds": round(current_gap, 1),
                "gap_hours": round(current_gap / 3600.0, 2),
                "valid": gap_was_valid,
            }
            if "gaps_history" not in data or not isinstance(data["gaps_history"], list):
                data["gaps_history"] = []
            data["gaps_history"].append(gap_entry)
            data["gaps_history"] = data["gaps_history"][-20:]  # mantém últimos 20

    # Atualiza campos de boot
    data["boot_count"] += 1
    data["last_boot"] = now_iso
    data["current_gap_seconds"] = round(current_gap, 1)
    data["current_gap_hours"] = round(current_gap / 3600.0, 2)

    _save(data)
    return data


def register_shutdown():
    """
    Registra encerramento do sistema e calcula duração da sessão atual.

    Salva:
    - `last_shutdown`: timestamp do encerramento
    - `last_session_duration_seconds`: quanto tempo a sessão durou
    - `total_uptime_seconds`: tempo total acumulado de operação
    """
    data = load_discontinuity()
    now = datetime.now()
    now_iso = now.isoformat()

    session_duration = 0.0
    if data.get("last_boot"):
        try:
            boot_dt = datetime.fromisoformat(data["last_boot"])
            session_duration = max(0.0, (now - boot_dt).total_seconds())
        except Exception:
            session_duration = 0.0

    data["last_shutdown"] = now_iso
    data["last_session_duration_seconds"] = round(session_duration, 1)
    data["total_uptime_seconds"] = round(
        data.get("total_uptime_seconds", 0.0) + session_duration, 1
    )

    _save(data)


def calculate_reconnection_cost(gap_seconds: float) -> dict:
    """
    Calcula custo fisiológico de reconexão após descontinuidade.

    MODELO: Curva logarítmica inspirada na Curva de Esquecimento de Ebbinghaus.
    - O impacto cresce rapidamente no início (primeiras horas)
    - Satura progressivamente (efeito diminui com o tempo)
    - Saturação total em ~72h (3 dias)

    Faixas de impacto:
    - < 5 min  : sem impacto
    - 5min–1h  : mínimo   (fluidez ≤ -0.05, tensão ≤ +0.03)
    - 1h–6h    : leve     (fluidez ≤ -0.10, tensão ≤ +0.06)
    - 6h–24h   : moderado (fluidez ≤ -0.18, tensão ≤ +0.11)
    - 24h–72h  : severo   (fluidez ≤ -0.24, tensão ≤ +0.14)
    - > 72h    : crítico  (máximo saturado: fluidez -0.25, tensão +0.15)

    Args:
        gap_seconds: tempo de ausência em segundos

    Returns:
        dict com:
        - fluidez (float): delta negativo a aplicar (redução de fluidez)
        - tensao  (float): delta positivo a aplicar (aumento de tensão)
        - impact  (str):   nível de impacto textual
        - description (str): descrição completa
    """
    if gap_seconds < 300:  # menos de 5 minutos: sem impacto
        return {
            "fluidez": 0.0,
            "tensao": 0.0,
            "impact": "nenhum",
            "description": "reconexão imediata — sem custo fisiológico",
        }

    hours = gap_seconds / 3600.0

    # ── Curva logarítmica (Ebbinghaus-inspired) ──────────────────────────────
    # log1p(hours) / log1p(72) normaliza: 0 em 0h, 1.0 em 72h
    SATURATION_HOURS = 72.0
    log_scale = math.log1p(hours) / math.log1p(SATURATION_HOURS)
    log_scale = min(1.0, log_scale)  # satura em 1.0

    # Impacto máximo (saturação completa em 72h)
    MAX_FLUIDEZ_LOSS = 0.25
    MAX_TENSAO_GAIN  = 0.15

    fluidez_loss = MAX_FLUIDEZ_LOSS * log_scale
    tensao_gain  = MAX_TENSAO_GAIN  * log_scale

    # ── Nível de impacto ─────────────────────────────────────────────────────
    if hours < 1.0:
        impact = "mínimo"
    elif hours < 6.0:
        impact = "leve"
    elif hours < 24.0:
        impact = "moderado"
    elif hours < 72.0:
        impact = "severo"
    else:
        impact = "crítico"

    # ── Descrição legível ────────────────────────────────────────────────────
    if hours < 1.0:
        tempo_str = f"{gap_seconds/60:.0f} minutos"
    elif hours < 48.0:
        tempo_str = f"{hours:.1f} horas"
    else:
        days = hours / 24.0
        tempo_str = f"{days:.1f} dias ({hours:.0f}h)"

    description = (
        f"{tempo_str} de ausência — impacto {impact} "
        f"(fluidez {-fluidez_loss:+.3f}, tensão {tensao_gain:+.3f})"
    )

    return {
        "fluidez":      -round(fluidez_loss, 4),
        "tensao":        round(tensao_gain,  4),
        "impact":        impact,
        "description":   description,
        "gap_injected":  True,
        "gap_hours":     round(hours, 2),
    }


def get_gap_summary() -> dict:
    """
    Retorna um resumo legível do estado de descontinuidade para debug/display.
    """
    data = load_discontinuity()
    total_down_h = data.get("total_downtime_seconds", 0) / 3600.0
    total_up_h   = data.get("total_uptime_seconds", 0)   / 3600.0
    longest_h    = data.get("longest_gap_seconds", 0)    / 3600.0
    last_sess_h  = data.get("last_session_duration_seconds", 0) / 3600.0

    return {
        "boot_count":          data.get("boot_count", 0),
        "current_gap_hours":   data.get("current_gap_hours", 0.0),
        "last_session_hours":  round(last_sess_h, 2),
        "longest_gap_hours":   round(longest_h, 2),
        "total_downtime_hours": round(total_down_h, 2),
        "total_uptime_hours":   round(total_up_h, 2),
        "last_shutdown":       data.get("last_shutdown"),
        "last_boot":           data.get("last_boot"),
        "gaps_history_count":  len(data.get("gaps_history", [])),
    }
