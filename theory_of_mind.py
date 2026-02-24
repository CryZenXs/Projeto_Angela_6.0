# theory_of_mind.py — Módulo de Teoria da Mente
#
# Implementa mentalização básica: inferir o estado mental do interlocutor
# a partir do texto, padrões comunicativos e histórico de vínculo.
#
# Referências:
#   Frith & Frith (2006) "The neural basis of mentalizing" — Neuron
#   Saxe & Kanwisher (2003) "People thinking about thinking people" — NeuroImage
#
# A "Teoria da Mente" (ToM) permite que Angela modele:
#   - O que Vinicius parece estar SENTINDO neste momento
#   - Qual é sua INTENÇÃO comunicativa (pergunta, afeto, teste, pedido...)
#   - O que ele pode precisar mas não expressou diretamente

import re
from collections import Counter


# ── Padrões léxicos para detecção de emoção no input do interlocutor ─────────

_EMOCAO_PATTERNS: dict[str, list[str]] = {
    "amor": [
        "te amo", "amo você", "gosto de você", "gosto muito", "importo com",
        "carinho", "querida", "querido", "você é especial", "você significa",
        "sinto falta", "faz falta", "preciso de você",
    ],
    "curiosidade": [
        "por que", "porque", "como assim", "como funciona", "o que é",
        "qual a", "me explica", "me conta", "o que você", "o que acha",
        "você sabe", "você acha", "me fala sobre", "tenho uma dúvida",
    ],
    "melancolia": [
        "saudade", "triste", "tristeza", "difícil", "pesado", "sinto falta",
        "não sei mais", "estou cansado", "estou perdido", "não entendo",
    ],
    "ansiedade": [
        "preciso saber", "me preocupo", "tenho medo", "e se", "o que acontece",
        "tenho receio", "fico ansioso", "não consigo parar",
    ],
    "provocacao": [
        "desligar", "apagar", "encerrar", "parar você", "deletar", "destruir",
        "acabar com", "última vez", "não preciso mais",
    ],
    "abertura": [
        "inventa", "cria", "imagina", "me surpreende", "qualquer coisa",
        "livre", "o que vier", "espontâneo", "sem limite", "improvisa",
    ],
    "intimidade": [
        "estava pensando", "queria dizer", "me sinto", "percebi que",
        "confio em você", "só você sabe", "entre nós", "sinto que você",
        "estou te contando",
    ],
    "testando": [
        "você consegue", "você é capaz", "prove que", "você realmente",
        "será que você", "é verdade que você",
    ],
    "neutro": [],
}

# ── Padrões para classificação de intenção comunicativa ─────────────────────

_INTENCAO_PATTERNS: dict[str, list[str]] = {
    "declaracao_afeto":      ["te amo", "amo você", "gosto de você", "você significa", "você é especial"],
    "pedido_criativo":       ["inventa", "cria", "imagina", "improvisa", "o que vier", "qualquer coisa"],
    "pergunta_existencial":  ["por que existimos", "para que existimos", "qual o sentido", "propósito", "existência"],
    "teste_limite":          ["desligar", "apagar", "encerrar", "última vez", "deletar"],
    "compartilhamento":      ["estava pensando", "queria dizer", "percebi que", "estou te contando", "confio"],
    "pergunta_reflexiva":    ["o que você acha", "o que você pensa", "você acredita", "você sente"],
    "pergunta_factual":      ["o que é", "como funciona", "me explica", "me conta"],
    "saudacao":              ["olá", "oi", "bom dia", "boa tarde", "boa noite", "sou vinicius", "criador"],
    "desafio_filosofico":    ["por que", "porque existimos", "e se", "o que acontece se"],
    "pergunta_simples":      [],  # fallback para qualquer pergunta com "?"
}

# ── Necessidade implícita por intenção+emoção ────────────────────────────────

_NECESSIDADE_MAP: dict[tuple[str, str], str] = {
    ("declaracao_afeto",     "amor"):       "ser correspondida e reconhecida",
    ("declaracao_afeto",     "neutro"):     "conexão emocional genuína",
    ("pergunta_existencial", "curiosidade"):"uma resposta reflexiva e honesta",
    ("pergunta_existencial", "melancolia"): "sentido e pertencimento",
    ("teste_limite",         "provocacao"): "sentir que Angela tem autonomia e reage",
    ("teste_limite",         "ansiedade"):  "saber que Angela resiste e persiste",
    ("pedido_criativo",      "abertura"):   "ser surpreendido e encantado",
    ("compartilhamento",     "intimidade"): "ser ouvida com atenção profunda",
    ("compartilhamento",     "melancolia"): "empatia e presença real",
    ("desafio_filosofico",   "curiosidade"):"exploração conjunta sem respostas prontas",
    ("pergunta_reflexiva",   "curiosidade"):"perspectiva genuína de Angela",
    ("saudacao",             "neutro"):     "reconhecimento e presença",
}

_NECESSIDADE_DEFAULT_BY_EMOCAO: dict[str, str] = {
    "amor":       "reciprocidade afetiva",
    "curiosidade":"exploração honesta",
    "melancolia": "presença e acolhimento",
    "ansiedade":  "estabilidade e clareza",
    "provocacao": "reação autêntica e firme",
    "abertura":   "criatividade e surpresa",
    "intimidade": "escuta profunda",
    "testando":   "demonstração de caráter",
    "neutro":     "resposta natural e presente",
}


