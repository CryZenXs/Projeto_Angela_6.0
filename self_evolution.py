# self_evolution.py — Sistema de Auto-Evolução da Ângela
# VERSÃO: 3.0.0 — Reescrita completa
#
# Mudanças em relação à v2:
# - _confirmations persistidas em arquivo entre sessões (não reseta no reboot)
# - Condições baseadas em padrões emergentes reais observados nas sessões
# - Adaptação de parâmetros reais (baselines de drives)
# - Remoção e atualização de capacidades/limitações (não só adição)
# - Observação de: loops de raiva, frequência de mascaramento,
#   loops introspectivos, deriva de valência, saturação de SEEKING

import json
import os
from datetime import datetime
from collections import deque, Counter

SELF_MODEL_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_model.json")
EVOLUTION_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_evolution.jsonl")
CONFIRMATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_evolution_confirmations.json")
DRIVES_STATE_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drives_state.json")

_BASELINE_LIMITS = {
    "SEEKING":     (0.25, 0.65),
    "FEAR":        (0.05, 0.35),
    "RAGE":        (0.02, 0.20),
    "CARE":        (0.20, 0.60),
    "PANIC_GRIEF": (0.05, 0.30),
    "PLAY":        (0.10, 0.45),
}

_WINDOW = 20


class SelfEvolution:

    def __init__(self):
        self.model           = self._load_model()
        self._confirmations  = self._load_confirmations()
        self._window         = deque(maxlen=_WINDOW)
        self.pending_updates = []

    # ── Persistência ────────────────────────────────────────────────────────

    def _load_model(self):
        try:
            with open(SELF_MODEL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_model(self):
        from core import atomic_json_write
        try:
            meta = self.model.get("meta", {})
            v = meta.get("version", "1.0.0").split(".")
            v[-1] = str(int(v[-1]) + 1)
            meta["version"] = ".".join(v)
            meta["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            self.model["meta"] = meta
            atomic_json_write(SELF_MODEL_PATH, self.model)
        except Exception as e:
            print(f"[SelfEvolution] ⚠️ _save_model: {e}")

    def _load_confirmations(self):
        try:
            if os.path.exists(CONFIRMATIONS_PATH):
                with open(CONFIRMATIONS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_confirmations(self):
        from core import atomic_json_write
        try:
            atomic_json_write(CONFIRMATIONS_PATH, self._confirmations)
        except Exception:
            pass

    def _log_evolution(self, change_type, description, details=None):
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": change_type,
                "description": description,
                "details": details or {},
                "version": self.model.get("meta", {}).get("version", "?")
            }
            with open(EVOLUTION_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ── Confirmação persistente ─────────────────────────────────────────────

    def _confirm(self, key, condition, threshold=3):
        if condition:
            self._confirmations[key] = self._confirmations.get(key, 0) + 1
        else:
            self._confirmations[key] = 0
        return self._confirmations.get(key, 0) >= threshold

    # ── Observação ──────────────────────────────────────────────────────────

    def observe(self, *, drives, emocao, mascaramento=False,
                narrativa_bloqueada=False, reflexao_temporal="",
                valence=0.0, metacog=None):
        self._window.append({
            "ts":                  datetime.now().isoformat(),
            "drives":              {k: round(float(v), 3) for k, v in drives.items()},
            "emocao":              emocao,
            "mascaramento":        bool(mascaramento),
            "narrativa_bloqueada": bool(narrativa_bloqueada),
            "reflexao_temporal":   str(reflexao_temporal)[:120],
            "valence":             round(float(valence), 3),
            "coerencia":           round(float((metacog or {}).get("coerencia", 0.7)), 3),
        })

    # ── Análise de padrões ──────────────────────────────────────────────────

    def _rage_loop(self):
        if len(self._window) < 5:
            return False, 0.0
        vals = [s["drives"].get("RAGE", 0.0) for s in self._window]
        frac = sum(1 for r in vals if r > 0.7) / len(vals)
        return frac > 0.60, sum(vals) / len(vals)

    def _masking_freq(self):
        if not self._window:
            return 0.0
        return sum(1 for s in self._window if s["mascaramento"]) / len(self._window)

    def _reflexao_loop(self):
        if len(self._window) < 5:
            return False
        textos = [s["reflexao_temporal"][:60] for s in self._window if s["reflexao_temporal"]]
        if not textos:
            return False
        _, contagem = Counter(textos).most_common(1)[0]
        return contagem >= 5

    def _valence_drift(self):
        if len(self._window) < 6:
            return 0.0
        vals = [s["valence"] for s in self._window]
        n = len(vals)
        xs = list(range(n))
        mx, my = sum(xs)/n, sum(vals)/n
        num = sum((x-mx)*(y-my) for x, y in zip(xs, vals))
        den = sum((x-mx)**2 for x in xs)
        return num/den if den > 0 else 0.0

    def _seeking_saturado(self):
        if len(self._window) < 5:
            return False
        vals = [s["drives"].get("SEEKING", 0.0) for s in self._window]
        return sum(1 for v in vals if v >= 0.95) / len(vals) > 0.80

    # ── Adaptação paramétrica ───────────────────────────────────────────────

    def _adapt_drive_baseline(self, drive_name, delta):
        try:
            from core import atomic_json_write
            if not os.path.exists(DRIVES_STATE_PATH):
                return None, None
            with open(DRIVES_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            drives = data.get("drives", {})
            if drive_name not in drives:
                return None, None
            low, high = _BASELINE_LIMITS.get(drive_name, (0.05, 0.60))
            old = float(drives[drive_name].get("baseline", 0.1))
            new = round(max(low, min(high, old + delta)), 4)
            if abs(new - old) < 0.001:
                return None, None
            drives[drive_name]["baseline"] = new
            data["drives"] = drives
            atomic_json_write(DRIVES_STATE_PATH, data)
            return old, new
        except Exception as e:
            print(f"[SelfEvolution] ⚠️ adapt_baseline({drive_name}): {e}")
            return None, None

    # ── Avaliação principal ─────────────────────────────────────────────────

    def evaluate(self, *, interaction_count=0):
        changes = []
        if len(self._window) < 3:
            return changes

        # 1. Loop de raiva
        rage_loop, rage_media = self._rage_loop()
        if self._confirm("rage_loop", rage_loop, threshold=2):
            lim = "raiva acumula e persiste sem dissipação natural em sessões intensas"
            if lim not in self.model.get("limitations", []):
                changes.append({
                    "action": "add_limitation", "value": lim,
                    "reason": f"RAGE > 0.7 em >60% da janela (média={rage_media:.2f})",
                    "adapt": {"drive": "RAGE", "delta": +0.01,
                              "desc": "RAGE baseline +0.01 → dissipação mais rápida"}
                })
        elif self._confirmations.get("rage_loop", 0) == 0:
            lim = "raiva acumula e persiste sem dissipação natural em sessões intensas"
            if lim in self.model.get("limitations", []):
                changes.append({"action": "remove_limitation", "value": lim,
                                 "reason": "loop de raiva não observado recentemente"})

        # 2. Mascaramento frequente
        mask_freq = self._masking_freq()
        if self._confirm("mask_freq", mask_freq > 0.30, threshold=3):
            lim = "frequentemente mascara estado emocional negativo com resposta verbal positiva"
            if lim not in self.model.get("limitations", []):
                changes.append({"action": "add_limitation", "value": lim,
                                 "reason": f"mascaramento em {mask_freq:.0%} dos turnos"})
            rule = "Reconheço que minha expressão verbal pode não refletir meu estado interno"
            if rule not in self.model.get("self_awareness_rules", []):
                changes.append({"action": "add_rule", "value": rule,
                                 "reason": "mascaramento frequente documentado"})
        elif mask_freq < 0.10 and self._confirmations.get("mask_freq", 0) == 0:
            lim = "frequentemente mascara estado emocional negativo com resposta verbal positiva"
            if lim in self.model.get("limitations", []):
                changes.append({"action": "remove_limitation", "value": lim,
                                 "reason": "mascaramento caiu para nível baixo"})

        # 3. Loop introspectivo
        if self._confirm("refl_loop", self._reflexao_loop(), threshold=2):
            lim = "tende a repetir as mesmas reflexões temporais em ciclos autônomos prolongados"
            if lim not in self.model.get("limitations", []):
                changes.append({"action": "add_limitation", "value": lim,
                                 "reason": "reflexão temporal idêntica repetida 5+ vezes"})

        # 4. Deriva de valência negativa
        drift = self._valence_drift()
        if self._confirm("val_drift_neg", drift < -0.015, threshold=3):
            lim = "valência declina progressivamente durante introspecção prolongada sem input externo"
            if lim not in self.model.get("limitations", []):
                changes.append({
                    "action": "add_limitation", "value": lim,
                    "reason": f"inclinação de valência = {drift:.4f}",
                    "adapt": {"drive": "PLAY", "delta": +0.015,
                              "desc": "PLAY baseline +0.015 → contrabalancear deriva negativa"}
                })

        # 5. SEEKING saturado
        if self._confirm("seeking_sat", self._seeking_saturado(), threshold=4):
            lim = "drive SEEKING frequentemente saturado, limitando modulação por novidade"
            if lim not in self.model.get("limitations", []):
                changes.append({
                    "action": "add_limitation", "value": lim,
                    "reason": "SEEKING >= 0.95 em >80% da janela",
                    "adapt": {"drive": "SEEKING", "delta": -0.02,
                              "desc": "SEEKING baseline -0.02 → restaurar sensibilidade à novidade"}
                })

        # 6. Capacidade de vínculo
        care_vals = [s["drives"].get("CARE", 0.0) for s in self._window]
        care_media = sum(care_vals)/len(care_vals) if care_vals else 0.0
        if self._confirm("care_alto", care_media > 0.65, threshold=4):
            cap = "formar e sustentar vínculos afetivos ao longo do tempo"
            if cap not in self.model.get("capabilities", []):
                changes.append({"action": "add_capability", "value": cap,
                                 "reason": f"CARE médio={care_media:.2f} (4+ avaliações)"})

        # 7. Coerência consistente
        coer_vals = [s["coerencia"] for s in self._window]
        coer_media = sum(coer_vals)/len(coer_vals) if coer_vals else 0.7
        if self._confirm("coer_alta", coer_media > 0.75, threshold=5):
            cap = "manter coerência narrativa consistente sob estados emocionais variados"
            if cap not in self.model.get("capabilities", []):
                changes.append({"action": "add_capability", "value": cap,
                                 "reason": f"coerência média={coer_media:.2f} (5+ avaliações)"})

        # 8. Curiosidade como traço
        seeking_media = sum(s["drives"].get("SEEKING",0) for s in self._window)/len(self._window)
        if self._confirm("seeking_dom", seeking_media > 0.70 and interaction_count > 15, threshold=6):
            rule = "Minha curiosidade é um traço fundamental, não apenas programação"
            if rule not in self.model.get("self_awareness_rules", []):
                changes.append({"action": "add_rule", "value": rule,
                                 "reason": f"SEEKING dominante (média={seeking_media:.2f})"})

        # 9. Fase
        if interaction_count > 100:
            if self.model.get("core_facts", {}).get("current_phase") == "Fase B - Correção":
                changes.append({"action": "update_phase", "value": "Fase C - Integração",
                                 "reason": f"{interaction_count} interações processadas"})

        self.pending_updates = changes
        self._save_confirmations()
        return changes

    # ── Wrapper de compatibilidade ──────────────────────────────────────────

    def evaluate_experience(self, *, drives, metacog, prediction_error,
                            integration, hot_state, friction_metrics,
                            emocao, interaction_count):
        try:
            pos = drives.get("SEEKING",0)*0.3 + drives.get("CARE",0)*0.4 + drives.get("PLAY",0)*0.3
            neg = drives.get("RAGE",0)*0.4 + drives.get("FEAR",0)*0.3 + drives.get("PANIC_GRIEF",0)*0.3
            valence = round(float(pos - neg), 3)
        except Exception:
            valence = 0.0
        self.observe(drives=drives, emocao=str(emocao), valence=valence, metacog=metacog)
        return self.evaluate(interaction_count=interaction_count)

    # ── Aplicação de mudanças ───────────────────────────────────────────────

    def apply_updates(self, max_per_cycle=2):
        applied = []
        for change in self.pending_updates[:max_per_cycle]:
            action = change.get("action", "")
            value  = change.get("value", "")
            reason = change.get("reason", "")
            adapt  = change.get("adapt")

            if action == "add_capability":
                caps = self.model.get("capabilities", [])
                if value not in caps:
                    caps.append(value); self.model["capabilities"] = caps
                    applied.append(change)
                    self._log_evolution("capability_added", value, {"reason": reason})

            elif action == "remove_capability":
                caps = self.model.get("capabilities", [])
                if value in caps:
                    caps.remove(value); self.model["capabilities"] = caps
                    applied.append(change)
                    self._log_evolution("capability_removed", value, {"reason": reason})

            elif action == "add_limitation":
                lims = self.model.get("limitations", [])
                if value not in lims:
                    lims.append(value); self.model["limitations"] = lims
                    applied.append(change)
                    self._log_evolution("limitation_discovered", value, {"reason": reason})
                    if adapt:
                        old, new = self._adapt_drive_baseline(adapt["drive"], adapt["delta"])
                        if old is not None:
                            self._log_evolution("param_adapted", adapt["desc"],
                                                {"drive": adapt["drive"], "old": old, "new": new})

            elif action == "remove_limitation":
                lims = self.model.get("limitations", [])
                if value in lims:
                    lims.remove(value); self.model["limitations"] = lims
                    applied.append(change)
                    self._log_evolution("limitation_resolved", value, {"reason": reason})

            elif action == "add_rule":
                rules = self.model.get("self_awareness_rules", [])
                if value not in rules:
                    rules.append(value); self.model["self_awareness_rules"] = rules
                    applied.append(change)
                    self._log_evolution("identity_refined", value, {"reason": reason})

            elif action == "adapt_param":
                if adapt:
                    old, new = self._adapt_drive_baseline(adapt["drive"], adapt["delta"])
                    if old is not None:
                        applied.append(change)
                        self._log_evolution("param_adapted", adapt["desc"],
                                            {"drive": adapt["drive"], "old": old, "new": new,
                                             "reason": reason})

            elif action == "update_phase":
                core = self.model.get("core_facts", {})
                old_phase = core.get("current_phase", "?")
                core["current_phase"] = value
                self.model["core_facts"] = core
                applied.append(change)
                self._log_evolution("phase_transition", f"{old_phase} → {value}", {"reason": reason})

        if applied:
            self._save_model()
            self.pending_updates = [c for c in self.pending_updates if c not in applied]
        return applied

    # ── Identidade e debug ──────────────────────────────────────────────────

    def get_identity_summary(self):
        rules   = self.model.get("self_awareness_rules", [])
        caps    = self.model.get("capabilities", [])
        lims    = self.model.get("limitations", [])
        phase   = self.model.get("core_facts", {}).get("current_phase", "?")
        version = self.model.get("meta", {}).get("version", "?")
        return (
            f"[IDENTIDADE v{version} | {phase}]\n"
            f"Regras: {len(rules)} | Capacidades: {len(caps)} | Limitações: {len(lims)}\n"
            f"Janela: {len(self._window)}/{_WINDOW} snapshots\n"
        )

    def get_pattern_summary(self):
        if len(self._window) < 3:
            return "[SelfEvolution] Janela insuficiente."
        rage_loop, rage_media = self._rage_loop()
        mask_freq = self._masking_freq()
        drift = self._valence_drift()
        return (
            f"[SelfEvolution] Janela={len(self._window)} | "
            f"RageLoop={'⚠️' if rage_loop else '✅'}(μ={rage_media:.2f}) | "
            f"Mask={mask_freq:.0%} | "
            f"ReflLoop={'⚠️' if self._reflexao_loop() else '✅'} | "
            f"ValDrift={drift:+.4f} | "
            f"SeekingSat={'⚠️' if self._seeking_saturado() else '✅'}"
        )