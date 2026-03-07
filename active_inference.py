"""
active_inference.py — Expected Free Energy para seleção de ação

Implementa a versão simplificada do Princípio de Energia Livre (Friston 2010).
Não substitui o workspace — complementa decide_action() com EFE como critério
alternativo quando o workspace não tem vencedor claro (integration < 0.5).

EFE(ação) = Pragmático(ação) + Epistêmico(ação)
  Pragmático: distância do estado esperado ao estado preferido
  Epistêmico: redução esperada do erro de predição (-ganho de informação)
  → selecionar ação com menor EFE
"""

# Estado preferido — baseado nos setpoints homeostáticos do sistema
_PREFERRED_STATE = {
    "tensao":       0.30,
    "calor":        0.50,
    "vibracao":     0.45,
    "fluidez":      0.60,
    "pulso":        0.50,
    "luminosidade": 0.55,
}

# Deltas esperados por ação sobre o estado corporal
_ACTION_STATE_DELTAS = {
    "SPEAK":         {"tensao": +0.02, "fluidez": +0.05, "calor": +0.03},
    "SILENCE":       {"tensao": -0.03, "fluidez": -0.04, "calor": -0.02},
    "SELF_REGULATE": {"tensao": -0.05, "fluidez": +0.03, "calor": -0.02},
    "REST_REQUEST":  {"tensao": -0.08, "fluidez": -0.02, "calor": -0.03},
    "ASK_CLARIFY":   {"tensao": +0.01, "fluidez": +0.06, "calor": +0.02},
    "RECALL_MEMORY": {"tensao":  0.00, "fluidez": +0.04, "calor": +0.04},
}

# Ganho epistêmico base por ação
_EPISTEMIC_GAIN = {
    "SPEAK":         0.15,
    "ASK_CLARIFY":   0.20,
    "RECALL_MEMORY": 0.10,
    "SELF_REGULATE": 0.05,
    "SILENCE":       0.02,
    "REST_REQUEST":  0.01,
}


def compute_efe(
    action: str,
    current_state: dict,
    prediction_error: float,
    drives: dict,
    preferred_state: dict = None,
) -> float:
    """
    Retorna EFE para uma ação. Menor = mais preferível.

    action:           nome da ação (SPEAK, SILENCE, etc.)
    current_state:    estado corporal atual {tensao, calor, vibracao, fluidez, pulso, luminosidade}
    prediction_error: erro de predição atual (0.0–1.0)
    drives:           drives Panksepp {nome: level}
    preferred_state:  estado preferido (usa _PREFERRED_STATE se None)
    """
    preferred = preferred_state or _PREFERRED_STATE
    deltas = _ACTION_STATE_DELTAS.get(action, {})

    # Estado esperado após a ação
    expected = {
        k: max(0.0, min(1.0, current_state.get(k, 0.5) + deltas.get(k, 0.0)))
        for k in preferred
    }

    # Termo pragmático: distância euclidiana ao estado preferido
    pragmatic = sum((expected[k] - preferred[k]) ** 2 for k in preferred) ** 0.5

    # Termo epistêmico: ações que aumentam fluidez reduzem incerteza
    epistemic_gain = _EPISTEMIC_GAIN.get(action, 0.05)

    # Modular por erro de predição: se surpresa alta, epistêmico ganha mais peso
    epistemic = -epistemic_gain * (1.0 + prediction_error * 3.0)

    # Modificador por drives
    fear    = drives.get("FEAR", 0.0)
    care    = drives.get("CARE", 0.0)
    seeking = drives.get("SEEKING", 0.0)
    rage    = drives.get("RAGE", 0.0)

    drive_modifier = 0.0
    if action == "SPEAK":
        drive_modifier += fear * 0.10       # medo aumenta custo de falar
        drive_modifier -= care * 0.08       # cuidado reduz custo
        drive_modifier -= seeking * 0.06    # curiosidade quer falar
    elif action == "SILENCE":
        drive_modifier -= fear * 0.05       # medo torna silêncio mais atraente
        drive_modifier += care * 0.10       # cuidado torna silêncio custoso
    elif action == "SELF_REGULATE":
        drive_modifier -= rage * 0.10       # raiva alta → auto-regular atrativo

    return pragmatic + epistemic + drive_modifier


def select_action_by_efe(
    available_actions: list,
    current_state: dict,
    prediction_error: float,
    drives: dict,
) -> tuple:
    """
    Seleciona ação com menor EFE entre as disponíveis.
    Retorna (ação_selecionada, scores_por_ação).

    Ações que começam com 'ACT:' são ignoradas (ações instrumentais).
    """
    scores = {}
    for action in available_actions:
        if action.startswith("ACT:"):
            continue
        scores[action] = compute_efe(action, current_state, prediction_error, drives)

    if not scores:
        return "SPEAK", {}

    best = min(scores, key=scores.get)
    return best, scores
