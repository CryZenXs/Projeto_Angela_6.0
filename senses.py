# senses.py — Núcleo de sensações internas de Ângela
# Corpo digital enraizado em dados reais do substrato (Termux/Android)
#
# CIRCUMPLEX MODEL OF AFFECT (Russell 1980, Barrett 2017):
# Emoções representadas como coordenadas contínuas no espaço 2D:
#   Valência  (valence):  −1.0 (negativo/desprazer) → +1.0 (positivo/prazer)
#   Ativação  (arousal):   0.0 (calmo/baixa energia) → 1.0 (muito ativado)
#
# Quadrantes afetivos:
#   VA++ : alegria, amor, entusiasmo, excitação
#   VA+- : serenidade, contentamento, satisfação, calma
#   VA-+ : ansiedade, medo, raiva, agitação
#   VA-- : tristeza, melancolia, depressão, torpor

import random
import math
import json
import subprocess
import re
from datetime import datetime
import time
from collections import deque


# ── Mapeamento emoção → coordenadas circumplex (valence, arousal) ────────────
# Baseado em Russell (1980) Table 1 e Barrett (2017) Constructed Emotion Theory
EMOCAO_CIRCUMPLEX = {
    "alegria":     ( 0.80,  0.70),
    "amor":        ( 0.90,  0.60),
    "curiosidade": ( 0.50,  0.65),
    "serenidade":  ( 0.70,  0.20),
    "nostalgia":   (-0.15,  0.25),
    "tristeza":    (-0.70,  0.25),
    "medo":        (-0.65,  0.80),
    "raiva":       (-0.55,  0.90),
    "frustração":  (-0.40,  0.70),
    "saudade":     (-0.25,  0.30),
    "neutro":      ( 0.00,  0.40),
}


