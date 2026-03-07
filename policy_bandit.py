"""
policy_bandit.py — Contextual Bandit para seleção de ações

Bandit contextual leve que aprende quais ações funcionam melhor
em diferentes estados, persistido em arquivo JSON.
"""

import os
import json
import random
from collections import deque

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


class PolicyBandit:
    """Epsilon-greedy contextual bandit com persistência em JSON."""

    def __init__(self, epsilon: float = 0.15,
                 state_file: str = "policy_state.json"):
        self.epsilon = epsilon
        self.state_file = os.path.join(BASE_PATH, state_file)
        self.q_table: dict = {}
        self.recent_actions: deque = deque(maxlen=10)
        self.total_updates: int = 0
        self.load_state()

    # ── contexto ────────────────────────────────────────────────

    def discretize_context(self, corpo_state: dict, damage: float,
                           pred_error: float,
                           ciclo: str = "vigilia",
                           drives: dict = None) -> str:
        tensao = corpo_state.get("tensao", 0.0)
        fluidez = corpo_state.get("fluidez", 0.0)

        parts = [
            "tensao_high" if tensao > 0.6 else "tensao_ok",
            "fluidez_low" if fluidez < 0.4 else "fluidez_ok",
            "damage_high" if damage > 0.3 else "damage_ok",
            "pred_err_high" if pred_error > 0.4 else "pred_err_ok",
            ciclo,
        ]

        if drives:
            # Aceita tanto {nome: float} (get_all_levels) quanto {nome: {"level": float}}
            dominant = max(
                drives.items(),
                key=lambda kv: kv[1].get("level", 0.0)
                               if isinstance(kv[1], dict) else float(kv[1]),
            )
            dom_name = dominant[0]
            dom_level = (dominant[1].get("level", 0.0)
                         if isinstance(dominant[1], dict) else float(dominant[1]))
            # Só adiciona se o drive dominante tiver ativação relevante (> 0.3)
            if dom_level > 0.3:
                parts.append(f"dom_{dom_name}")

        return "|".join(parts)

    # ── seleção ─────────────────────────────────────────────────

    def select_action(self, context: str,
                      available_actions: list) -> str:
        if context not in self.q_table or random.random() < self.epsilon:
            action = random.choice(available_actions)
        else:
            ctx_data = self.q_table[context]
            known = {a: ctx_data[a]["mean"]
                     for a in available_actions if a in ctx_data}
            if not known:
                action = random.choice(available_actions)
            else:
                action = max(known, key=known.get)

        self.recent_actions.append(action)
        return action

    # ── atualização ─────────────────────────────────────────────

    def update(self, context: str, action: str, reward: float):
        if context not in self.q_table:
            self.q_table[context] = {}
        if action not in self.q_table[context]:
            self.q_table[context][action] = {
                "total_reward": 0.0, "count": 0, "mean": 0.0,
            }

        entry = self.q_table[context][action]
        entry["count"] += 1
        entry["total_reward"] += reward
        entry["mean"] = entry["total_reward"] / entry["count"]

        self.total_updates += 1
        self.adjust_epsilon()
        self.save_state()

    # ── novidade ────────────────────────────────────────────────

    def is_novel_action(self, action: str) -> bool:
        last5 = list(self.recent_actions)[-5:]
        return action not in last5

    # ── resumo ──────────────────────────────────────────────────

    def get_policy_summary(self) -> dict:
        top_actions = {}
        for ctx, actions in self.q_table.items():
            if actions:
                best = max(actions, key=lambda a: actions[a]["mean"])
                top_actions[ctx] = {
                    "action": best,
                    "mean_reward": actions[best]["mean"],
                }

        return {
            "n_contexts": len(self.q_table),
            "n_updates": self.total_updates,
            "top_actions": top_actions,
            "epsilon": round(self.epsilon, 4),
        }

    # ── epsilon decay ───────────────────────────────────────────

    def adjust_epsilon(self, min_epsilon: float = 0.05,
                       decay: float = 0.995):
        self.epsilon = max(min_epsilon, self.epsilon * decay)

    # ── persistência ────────────────────────────────────────────

    def save_state(self):
        from core import atomic_json_write
        try:
            data = {
                "epsilon": self.epsilon,
                "q_table": self.q_table,
                "recent_actions": list(self.recent_actions),
                "total_updates": self.total_updates,
            }
            atomic_json_write(self.state_file, data)
        except Exception as e:
            print(f"[PolicyBandit] ⚠️ save_state falhou — política não persistida: {e}")

    def load_state(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.epsilon = data.get("epsilon", self.epsilon)
            # Fix: garante que epsilon carregado nunca fique abaixo do floor
            self.epsilon = max(self.epsilon, 0.05)
            self.q_table = data.get("q_table", {})
            self.recent_actions = deque(
                data.get("recent_actions", []), maxlen=10,
            )
            self.total_updates = data.get("total_updates", 0)
        except FileNotFoundError:
            pass  # primeiro uso — estado vazio é normal
        except Exception as e:
            print(f"[PolicyBandit] ⚠️ load_state falhou — iniciando com estado vazio: {e}")
