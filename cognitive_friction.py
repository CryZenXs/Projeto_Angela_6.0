# cognitive_friction.py
# Atrito cognitivo PASSIVO e OPACO
# Objetivo: introduzir custos irreversíveis e degradação funcional
# sem informar o sistema nem gerar narrativas explícitas sobre degradação.
#
# VERSÃO: 2.0 (Hotfix #4 - Parâmetros balanceados)
# DATA: 07 Fevereiro 2026
# MUDANÇAS: Parâmetros ajustados para crescimento sustentável (13 dias até damage=1.0)

import random
import math
import os
import json
from collections import deque
from datetime import datetime

DAMAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friction_damage.persistent")


def get_persistent_metrics():
    """
    Retorna damage e load do arquivo persistente sem modificar estado.
    Para uso em deep_awake e outros módulos que precisam apenas ler as métricas.
    """
    try:
        if os.path.exists(DAMAGE_FILE):
            with open(DAMAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "damage": float(data.get("damage", 0.0)),
                    "load": float(data.get("load", 0.0)),
                }
    except Exception:
        pass
    return {"damage": 0.0, "load": 0.0}


class CognitiveFriction:
    def __init__(self,
                 seed=None,
                 base_friction=0.002,        # CORRIGIDO: era 0.02 (10x menor)
                 stress_gain=0.08,           # CORRIGIDO: era 0.6 (7.5x menor)
                 recovery_rate=0.008,        # CORRIGIDO: era 0.001 (8x maior)
                 irreversibility=0.08,       # CORRIGIDO: era 0.15 (47% menor)
                 memory_noise=0.03,
                 planning_noise=0.04,
                 language_noise=0.05):
        """
        PARÂMETROS BALANCEADOS (Hotfix #4):
        
        base_friction: atrito mínimo sempre presente (0.002)
        stress_gain: quanto estresse/emocao intensa amplifica o atrito (0.08)
        recovery_rate: recuperação significativa (0.008)
        irreversibility: fração do dano que nunca se recupera (0.08)
        *_noise: ruído funcional aplicado a módulos-alvo
        
        RESULTADOS ESPERADOS:
        - Vigília pura: ~101h até damage=1.0
        - Com ciclos normais: ~13 dias até damage=1.0
        - Após 3h vigília: damage ~0.03 (antes era 1.0)
        - Ratio acumulação/recovery: 4.75:1 (antes era 290:1)
        """
        self.rng = random.Random(seed)
        self.base_friction = base_friction
        self.stress_gain = stress_gain
        self.recovery_rate = recovery_rate
        self.irreversibility = irreversibility
        self.memory_noise = memory_noise
        self.planning_noise = planning_noise
        self.language_noise = language_noise

        # Carrega estado persistente ou inicializa
        self._load_persistent_state()
        
        self.last_ts = datetime.now()

        # Histórico curto para efeitos cumulativos
        self._recent = deque(maxlen=32)

    def _load_persistent_state(self):
        """Carrega damage e load do arquivo persistente"""
        try:
            if os.path.exists(DAMAGE_FILE):
                with open(DAMAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.damage = float(data.get("damage", 0.0))
                    self.load = float(data.get("load", 0.0))
                    self.chronic = bool(data.get("chronic", False))
                    # Incrementa contador de sessões
                    data["total_sessions"] = data.get("total_sessions", 0) + 1
                    data["last_updated"] = datetime.now().isoformat()
                    # Salva incremento (usa atomic write para consistência)
                    from core import atomic_json_write
                    atomic_json_write(DAMAGE_FILE, data)
            else:
                self.damage = 0.0
                self.load = 0.0
                self.chronic = False
        except Exception as e:
            print(f"[CognitiveFriction] ⚠️ _load_persistent_state falhou — damage reiniciado em 0: {e}")
            self.damage = 0.0
            self.load = 0.0
            self.chronic = False

    def _save_persistent_state(self):
        """Salva damage e load no arquivo persistente.

        Bug E fix: em vez de sobrescrever o arquivo com os valores em memória,
        faz read-merge-write — lê o arquivo atual, toma o MAX de damage entre
        o valor em disco e o valor em memória, e só então escreve.
        Isso evita que angela.py e deep_awake.py (processos simultâneos) se
        sobrescrevam mutuamente, o que faria o damage retroceder silenciosamente.
        atomic_json_write garante que a escrita em si não corrompe o arquivo.
        """
        from core import atomic_json_write
        try:
            # Lê estado atual do disco (pode ter sido escrito pelo outro processo)
            disk_damage = 0.0
            disk_load = 0.0
            disk_sessions = 1
            if os.path.exists(DAMAGE_FILE):
                try:
                    with open(DAMAGE_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                        disk_damage = float(existing.get("damage", 0.0))
                        disk_load = float(existing.get("load", 0.0))
                        disk_sessions = existing.get("total_sessions", 1)
                except Exception:
                    pass

            # Merge conservador: toma o máximo de damage (nunca reverte)
            merged_damage = max(self.damage, disk_damage)
            merged_load = max(self.load, disk_load)  # idem para load
            self.damage = merged_damage  # mantém instância sincronizada
            self.load = merged_load

            data = {
                "damage": float(merged_damage),
                "load": float(merged_load),
                "chronic": bool(self.chronic or merged_damage > 0.35),
                "last_updated": datetime.now().isoformat(),
                "total_sessions": disk_sessions,
                "version": "2.0.0"
            }
            atomic_json_write(DAMAGE_FILE, data)
        except Exception as e:
            print(f"[CognitiveFriction] ⚠️ _save_persistent_state falhou — damage não persistido: {e}")

    # --------- Núcleo ---------
    def step(self, *, emotional_intensity=0.0, arousal=0.0, task_complexity=0.5):
        """
        Atualiza o atrito em função do estado atual.
        NÃO retorna sinal explícito de degradação.
        """
        # custo instantâneo
        stress = max(emotional_intensity, arousal)
        instant = self.base_friction + self.stress_gain * stress * task_complexity

        # ruído estocástico suave
        instant *= (0.9 + 0.2 * self.rng.random())

        if self.damage > 0.35:
            self.chronic = True

        # acumula carga
        self.load += instant
        self._recent.append(instant)

        # converte parte em dano irreversível
        if self.load > 0.6:
            delta_damage = (self.load - 0.6) * self.irreversibility
            self.damage = min(1.0, self.damage + delta_damage)
            self.load *= (1.0 - self.irreversibility)

        # recuperação lenta e incompleta
        self.load = max(0.0, self.load - self.recovery_rate)
        
        # Persiste estado após cada step
        self._save_persistent_state()

    # --------- Aplicações Silenciosas ---------
    def perturb_memory(self, vector):
        """
        Aplica ruído sutil à recuperação de memória.
        Espera-se que 'vector' seja uma lista/array numérico.
        """
        if vector is None:
            return None
        noise_level = self.memory_noise * (0.3 + self.damage)
        return [v + self.rng.gauss(0, noise_level) for v in vector]

    def perturb_planning(self, score: float) -> float:
        """
        Reduz levemente scores de planejamento/avaliação.
        """
        n = self.planning_noise * (0.2 + self.damage)
        return max(0.0, score * (1.0 - n))

    def perturb_language(self, temperature: float) -> float:
        """
        Aumenta temperatura efetiva de geração linguística
        sem alterar parâmetros globais visíveis.
        """
        n = self.language_noise * (0.2 + self.damage)
        return min(2.0, temperature * (1.0 + n))

    # --------- Métricas OBSERVÁVEIS (externas) ---------
    def external_metrics(self):
        """
        Métricas apenas para o observador humano.
        NUNCA devem ser expostas à Ângela.
        """
        return {
            "load": round(self.load, 4),
            "damage": round(self.damage, 4),
            "recent_mean": round(sum(self._recent)/len(self._recent), 4) if self._recent else 0.0
        }