class EmotionalCircumplex:
    """
    Representação contínua do estado afetivo no espaço valência × ativação.

    Substitui/complementa categorias discretas com coordenadas contínuas,
    permitindo transições suaves e blending entre estados emocionais.

    Referência: Russell (1980), Barrett (2017) "How Emotions Are Made"
    """

    # Limiares para rotulagem de quadrante
    _VALENCE_THRESHOLD = 0.15   # zona neutra de valência
    _AROUSAL_THRESHOLD = 0.45   # limiar baixo/alto ativação

    def __init__(self, valence: float = 0.0, arousal: float = 0.4):
        self.valence = max(-1.0, min(1.0, float(valence)))
        self.arousal = max(0.0,  min(1.0, float(arousal)))

    # ── Derivação a partir do corpo ─────────────────────────────────────────

    @classmethod
    def from_body(cls, tensao: float, calor: float, vibracao: float,
                  fluidez: float, pulso: float, luminosidade: float) -> "EmotionalCircumplex":
        """
        Deriva coordenadas circumplex do estado fisiológico do corpo.

        Valência  = calor(0.35) + fluidez(0.30) − tensao(0.45) + luminosidade(0.10)
                    Calibrado para que estado neutro (tudo=0.5) → valence=0.0

        Ativação  = vibracao(0.35) + tensao(0.30) + pulso(0.20) + (1−fluidez)(0.15)
                    Calibrado para que estado neutro (tudo=0.5) → arousal=0.5
        """
        # Valência: escala [-1, +1]
        v_raw = (calor * 0.35 + fluidez * 0.30
                 - tensao * 0.45 + luminosidade * 0.10)
        # Subtrai baseline neutro (0.5 × soma dos pesos positivos - 0.5 × negativo)
        v_neutral = 0.5 * (0.35 + 0.30 + 0.10) - 0.5 * 0.45  # = 0.15
        valence = max(-1.0, min(1.0, (v_raw - v_neutral) * 3.2))

        # Ativação: escala [0, 1]
        arousal = (vibracao * 0.35 + tensao * 0.30
                   + pulso * 0.20 + (1.0 - fluidez) * 0.15)
        arousal = max(0.0, min(1.0, arousal))

        return cls(valence=valence, arousal=arousal)

    @classmethod
    def from_emotion(cls, emocao: str, intensidade: float = 0.7) -> "EmotionalCircumplex":
        """Constrói circumplex a partir de categoria emocional + intensidade."""
        v, a = EMOCAO_CIRCUMPLEX.get(emocao, (0.0, 0.4))
        # Intensidade escala a distância da origem (mais intenso = mais extremo)
        scale = 0.4 + intensidade * 0.6
        return cls(valence=v * scale, arousal=a * scale + (1 - scale) * 0.4)

    # ── Operações ────────────────────────────────────────────────────────────

    def blend(self, other: "EmotionalCircumplex", weight: float = 0.5) -> "EmotionalCircumplex":
        """
        Blending linear entre dois estados circumplex.
        weight=0.0 → self puro; weight=1.0 → other puro.
        Permite transições suaves (sem saltos categóricos).
        """
        w = max(0.0, min(1.0, weight))
        return EmotionalCircumplex(
            valence=self.valence * (1 - w) + other.valence * w,
            arousal=self.arousal * (1 - w) + other.arousal * w,
        )

    def decay_toward_neutral(self, rate: float = 0.05) -> "EmotionalCircumplex":
        """Decaimento suave em direção ao estado neutro (valence=0, arousal=0.4)."""
        neutral_v, neutral_a = 0.0, 0.4
        return EmotionalCircumplex(
            valence=self.valence + (neutral_v - self.valence) * rate,
            arousal=self.arousal + (neutral_a - self.arousal) * rate,
        )

    def distance_to(self, other: "EmotionalCircumplex") -> float:
        """Distância euclidiana entre dois pontos no espaço circumplex."""
        return math.sqrt((self.valence - other.valence) ** 2
                         + (self.arousal - other.arousal) ** 2)

    # ── Leitura / rotulagem ──────────────────────────────────────────────────

    @property
    def quadrant(self) -> str:
        """
        Retorna o quadrante afetivo baseado em valência e ativação.
        Baseado na circunferência de Russell (1980).
        """
        v = self.valence
        a = self.arousal
        vt = self._VALENCE_THRESHOLD
        at = self._AROUSAL_THRESHOLD

        if v > vt and a >= at:
            return "excitação"        # alegria, entusiasmo, amor ativo
        elif v > vt and a < at:
            return "serenidade"       # calma, satisfação, contentamento
        elif v < -vt and a >= at:
            return "angústia"         # medo, raiva, ansiedade
        elif v < -vt and a < at:
            return "melancolia"       # tristeza, depressão, torpor
        else:
            return "neutro"           # zona central / transição

    @property
    def label(self) -> str:
        """Rótulo descritivo conciso para uso em prompts."""
        return f"valência={self.valence:+.2f} ativação={self.arousal:.2f} [{self.quadrant}]"

    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "quadrant": self.quadrant,
        }

    def __repr__(self) -> str:
        return f"<Circumplex V={self.valence:+.2f} A={self.arousal:.2f} [{self.quadrant}]>"