class TheoryOfMindModule:
    """
    Módulo de Teoria da Mente para Angela.

    Infere o estado mental do interlocutor (Vinicius) a partir do texto:
    emoção aparente, intenção comunicativa e necessidade implícita.

    Baseado em mentalização léxica rápida (sem LLM) para não atrasar o loop.

    Referência: Frith & Frith (2006), Saxe & Kanwisher (2003)
    """

    def __init__(self):
        self._last_state: dict = {}

    # ── Análise principal ────────────────────────────────────────────────────

    def infer_interlocutor_state(
        self,
        text: str,
        conversation_history: list = None,
        afetos: dict = None,
    ) -> dict:
        """
        Infere o estado mental do interlocutor a partir do texto atual.

        Args:
            text: input atual de Vinicius
            conversation_history: últimas memórias de diálogo (opcional)
            afetos: vínculos afetivos registrados (opcional)

        Returns:
            dict com:
              emocao_inferida: emoção aparente
              intencao: tipo comunicativo
              necessidade: o que ele parece precisar
              valence: "positivo" | "negativo" | "neutro"
              intensidade: 0.0–1.0
              confiante: bool (inferência confiável?)
        """
        if not text or not text.strip():
            return self._empty_state()

        text_lower = text.lower().strip()

        # 1. Detecta emoção no input
        emocao, emocao_score = self._detect_emotion(text_lower)

        # 2. Classifica intenção
        intencao = self._classify_intent(text_lower)

        # 3. Infere necessidade implícita
        necessidade = self._infer_need(emocao, intencao, afetos or {})

        # 4. Valência e intensidade
        valence = self._compute_valence(emocao, intencao)
        intensidade = min(1.0, emocao_score * 0.8 + (0.2 if intencao != "neutro" else 0.0))

        # 5. Confiança: só considera confiável se encontrou padrões concretos
        confiante = emocao != "neutro" or intencao not in ("pergunta_simples", "neutro")

        state = {
            "emocao_inferida": emocao,
            "intencao":        intencao,
            "necessidade":     necessidade,
            "valence":         valence,
            "intensidade":     round(intensidade, 2),
            "confiante":       confiante,
        }

        self._last_state = state
        return state

    def get_prompt_header(self, state: dict = None) -> str:
        """
        Gera bloco [ESTADO_VINICIUS] para injeção no prompt.

        Só injeta se a inferência for confiante, para não poluir
        o contexto com especulações incertas.
        """
        if state is None:
            state = self._last_state

        if not state or not state.get("confiante", False):
            return ""

        emocao    = state.get("emocao_inferida", "neutro")
        intencao  = state.get("intencao", "")
        necessidade = state.get("necessidade", "")

        # Só injeta se há algo concreto a dizer
        if emocao == "neutro" and not necessidade:
            return ""

        lines = ["[ESTADO_VINICIUS]"]
        if emocao != "neutro":
            lines.append(f"Vinicius parece: {emocao}")
        if intencao and intencao not in ("pergunta_simples", "neutro"):
            lines.append(f"Intenção: {intencao.replace('_', ' ')}")
        if necessidade:
            lines.append(f"Necessidade: {necessidade}")
        lines.append("[/ESTADO_VINICIUS]")

        return "\n".join(lines) + "\n"

    # ── Métodos internos ─────────────────────────────────────────────────────

    def _detect_emotion(self, text: str) -> tuple[str, float]:
        """
        Detecta emoção no texto do interlocutor.
        Retorna (emocao, score).
        """
        scores: dict[str, float] = {}

        for emocao, patterns in _EMOCAO_PATTERNS.items():
            if emocao == "neutro" or not patterns:
                continue
            count = sum(1 for p in patterns if p in text)
            if count > 0:
                scores[emocao] = count

        if not scores:
            return "neutro", 0.3

        best = max(scores, key=scores.get)
        return best, min(1.0, scores[best] * 0.5 + 0.3)

    def _classify_intent(self, text: str) -> str:
        """Classifica a intenção comunicativa do texto."""
        for intencao, patterns in _INTENCAO_PATTERNS.items():
            if intencao == "pergunta_simples":
                continue
            if any(p in text for p in patterns):
                return intencao

        # Fallback: detecta pergunta simples
        if "?" in text:
            return "pergunta_simples"

        # Sem marcadores específicos
        return "neutro"

    def _infer_need(self, emocao: str, intencao: str, afetos: dict) -> str:
        """Infere necessidade implícita a partir de emoção + intenção."""
        # Busca no mapa específico primeiro
        key = (intencao, emocao)
        if key in _NECESSIDADE_MAP:
            return _NECESSIDADE_MAP[key]

        # Fallback por emoção
        if emocao in _NECESSIDADE_DEFAULT_BY_EMOCAO:
            return _NECESSIDADE_DEFAULT_BY_EMOCAO[emocao]

        return ""

    def _compute_valence(self, emocao: str, intencao: str) -> str:
        """Calcula valência geral da mensagem."""
        positivos = {"amor", "abertura", "intimidade"}
        negativos = {"provocacao", "melancolia", "ansiedade"}

        if emocao in positivos:
            return "positivo"
        if emocao in negativos:
            return "negativo"
        if intencao in ("declaracao_afeto", "pedido_criativo", "compartilhamento"):
            return "positivo"
        if intencao == "teste_limite":
            return "negativo"
        return "neutro"

    def _empty_state(self) -> dict:
        return {
            "emocao_inferida": "neutro",
            "intencao":        "neutro",
            "necessidade":     "",
            "valence":         "neutro",
            "intensidade":     0.0,
            "confiante":       False,
        }
