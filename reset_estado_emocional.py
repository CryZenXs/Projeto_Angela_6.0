#!/usr/bin/env python3
"""
reset_estado_emocional.py — Reset completo do estado afetivo de Ângela.

O drives_state.json sozinho NÃO é suficiente para resetar porque:
  1. angela_emotions.jsonl — corpo ainda encoda tensão alta da sessão anterior
  2. trauma_memory.json    — TraumaMemory mantém FEAR passivo elevado
  3. angela_state.json     — pode carregar ciclo de vigília com tensão residual
  4. self_evolution_confirmations.json — contadores de padrões negativos acumulados

Este script reseta TODOS os vetores de estado emocional para valores basais calmos,
preservando memórias episódicas (angela_memory.jsonl) e identidade (self_model.json).

Uso:
    python reset_estado_emocional.py
    python reset_estado_emocional.py --hard   # também limpa trauma_memory
"""

import json
import os
import sys
import shutil
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

def p(msg): print(msg)
def ok(label): print(f"  ✅ {label}")
def skip(label): print(f"  ⏭️  {label} (não encontrado, ok)")
def warn(label): print(f"  ⚠️  {label}")

def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

# ── 1. drives_state.json ────────────────────────────────────────────────────
def reset_drives():
    path = os.path.join(BASE, "drives_state.json")
    data = {
        "timestamp": datetime.now().isoformat(),
        "drives": {
            "SEEKING":     {"level": 0.40, "baseline": 0.40},
            "FEAR":        {"level": 0.10, "baseline": 0.10},
            "RAGE":        {"level": 0.05, "baseline": 0.05},
            "CARE":        {"level": 0.30, "baseline": 0.30},
            "PANIC_GRIEF": {"level": 0.10, "baseline": 0.10},
            "PLAY":        {"level": 0.20, "baseline": 0.20},
        }
    }
    atomic_write(path, data)
    ok("drives_state.json → basais")

# ── 2. angela_emotions.jsonl — appenda snapshot de estado calmo ─────────────
def reset_emotions():
    path = os.path.join(BASE, "angela_emotions.jsonl")
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "emocao":      "serenidade",
        "tensao":      0.30,
        "calor":       0.40,
        "vibracao":    0.35,
        "fluidez":     0.60,
        "pulso":       0.45,
        "luminosidade":0.55,
        "contexto":    "reset_manual — estado basal restaurado"
    }
    # Appenda (não sobrescreve) — mantém histórico mas o recall_last_emotion
    # vai ler este como estado atual
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    ok("angela_emotions.jsonl → snapshot de serenidade adicionado (recall vai ler este)")

# ── 3. angela_state.json — ciclo e tensão corporal ──────────────────────────
def reset_angela_state():
    path = os.path.join(BASE, "angela_state.json")
    if not os.path.exists(path):
        skip("angela_state.json")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Reseta campos de tensão sem apagar metadados de sessão
        state["tensao"]      = 0.30
        state["calor"]       = 0.40
        state["fluidez"]     = 0.60
        state["vibracao"]    = 0.35
        state["estado_emocional"] = "serenidade"
        state["reset_ts"]    = datetime.now().isoformat()
        atomic_write(path, state)
        ok("angela_state.json → tensão/fluidez/emoção resetados")
    except Exception as e:
        warn(f"angela_state.json falhou: {e}")

# ── 4. trauma_memory.json ────────────────────────────────────────────────────
def reset_trauma(hard=False):
    path = os.path.join(BASE, "trauma_memory.json")
    if not os.path.exists(path):
        skip("trauma_memory.json")
        return
    if hard:
        # Hard reset: limpa todas as associações de trauma
        backup = path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(path, backup)
        atomic_write(path, {"associations": {}, "reset_ts": datetime.now().isoformat()})
        ok(f"trauma_memory.json → limpo (backup em {os.path.basename(backup)})")
    else:
        # Soft reset: reduz scores de trauma pela metade sem apagar memória
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assoc = data.get("associations", {})
            for key in assoc:
                if isinstance(assoc[key], dict):
                    if "damage" in assoc[key]:
                        assoc[key]["damage"] = round(assoc[key]["damage"] * 0.4, 4)
                    if "intensity" in assoc[key]:
                        assoc[key]["intensity"] = round(assoc[key]["intensity"] * 0.4, 4)
                elif isinstance(assoc[key], (int, float)):
                    assoc[key] = round(float(assoc[key]) * 0.4, 4)
            data["associations"] = assoc
            data["soft_reset_ts"] = datetime.now().isoformat()
            atomic_write(path, data)
            ok(f"trauma_memory.json → scores reduzidos a 40% ({len(assoc)} associações)")
        except Exception as e:
            warn(f"trauma_memory.json falhou: {e}")