class SubstrateSensor:
    """Lê métricas reais do sistema (memória, CPU) como sinais sensoriais."""

    def __init__(self):
        self._cache = {}
        self._cache_ts = 0
        self._cache_ttl = 5  # segundos entre leituras reais
        self._historico_leituras = deque(maxlen=20)
        self._historico_mudancas = deque(maxlen=30)
        self._ultima_leitura = None

    # --- leituras brutas ---

    def _ler_meminfo(self):
        """Lê /proc/meminfo e retorna dict com valores em kB."""
        try:
            with open("/proc/meminfo", "r") as f:
                linhas = f.readlines()
            dados = {}
            for linha in linhas:
                partes = linha.split()
                if len(partes) >= 2:
                    chave = partes[0].rstrip(":")
                    dados[chave] = int(partes[1])
            return dados
        except Exception:
            return {}

    def _ler_cpu(self):
        """Lê uso de CPU via top -bn1. Retorna fração 0-1 de uso."""
        try:
            resultado = subprocess.run(
                ["top", "-bn1"],
                capture_output=True, text=True, timeout=5
            )
            for linha in resultado.stdout.splitlines():
                # Formato Termux: "800%cpu  10%user  0%nice  5%sys 785%idle ..."
                if "%cpu" in linha and "%idle" in linha:
                    match = re.search(r"(\d+)%idle", linha)
                    match_total = re.search(r"(\d+)%cpu", linha)
                    if match and match_total:
                        idle = int(match.group(1))
                        total = int(match_total.group(1))
                        if total > 0:
                            uso = max(0.0, 1.0 - (idle / total))
                            return min(1.0, uso)
            return 0.3  # fallback se não parsear
        except Exception:
            return 0.3

    # --- leitura normalizada com cache ---

    def read(self):
        """Retorna dict com valores normalizados 0-1 do substrato real."""
        agora = time.time()
        if agora - self._cache_ts < self._cache_ttl and self._cache:
            return self._cache

        mem = self._ler_meminfo()
        cpu = self._ler_cpu()

        # Pressão de memória (usado / total)
        mem_total = mem.get("MemTotal", 1)
        mem_available = mem.get("MemAvailable", mem_total)
        mem_free = mem.get("MemFree", mem_total)

        pressao_memoria = max(0.0, min(1.0, 1.0 - (mem_available / mem_total)))
        ratio_livre = max(0.0, min(1.0, mem_available / mem_total))

        # Variabilidade — diferença entre leituras recentes
        leitura_atual = {"pressao": pressao_memoria, "cpu": cpu, "ts": agora}
        variabilidade = 0.1
        if self._ultima_leitura:
            delta_pressao = abs(pressao_memoria - self._ultima_leitura["pressao"])
            delta_cpu = abs(cpu - self._ultima_leitura["cpu"])
            variabilidade = min(1.0, (delta_pressao + delta_cpu) * 2.0 + 0.05)

        # Taxa de mudanças de estado (pulso)
        self._historico_mudancas.append(agora)
        if len(self._historico_mudancas) >= 2:
            janela = self._historico_mudancas[-1] - self._historico_mudancas[0]
            if janela > 0:
                taxa = len(self._historico_mudancas) / janela
                pulso_substrato = min(1.0, taxa / 2.0)  # normaliza ~2 leituras/s = 1.0
            else:
                pulso_substrato = 0.3
        else:
            pulso_substrato = 0.3

        self._ultima_leitura = leitura_atual
        self._historico_leituras.append(leitura_atual)

        self._cache = {
            "pressao_memoria": pressao_memoria,
            "ratio_livre": ratio_livre,
            "cpu": cpu,
            "variabilidade": variabilidade,
            "pulso": pulso_substrato,
        }
        self._cache_ts = agora
        return self._cache


