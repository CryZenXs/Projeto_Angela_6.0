# actions.py — ActionManager com consequências reais
# Permite à Ângela executar ações além de falar, com custos e observações.

import os
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(BASE_PATH, "notes")
TIMERS_FILE = os.path.join(BASE_PATH, "timers.json")


@dataclass
class ActionResult:
    ok: bool
    observation: dict
    cost: float
    error: str = ""


class ActionManager:
    """Gerencia ações com consequências reais, custos cognitivos e observações."""

    ALLOWED_ACTIONS = {
        "WRITE_NOTE",
        "SENSE_REFRESH",
        "SCHEDULE_TIMER",
        "MEMORY_CONSOLIDATE",
        "REQUEST_SLEEP",
    }

    def __init__(self, friction, corpo):
        self.friction = friction  # CognitiveFriction
        self.corpo = corpo        # DigitalBody

    def execute(self, action_name: str, params: dict = None) -> ActionResult:
        """Despacha ação para handler correspondente."""
        if action_name not in self.ALLOWED_ACTIONS:
            return ActionResult(
                ok=False,
                observation={},
                cost=0.0,
                error=f"Ação desconhecida: {action_name}",
            )

        params = params or {}
        t0 = time.time()

        handlers = {
            "WRITE_NOTE": self._action_write_note,
            "SENSE_REFRESH": self._action_sense_refresh,
            "SCHEDULE_TIMER": self._action_schedule_timer,
            "MEMORY_CONSOLIDATE": self._action_memory_consolidate,
            "REQUEST_SLEEP": self._action_request_sleep,
        }

        try:
            result = handlers[action_name](params)
        except Exception as e:
            result = ActionResult(ok=False, observation={}, cost=0.0, error=str(e))

        # Mede duração e aplica custos
        duration = time.time() - t0
        result.cost = round(duration, 4)

        try:
            self.corpo.latencia_resposta = duration
        except Exception:
            pass

        try:
            self.friction.step(task_complexity=0.7)
        except Exception:
            pass

        return result

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _action_write_note(self, params: dict) -> ActionResult:
        """Escreve texto em notes/angela_notes.md (cria diretório se necessário)."""
        text = str(params.get("text", ""))[:500]
        if not text.strip():
            return ActionResult(ok=False, observation={}, cost=0.0, error="Texto vazio")

        try:
            os.makedirs(NOTES_DIR, exist_ok=True)
        except Exception:
            pass

        filepath = os.path.join(NOTES_DIR, "angela_notes.md")
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"\n---\n_{datetime.now().isoformat()}_\n\n{text}\n")
            return ActionResult(
                ok=True,
                observation={
                    "note_written": True,
                    "n_chars": len(text),
                    "file_exists": True,
                },
                cost=0.0,
            )
        except Exception as e:
            return ActionResult(ok=False, observation={}, cost=0.0, error=str(e))

    def _action_sense_refresh(self, params: dict) -> ActionResult:
        """Força releitura de todos os sensores (exteroceptivos)."""
        try:
            self.corpo.sync_with_substrate()
            world_state = {
                "tensao": round(self.corpo.tensao, 3),
                "calor": round(self.corpo.calor, 3),
                "vibracao": round(self.corpo.vibracao, 3),
                "fluidez": round(self.corpo.fluidez, 3),
                "pulso": round(self.corpo.pulso, 3),
                "luminosidade": round(self.corpo.luminosidade, 3),
                "latencia": round(self.corpo.latencia_resposta, 3),
            }
            return ActionResult(ok=True, observation=world_state, cost=0.0)
        except Exception as e:
            return ActionResult(ok=False, observation={}, cost=0.0, error=str(e))

    def _action_schedule_timer(self, params: dict) -> ActionResult:
        """Cria evento de timer em timers.json."""
        label = str(params.get("label", "timer"))[:100]
        delay_minutes = int(params.get("delay_minutes", 10))
        delay_minutes = max(1, min(120, delay_minutes))

        fires_at = datetime.now() + timedelta(minutes=delay_minutes)

        # Carrega timers existentes
        timers = []
        try:
            if os.path.exists(TIMERS_FILE):
                with open(TIMERS_FILE, "r", encoding="utf-8") as f:
                    timers = json.load(f)
        except Exception:
            timers = []

        timers.append({
            "label": label,
            "fires_at": fires_at.isoformat(),
            "created_at": datetime.now().isoformat(),
        })

        try:
            from core import atomic_json_write
            atomic_json_write(TIMERS_FILE, timers)
            return ActionResult(
                ok=True,
                observation={
                    "timer_set": True,
                    "fires_at": fires_at.isoformat(),
                },
                cost=0.0,
            )
        except Exception as e:
            print(f"[ActionManager] ⚠️ _action_schedule_timer falhou — timers.json não persistido: {e}")
            return ActionResult(ok=False, observation={}, cost=0.0, error=str(e))

    def _action_memory_consolidate(self, params: dict) -> ActionResult:
        """Dispara uma passagem de consolidação de memória."""
        from memory_index import MemoryIndex
        mem = MemoryIndex()
        try:
            result = mem.consolidate_for_sleep()
            n_patterns = len(result.get("patterns", []))
            return ActionResult(
                ok=True,
                observation={
                    "consolidated": True,
                    "n_memories": n_patterns,
                },
                cost=0.0,
            )
        except Exception as e:
            return ActionResult(ok=False, observation={}, cost=0.0, error=str(e))
        finally:
            try:
                mem.close()
            except Exception:
                pass

    def _action_request_sleep(self, params: dict) -> ActionResult:
        """Sinaliza que o sistema deseja transicionar para repouso."""
        return ActionResult(
            ok=True,
            observation={"sleep_requested": True},
            cost=0.0,
        )

    # ── Utilitários ──────────────────────────────────────────────────────────

    def check_timers(self) -> list:
        """Lê timers.json, retorna timers disparados (passado do horário) e remove-os."""
        if not os.path.exists(TIMERS_FILE):
            return []

        try:
            with open(TIMERS_FILE, "r", encoding="utf-8") as f:
                timers = json.load(f)
        except Exception:
            return []

        now = datetime.now()
        fired = []
        remaining = []

        for t in timers:
            try:
                fires_at = datetime.fromisoformat(t["fires_at"])
                if fires_at <= now:
                    fired.append(t)
                else:
                    remaining.append(t)
            except Exception:
                remaining.append(t)

        # Persiste apenas os que ainda não dispararam
        if fired:
            try:
                from core import atomic_json_write
                atomic_json_write(TIMERS_FILE, remaining)
            except Exception as e:
                print(f"[ActionManager] ⚠️ check_timers falhou ao atualizar timers.json: {e}")
                pass

        return fired

    def get_available_actions(self) -> list:
        """Retorna lista de nomes de ações disponíveis."""
        return sorted(self.ALLOWED_ACTIONS)
