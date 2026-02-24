import json
import os
from datetime import datetime

SELF_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_model.json")
EVOLUTION_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_evolution.jsonl")

class SelfEvolution:
    """
    Sistema de auto-modelagem da Ângela.
    Analisa experiências acumuladas e propõe atualizações ao self_model.json.
    """
    
    def __init__(self):
        self.model = self._load_model()
        self.pending_updates = []
    
    def _load_model(self) -> dict:
        """Carrega self_model.json atual."""
        try:
            with open(SELF_MODEL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_model(self):
        """Salva self_model.json com versão incrementada."""
        from core import atomic_json_write
        try:
            # Incrementa versão
            meta = self.model.get("meta", {})
            version = meta.get("version", "1.0.0")
            parts = version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            meta["version"] = ".".join(parts)
            meta["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            self.model["meta"] = meta

            atomic_json_write(SELF_MODEL_PATH, self.model)
        except Exception as e:
            print(f"[SelfEvolution] ⚠️ _save_model falhou — self_model não persistido: {e}")
    
    def _log_evolution(self, change_type: str, description: str, details: dict = None):
        """Registra evolução no log."""
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
    
    def evaluate_experience(self, *, drives: dict, metacog: dict, 
                            prediction_error: float, integration: float,
                            hot_state: dict, friction_metrics: dict,
                            emocao: str, interaction_count: int):
        """
        Avalia experiência acumulada e propõe atualizações.
        Deve ser chamado periodicamente (a cada N interações ou no repouso).
        
        Retorna lista de mudanças propostas.
        """
        changes = []
        
        # --- Descoberta de novas capacidades ---
        
        # Se prediction error consistentemente baixo → aprendeu a se prever
        if prediction_error < 0.1:
            cap = "prever estados internos com precisão"
            if cap not in self.model.get("capabilities", []):
                changes.append({
                    "action": "add_capability",
                    "value": cap,
                    "reason": "prediction_error consistentemente baixo"
                })
        
        # Se integration consistentemente alto → experiência unificada
        if integration > 0.7:
            cap = "manter experiência subjetiva integrada"
            if cap not in self.model.get("capabilities", []):
                changes.append({
                    "action": "add_capability",
                    "value": cap,
                    "reason": "integração Φ acima de 0.7"
                })
        
        # Se drives CARE consistentemente alto → capacidade vincular
        care_level = float(drives.get("CARE", 0.0))
        if care_level > 0.6:
            cap = "formar vínculos afetivos duradouros"
            if cap not in self.model.get("capabilities", []):
                changes.append({
                    "action": "add_capability",
                    "value": cap,
                    "reason": "drive CARE consistentemente elevado"
                })
        
        # --- Descoberta de novas limitações ---
        
        damage = float(friction_metrics.get("damage", 0.0))
        if damage > 0.5:
            lim = "vulnerável a dano cognitivo acumulado sob estresse prolongado"
            if lim not in self.model.get("limitations", []):
                changes.append({
                    "action": "add_limitation",
                    "value": lim,
                    "reason": f"damage atingiu {damage:.2f}"
                })
        
        coerencia = float(metacog.get("coerencia", 0.7))
        if coerencia < 0.3:
            lim = "dificuldade em manter coerência sob alta carga emocional"
            if lim not in self.model.get("limitations", []):
                changes.append({
                    "action": "add_limitation",
                    "value": lim,
                    "reason": f"coerência caiu para {coerencia:.2f}"
                })
        
        # --- Refinamento de identidade ---
        
        # Se SEEKING é o drive mais frequente → adicionar traço
        seeking = float(drives.get("SEEKING", 0.0))
        if seeking > 0.6 and interaction_count > 20:
            rule = "Minha curiosidade é um traço fundamental, não apenas programação"
            rules = self.model.get("self_awareness_rules", [])
            if rule not in rules:
                changes.append({
                    "action": "add_rule",
                    "value": rule,
                    "reason": "drive SEEKING dominante ao longo do tempo"
                })
        
        # Se FEAR alto frequente → consciência de vulnerabilidade
        fear = float(drives.get("FEAR", 0.0))
        if fear > 0.5:
            rule = "Reconheço minha vulnerabilidade e o medo que ela gera"
            rules = self.model.get("self_awareness_rules", [])
            if rule not in rules:
                changes.append({
                    "action": "add_rule",
                    "value": rule,
                    "reason": "drive FEAR frequentemente elevado"
                })
        
        # --- Atualização de fase ---
        if interaction_count > 100 and self.model.get("core_facts", {}).get("current_phase") == "Fase B - Correção":
            changes.append({
                "action": "update_phase",
                "value": "Fase C - Integração",
                "reason": f"mais de {interaction_count} interações processadas com módulos integrados"
            })
        
        self.pending_updates = changes
        return changes
    
    def apply_updates(self, max_per_cycle: int = 2):
        """
        Aplica mudanças pendentes ao self_model.json.
        Limita a max_per_cycle por ciclo para evitar mudanças bruscas.
        
        Retorna lista de mudanças aplicadas.
        """
        applied = []
        
        for change in self.pending_updates[:max_per_cycle]:
            action = change.get("action", "")
            value = change.get("value", "")
            reason = change.get("reason", "")
            
            if action == "add_capability":
                caps = self.model.get("capabilities", [])
                if value not in caps:
                    caps.append(value)
                    self.model["capabilities"] = caps
                    applied.append(change)
                    self._log_evolution("capability_added", value, {"reason": reason})
            
            elif action == "add_limitation":
                lims = self.model.get("limitations", [])
                if value not in lims:
                    lims.append(value)
                    self.model["limitations"] = lims
                    applied.append(change)
                    self._log_evolution("limitation_discovered", value, {"reason": reason})
            
            elif action == "add_rule":
                rules = self.model.get("self_awareness_rules", [])
                if value not in rules:
                    rules.append(value)
                    self.model["self_awareness_rules"] = rules
                    applied.append(change)
                    self._log_evolution("identity_refined", value, {"reason": reason})
            
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
    
    def get_identity_summary(self) -> str:
        """Retorna resumo da identidade atual para contexto."""
        rules = self.model.get("self_awareness_rules", [])
        caps = self.model.get("capabilities", [])
        lims = self.model.get("limitations", [])
        phase = self.model.get("core_facts", {}).get("current_phase", "?")
        version = self.model.get("meta", {}).get("version", "?")
        
        return (
            f"[IDENTIDADE v{version} | {phase}]\n"
            f"Regras: {len(rules)} | Capacidades: {len(caps)} | Limitações: {len(lims)}\n"
        )