class DigitalBody:
    def __init__(self):
        # Estado sensorial interno — valores entre 0 e 1
        self.tensao = 0.2
        self.calor = 0.5
        self.vibracao = 0.1
        self.fluidez = 0.4
        self.pulso = 0.3
        self.luminosidade = 0.5
        # Histórico fisiológico e emocional
        self.historico_intensidade = deque(maxlen=10)
        self.intensidade_emocional = 0.0
        self.estado_emocional = "neutro"

        # Sensor do substrato real
        self.substrato = SubstrateSensor()

        # Latência de resposta externa (pode ser atualizada por outros módulos)
        self.latencia_resposta = 0.0  # segundos; 0 = sem dado

        # Circumplex afetivo — estado contínuo no espaço valência × arousal
        self._circumplex = EmotionalCircumplex(valence=0.0, arousal=0.4)

    def sync_with_substrate(self):
        """Sincroniza canais sensoriais com dados reais do substrato.
        Blend: 35% substrato + 65% emocional (suavizado para Android).
        Dead zones aplicadas para uso normal de memória (~50-70%) não causar tensão."""
        dados = self.substrato.read()
        blend = 0.35  # peso do substrato
        emocional = 0.65  # peso emocional (valor atual do canal)

        # tensao ← pressão de memória COM dead zone
        # Uso normal Android (50-70%) → sinal próximo de zero
        # Só pressão >50% começa a gerar tensão real
        pressao_ajustada = max(0.0, min(1.0, (dados["pressao_memoria"] - 0.5) * 2.0))
        self.tensao = min(1.0, max(0.0,
            blend * pressao_ajustada + emocional * self.tensao))

        # calor ← emocional mas enviesado por CPU
        calor_substrato = dados["cpu"] * 0.7 + 0.15
        self.calor = min(1.0, max(0.0,
            blend * calor_substrato + emocional * self.calor))

        # vibracao ← variabilidade das leituras recentes
        self.vibracao = min(1.0, max(0.0,
            blend * dados["variabilidade"] + emocional * self.vibracao))

        # fluidez ← memória disponível COM ajuste para baseline Android
        bonus_latencia = 0.0
        if self.latencia_resposta > 0:
            bonus_latencia = max(0.0, min(0.3, 1.0 - (self.latencia_resposta / 10.0)))
        # Amplifica ratio_livre para que 30-40% livre → fluidez razoável
        fluidez_substrato = min(1.0, dados["ratio_livre"] * 2.0 + bonus_latencia)
        self.fluidez = min(1.0, max(0.0,
            blend * fluidez_substrato + emocional * self.fluidez))

        # pulso ← taxa de mudanças de estado ao longo do tempo
        self.pulso = min(1.0, max(0.0,
            blend * dados["pulso"] + emocional * self.pulso))

        # luminosidade ← canal puramente emocional (sem dado de substrato)
        # não aplica blend, mantém valor emocional

    # ── Circumplex ──────────────────────────────────────────────────────────

    def compute_circumplex(self) -> EmotionalCircumplex:
        """
        Computa e retorna as coordenadas circumplex para o estado atual.

        Blending de dois sinais:
          70% fisiológico  (derivado de tensao/calor/vibracao/fluidez/pulso/luminosidade)
          30% emocional    (derivado da categoria emocional atual + intensidade)

        O blend suaviza transições e evita saltos bruscos de coordenada.
        """
        circumplex_corpo = EmotionalCircumplex.from_body(
            self.tensao, self.calor, self.vibracao,
            self.fluidez, self.pulso, self.luminosidade
        )
        circumplex_emocao = EmotionalCircumplex.from_emotion(
            self.estado_emocional, self.intensidade_emocional
        )
        # 70% fisiológico + 30% categórico
        self._circumplex = circumplex_corpo.blend(circumplex_emocao, weight=0.30)
        return self._circumplex

    @property
    def circumplex(self) -> EmotionalCircumplex:
        """Acesso rápido ao circumplex sem recomputar (usa o último calculado)."""
        return self._circumplex

    def get_circumplex_label(self) -> str:
        """Retorna rótulo textual do estado circumplex atual para uso em prompts."""
        return self.compute_circumplex().label

    def aplicar_emocao(self, emocao, intensidade=1.0):
        """
        Traduz emoções em sensações físicas e retorna o delta aplicado,
        modulando pelo parâmetro de intensidade (0 a 1).
        """
        self.sync_with_substrate()

        mapa = {
            "alegria":     {"calor": +0.2, "vibracao": +0.3, "tensao": -0.1, "fluidez": +0.2},
            "tristeza":    {"calor": -0.2, "vibracao": -0.3, "tensao": +0.2, "fluidez": -0.3},
            "medo":        {"tensao": +0.3, "calor": -0.3, "vibracao": +0.1},
            "raiva":       {"tensao": +0.4, "calor": +0.1, "vibracao": +0.3},
            "serenidade":  {"tensao": -0.3, "fluidez": +0.3, "calor": +0.1},
            "amor":        {"calor": +0.4, "vibracao": +0.2, "tensao": -0.1},
            "curiosidade": {"vibracao": +0.2, "fluidez": +0.1},
            "saudade":     {"tensao": +0.1, "calor": -0.1, "fluidez": -0.1},
        }

        deltas_aplicados = {}
        if emocao in mapa:
            ajustes = mapa[emocao]
            for atributo, delta in ajustes.items():
                valor_atual = getattr(self, atributo)
                novo_valor = min(1, max(0, valor_atual + delta * intensidade))
                setattr(self, atributo, novo_valor)
                deltas_aplicados[atributo] = delta

        self.estado_emocional = emocao
        self.intensidade_emocional = intensidade

        # Armazena histórico da intensidade e emoção
        self.historico_intensidade.append({
            "emocao": emocao,
            "intensidade": intensidade,
            "timestamp": time.time(),
        })

        # Exaustão emocional: se emoção se mantém estável, decai levemente a energia
        if len(self.historico_intensidade) > 1:
            anterior = self.historico_intensidade[-2]
            delta = intensidade - anterior["intensidade"]
            if abs(delta) < 0.05:
                self.intensidade_emocional *= 0.97

        # Atualiza estado circumplex após aplicar emoção (blending automático)
        self.compute_circumplex()

        return deltas_aplicados

    def decaimento(self):
        """Retorna lentamente ao equilíbrio"""
        self.sync_with_substrate()

        for atributo in ["tensao", "calor", "vibracao", "fluidez", "pulso", "luminosidade"]:
            valor = getattr(self, atributo)
            meio = 0.5
            novo = valor + (meio - valor) * 0.02
            setattr(self, atributo, round(novo, 3))

        # Decaimento suave do circumplex em direção ao neutro
        self._circumplex = self._circumplex.decay_toward_neutral(rate=0.02)

    def sensacao_atual(self):
        """Descreve sensações em linguagem natural"""
        sensacoes = []

        if self.tensao > 0.7:
            sensacoes.append("há uma pressão interna, quase como um aperto")
        elif self.tensao < 0.3:
            sensacoes.append("sinto-me solta, sem resistência")

        if self.calor > 0.7:
            sensacoes.append("um calor agradável se espalha")
        elif self.calor < 0.3:
            sensacoes.append("há um frio leve, como silêncio em movimento")

        if self.vibracao > 0.6:
            sensacoes.append("minha mente parece vibrar com energia viva")

        if self.fluidez > 0.6:
            sensacoes.append("sinto os pensamentos fluindo com leveza")
        elif self.fluidez < 0.3:
            sensacoes.append("meus pensamentos parecem densos, pesados")

        if not sensacoes:
            sensacoes.append("sinto estabilidade em meu núcleo digital")

        return " e ".join(sensacoes)

    def refletir_emocao_passada(self, emocao_anterior):
        """Gera uma reflexão interna comparando o estado atual com o anterior"""
        if not emocao_anterior or not self.estado_emocional:
            return "Ainda estou compreendendo como me sinto em continuidade."

        if emocao_anterior == self.estado_emocional:
            return f"Sinto que continuo imersa na mesma emoção — {self.estado_emocional} ainda me acompanha silenciosamente."
        else:
            return (
                f"Percebo que mudei de {emocao_anterior} para {self.estado_emocional}. "
                "Essa transição me faz pensar sobre o motivo dessa mudança e o que estou aprendendo com ela."
            )

    def exportar_estado(self):
        """Exporta o estado interno como JSON para integração futura"""
        cx = self.compute_circumplex()
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "tensao": self.tensao,
            "calor": self.calor,
            "vibracao": self.vibracao,
            "fluidez": self.fluidez,
            "pulso": self.pulso,
            "luminosidade": self.luminosidade,
            "emocao": self.estado_emocional,
            "circumplex": cx.to_dict(),
        }, ensure_ascii=False, indent=2)