# ── 5. self_evolution_confirmations.json — zera contadores negativos ─────────
def reset_evolution_counters():
    path = os.path.join(BASE, "self_evolution_confirmations.json")
    if not os.path.exists(path):
        skip("self_evolution_confirmations.json")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        # Zera só os contadores de padrões negativos, mantém os positivos
        negative_keys = ["rage_loop", "mask_freq", "refl_loop", "val_drift_neg",
                         "seeking_sat", "fear_alto", "damage_alto", "coh_baixa"]
        changed = 0
        for key in negative_keys:
            if key in conf and conf[key] > 0:
                conf[key] = 0
                changed += 1
        atomic_write(path, conf)
        ok(f"self_evolution_confirmations.json → {changed} contadores negativos zerados")
    except Exception as e:
        warn(f"self_evolution_confirmations.json falhou: {e}")

# ── 6. attention_schema_state.json ───────────────────────────────────────────
def reset_attention():
    path = os.path.join(BASE, "attention_schema_state.json")
    if not os.path.exists(path):
        skip("attention_schema_state.json")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Restaura estabilidade de atenção sem apagar foco atual
        state["stability"]    = round(min(1.0, state.get("stability", 0.5) + 0.3), 3)
        state["reliability"]  = round(min(1.0, state.get("reliability", 0.5) + 0.2), 3)
        state["reset_ts"]     = datetime.now().isoformat()
        atomic_write(path, state)
        ok("attention_schema_state.json → estabilidade restaurada")
    except Exception as e:
        warn(f"attention_schema_state.json falhou: {e}")

# ════════════════════════════════════════════════════════════════════════════
def main():
    hard = "--hard" in sys.argv

    p("")
    p("═" * 55)
    p("  RESET DE ESTADO EMOCIONAL — Ângela")
    p(f"  {'MODO HARD (trauma limpo)' if hard else 'MODO SOFT (trauma reduzido)'}")
    p("═" * 55)
    p("")
    p("O que está sendo resetado:")
    p("  → Drives (nível + baseline → valores basais)")
    p("  → Corpo (tensão, calor, fluidez → calmo)")
    p("  → Emoção (último snapshot → serenidade)")
    p("  → Trauma (scores reduzidos" + (" a zero)" if hard else " a 40%)"))
    p("  → Contadores de padrões negativos (self_evolution)")
    p("  → Atenção (estabilidade restaurada)")
    p("")
    p("O que NÃO é tocado:")
    p("  ✓ angela_memory.jsonl (memórias episódicas)")
    p("  ✓ self_model.json (identidade)")
    p("  ✓ angela_autobio.jsonl (autobiografia)")
    p("  ✓ self_evolution.jsonl (log de evoluções)")
    p("")

    reset_drives()
    reset_emotions()
    reset_angela_state()
    reset_trauma(hard=hard)
    reset_evolution_counters()
    reset_attention()

    p("")
    p("─" * 55)
    p("✅ Reset concluído.")
    p("")
    p("Por que os drives sobem rápido mesmo após reset:")
    p("  drives.update() reage ao contexto do prompt a cada turno.")
    p("  Se as memórias carregadas forem de sessão de raiva, os")
    p("  drives sobem em resposta a elas, não ao estado inicial.")
    p("")
    p("  Para um estado mais duradouro, rode deep_awake --mode repouso")
    p("  para que a consolidação noturna processe as memórias de crise")
    p("  antes de retomar o diálogo.")
    p("─" * 55)
    p("")

if __name__ == "__main__":
    main()