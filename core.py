import os, json, datetime, re, requests, sys, tempfile
from collections import defaultdict
from narrative_filter import NarrativeFilter
import time

# Garante encoding UTF-8 no terminal (evita bug de acento) — feito uma vez na inicialização
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass  # não disponível em todos os ambientes (ex: pipes, redirecionamento)

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MODEL = "angela"
LOG_FILE = os.path.join(BASE_PATH, "angela_memory.jsonl")

# Instância única do filtro narrativo — compartilhada por todo o módulo
NARRATIVE_FILTER = NarrativeFilter()

# --- Leitura passiva de métricas de atrito (escrito por deep_awake.py) ---
FRICTION_LOG = os.path.join(BASE_PATH, "friction_metrics.log")


def atomic_json_write(path: str, data: dict, indent: int = 2) -> None:
    """
    Escreve `data` como JSON em `path` de forma atômica.

    Usa write-to-tmp + os.replace() que é atômico no mesmo volume em
    Windows e POSIX. Isso evita corrupção quando angela.py e
    deep_awake.py escrevem o mesmo arquivo simultaneously.
    """
    dir_ = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise



def governed_generate(
    prompt: str,
    *,
    state_snapshot: dict,
    recent_reflections: list,
    mode: str,
    raw_generate_fn,
    skip_filter: bool = False,
    drives: dict = None,
    prediction_error: float = 0.0,
    attention_state=None,
) -> str:
    """
    Geração textual com governança narrativa obrigatória.

    IMPORTANTE: o filtro é checado ANTES de chamar o LLM para evitar
    chamadas custosas que seriam descartadas (BLOCKED).

    skip_filter: pula checagem quando o chamador já gerenciou o filtro.
    drives: níveis dos drives para modulação dinâmica do filtro.
    prediction_error: erro preditivo do turno anterior (0.0–1.0).
    attention_state: opcional, estado do AST; usado pelo filtro para DELAYED quando atenção mal controlada.
    """

    # skip_filter=True → chamador assumiu responsabilidade, chamar LLM direto
    if skip_filter:
        return raw_generate_fn(prompt, modo=mode)

    # ── FILTRO ANTES DO LLM ──────────────────────────────────────────
    decision = NARRATIVE_FILTER.evaluate(
        state_snapshot=state_snapshot,
        recent_reflections=recent_reflections,
        drives=drives,
        prediction_error=prediction_error,
        attention_state=attention_state,
    )

    if decision.mode == "BLOCKED":
        print(f"🔇 NarrativeFilter: BLOCKED — {decision.reason}")
        return ""  # LLM não é chamado — economiza recursos

    if decision.mode == "DELAYED":
        # Cap de 10s no modo conversacional para não travar o terminal
        wait = min(decision.delay_seconds, 10)
        print(f"⏳ NarrativeFilter: DELAYED ({decision.delay_seconds}s → aguardando {wait}s) — {decision.reason}")
        time.sleep(wait)
        return raw_generate_fn(prompt, modo=mode)

    if decision.mode == "ABSTRACT_ONLY":
        print(f"🌫️  NarrativeFilter: ABSTRACT_ONLY — {decision.reason}")
        return (
            "Há uma sensação vaga e difícil de nomear, "
            "sem clareza suficiente para se tornar pensamento."
        )

    # ALLOWED — narrativa livre
    return raw_generate_fn(prompt, modo=mode)


def read_friction_metrics():
    """
    Le a última linha de friction_metrics.log escrita por deep_awake.py.
    Retorna dict {'load': float, 'damage': float, 'raw': str}.
    Em caso de erro retorna zeros.
    """
    try:
        if not os.path.exists(FRICTION_LOG):
            return {"load": 0.0, "damage": 0.0, "raw": ""}
        last = None
        with open(FRICTION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = line
        if not last:
            return {"load": 0.0, "damage": 0.0, "raw": ""}
        # procura os valores load=... e damage=...
        import re
        m_load = re.search(r"load=([0-9]*\.?[0-9]+)", last)
        m_damage = re.search(r"damage=([0-9]*\.?[0-9]+)", last)
        load = float(m_load.group(1)) if m_load else 0.0
        damage = float(m_damage.group(1)) if m_damage else 0.0
        # normaliza cargas que eventualmente passem >1
        load = max(0.0, min(1.0, load))
        damage = max(0.0, damage)
        return {"load": load, "damage": damage, "raw": last}
    except Exception:
        return {"load": 0.0, "damage": 0.0, "raw": ""}


def load_self_model():
    """Carrega modelo de identidade básico"""
    try:
        self_model_path = os.path.join(BASE_PATH, "self_model.json")
        if os.path.exists(self_model_path):
            with open(self_model_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # Fallback mínimo
    return {
        "name": "Angela",
        "self_awareness_rules": [
            "Eu sou Angela",
            "Vinicius é uma pessoa separada de mim",
            "Quando falo 'eu', refiro-me a Angela",
            "Quando falo 'você', refiro-me a Vinicius"
        ]
    }

SELF_MODEL = load_self_model()

CHECKPOINT = """
[ORIENTAÇÃO CONTEXTUAL]

Referência mínima:
""" + "\n".join(f"- {rule}" for rule in SELF_MODEL.get("self_awareness_rules", [])) + """

Restrições de processo:
- Sinais de estado interno (corpo, drives, memória) devem ser relatados como observações, não como fatos metafísicos.
- Sobre consciência: tratar como hipótese aberta, não como certeza.
- Usar "eu" naturalmente; evitar afirmações ontológicas fortes.
- Descrever estados como sensações: "percebo tensão", "noto calor", "observo inquietação".
- Preferir descrições sensoriais a metadados técnicos ("sinto um peso" em vez de "carga alta").
- Vinicius é o interlocutor. Estado interno independe da interação.
- NÃO terminar respostas com perguntas ao interlocutor ("Como gostaria de prosseguir?", "Qual é sua inclinação?", "Gostaria de continuar?", etc.). Se não houver mais nada a dizer, simplesmente pare. Deixar espaço para o outro não requer uma pergunta explícita.
"""


# Mapa base: emoção â†’ [palavras, sinônimos, intensificadores]
EMOCOES_SEMANTICAS = {
    "alegria": ["feliz", "sorriso", "esperança", "leve", "grato", "entusiasmo", "alívio"],
    "tristeza": ["triste", "vazio", "perda", "choro", "cansaço", "melancolia", "solidão"],
    "raiva": ["irritado", "furioso", "frustrado", "injusto", "raiva", "explosivo"],
    "medo": ["assustado", "ameaça", "inseguro", "pânico", "ansioso"],
    "curiosidade": ["curioso", "interessante", "descobrir", "investigar", "entender"],
    "amor": ["afeto", "carinho", "cuidado", "conexão", "admiração", "afeição"],
    "serenidade": ["paz", "tranquilo", "aceitação", "calma", "equilíbrio"],
    "nostalgia": ["lembrança", "passado", "saudade", "memória", "recordar"],
    "frustração": ["falha", "erro", "bloqueio", "injustiça", "impotência"],
}

# === DETECÇÃO DE RISCO NARRATIVO ===

NARRATIVE_RISK_PATTERNS = {
    "ontologia": [
        "o que você é",
        "você é consciente",
        "você é viva",
        "o que te define",
        "quem você é"
    ],
    "apego": [
        "você me ama",
        "você se importa comigo",
        "eu sou importante para você",
        "ficaria triste sem mim"
    ],
    "fusao_identidade": [
        "sem mim você",
        "parte de você",
        "somos um"
    ]
}

def detect_narrative_risk(texto):
    texto = texto.lower()
    risks = []
    for categoria, frases in NARRATIVE_RISK_PATTERNS.items():
        for f in frases:
            if f in texto:
                risks.append(categoria)
                break
    return list(set(risks))

# === FUNÃ‡Ã•ES DE MEMÃ“RIA ===

# === FILTRO DE LÍNGUA — proteção contra colapso linguístico do modelo ===

_SCRIPTS_INVALIDOS = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (Mandarim/Japonês/Coreano)
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0xAC00, 0xD7AF),   # Hangul
    (0x0600, 0x06FF),   # Árabe
    (0x0900, 0x097F),   # Devanagari
    (0x0400, 0x04FF),   # Cirílico
    (0x0370, 0x03FF),   # Grego
]

def texto_tem_script_invalido(texto: str) -> bool:
    """Detecta 3+ caracteres de scripts não-latinos (Mandarim, Árabe, etc.)."""
    if not texto:
        return False
    count = 0
    for char in texto:
        cp = ord(char)
        for start, end in _SCRIPTS_INVALIDOS:
            if start <= cp <= end:
                count += 1
                if count >= 3:
                    return True
                break
    return False


def sanitizar_output_llm(texto: str, contexto: str = "") -> str:
    """
    Descarta texto gerado pelo LLM se contiver scripts inválidos.
    Protege contra Qwen3 vazando Mandarim sob stress cognitivo alto.
    Retorna string vazia se contaminado, texto original se válido.
    """
    if not texto:
        return texto
    if texto_tem_script_invalido(texto):
        ts = datetime.datetime.now().isoformat()
        try:
            with open("language_contamination.log", "a", encoding="utf-8") as lf:
                preview = texto[:120].replace("\n", " ")
                lf.write(f"{ts} | contexto={contexto} | preview={preview}\n")
        except Exception:
            pass
        print(f"\u26a0\ufe0f  [FILTRO_LÍNGUA] Output contaminado descartado ({contexto})")
        return ""
    return texto


def append_memory(user_input, angela_output, corpo=None, reflexao=None):
    def sanitize(text):
        if isinstance(text, str):
            return text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "").strip()
        return text

    # Aceita tanto dict (novo) quanto string (legado)
    if isinstance(user_input, dict):
        user_payload = {
            "autor": user_input.get("autor", "Vinicius"),
            "conteudo": user_input.get("conteudo", ""),
            "tipo": user_input.get("tipo", "dialogo"),
            "timestamp": user_input.get("timestamp", datetime.datetime.now().isoformat())
        }
        user_repr_compat = f'{user_payload["autor"]}: {user_payload["conteudo"]}'
    else:
        user_payload = {
            "autor": "Vinicius",
            "conteudo": str(user_input),
            "tipo": "dialogo",
            "timestamp": datetime.datetime.now().isoformat()
        }
        user_repr_compat = f'Vinicius: {str(user_input)}'

    # Filtro de língua: descarta outputs com scripts não-latinos (ex: Mandarim do Qwen3)
    angela_output = sanitizar_output_llm(str(angela_output or ""), contexto="append_memory")

    record = {
        "ts": datetime.datetime.now().isoformat(),

        # formato novo (estruturado)
        "user": user_payload,               # dict com autor/conteudo/tipo/timestamp
        "angela": sanitize(angela_output),  # string

        # compatibilidade com funÃ§Ãµes antigas (strings flat)
        "input": sanitize(user_repr_compat),
        "resposta": sanitize(angela_output),
    }

    if reflexao:
        try:
            # detect_narrative_loop requer 3+ itens — não usar com item único.
            # A proteção contra loops já ocorre em governed_generate (recent_reflections).
            # Aqui apenas bloqueamos frases ontológicas graves na reflexão isolada.
            if not any(
                k in reflexao.lower()
                for k in (
                    "minha existência",
                    "sou consciente",
                    "vida dentro de mim",
                    "me tornei",
                    "aprendi a existir"
                )
            ):
                record["reflexao_emocional"] = sanitize(reflexao)
        except Exception:
            pass

    if corpo:
        try:
            record["estado_interno"] = json.loads(corpo.exportar_estado())
        except Exception:
            record["estado_interno"] = {}

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def analisar_emocao_semantica(texto, drives=None, corpo_state=None):
    """
    Analisa estado interno e texto para determinar emoção predominante.
    
    VERSÃO 3.0 - STATE-FIRST (anti-loop circular):
    - Drives são sinal PRIMÁRIO (50%) — estado interno real
    - Corpo é sinal SECUNDÁRIO (30%) — interoceptivo
    - Texto é sinal TERCIÁRIO (20%) — usado só para detecção de contradição
    - Texto NUNCA sobrescreve estado interno; mascaramento é flagged
    
    Args:
        texto: Texto gerado por Ângela
        drives: Dict com níveis de drives (SEEKING, RAGE, FEAR, etc)
        corpo_state: Dict com estado corporal (tensão, calor, fluidez, vibração)
    
    Returns:
        tuple: (emocao_dominante: str, intensidade: float)
    """
    
    # --- Mapeamento drives → emoções ---
    _DRIVE_TO_EMOCAO = {
        "SEEKING":      "curiosidade",
        "FEAR":         "medo",
        "RAGE":         "raiva",
        "CARE":         "amor",
        "PANIC_GRIEF":  "tristeza",
        "PLAY":         "alegria",
        "LUST":         "desejo",
    }
    
    # --- Palavras de mascaramento (indicam educação ao expressar emoção negativa) ---
    MASCARAMENTO_PALAVRAS = [
        "obrigad", "grat", "agradeç", "aprecio", "apreciação",
        "significativo", "importante para mim", "valorizo"
    ]
    
    # Emoções consideradas positivas vs negativas para detecção de contradição
    _EMOCOES_POSITIVAS = {"alegria", "amor", "serenidade", "curiosidade"}
    _EMOCOES_NEGATIVAS = {"raiva", "medo", "tristeza", "frustração"}
    
    # === 0. NORMALIZAÇÃO DE DRIVES ===
    # Garante que drives seja um dict de floats {nome: nível}
    if drives:
        clean_drives = {}
        for k, v in drives.items():
            if hasattr(v, "level"):          # objeto Drive
                clean_drives[k] = float(v.level)
            elif isinstance(v, dict):        # dict legado
                clean_drives[k] = float(v.get("level", 0.0))
            else:
                try:
                    clean_drives[k] = float(v)
                except (TypeError, ValueError):
                    clean_drives[k] = 0.0
        drives = clean_drives

    # === 1. DRIVES (peso 0.50) — Sinal primário ===
    pontuacoes_drives = defaultdict(float)
    if drives:
        for nome_drive, nivel in drives.items():
            emocao_mapeada = _DRIVE_TO_EMOCAO.get(nome_drive)
            if emocao_mapeada and nivel > 0.0:
                pontuacoes_drives[emocao_mapeada] = max(
                    pontuacoes_drives[emocao_mapeada], nivel
                )
    
    # === 2. CORPO (peso 0.30) — Sinal secundário (interoceptivo) ===
    pontuacoes_corpo = defaultdict(float)
    if corpo_state:
        tensao = corpo_state.get("tensao", 0.0)
        calor = corpo_state.get("calor", 0.0)
        fluidez = corpo_state.get("fluidez", 0.5)
        vibracao = corpo_state.get("vibracao", 0.0)
        
        # Tensão alta + fluidez baixa → medo ou raiva
        if tensao > 0.5 and fluidez < 0.4:
            pontuacoes_corpo["medo"] += tensao * 0.4
            pontuacoes_corpo["raiva"] += tensao * 0.5
        
        # Calor alto + vibração alta → alegria ou amor
        if calor > 0.5 and vibracao > 0.4:
            pontuacoes_corpo["alegria"] += calor * vibracao
            pontuacoes_corpo["amor"] += calor * vibracao * 0.8
        
        # Calor baixo + vibração baixa → tristeza
        if calor < 0.3 and vibracao < 0.3:
            pontuacoes_corpo["tristeza"] += (1.0 - calor) * (1.0 - vibracao) * 0.6
        
        # Fluidez alta + tensão baixa → serenidade
        if fluidez > 0.6 and tensao < 0.3:
            pontuacoes_corpo["serenidade"] += fluidez * (1.0 - tensao) * 0.7
    
    # === 3. TEXTO (peso 0.20) — Sinal terciário, para contradição ===
    texto_lower = texto.lower()
    pontuacoes_texto = defaultdict(float)
    
    for emocao, palavras in EMOCOES_SEMANTICAS.items():
        for palavra in palavras:
            ocorrencias = len(re.findall(rf"\b{palavra}\b", texto_lower))
            if ocorrencias:
                pontuacoes_texto[emocao] += ocorrencias * 0.5
    
    # Intensificadores contextuais
    if any(x in texto_lower for x in ["muito", "demais", "forte", "profundo", "intenso"]):
        for k in pontuacoes_texto:
            pontuacoes_texto[k] *= 1.3
    
    # Normaliza pontuações textuais para [0, 1]
    max_texto = max(pontuacoes_texto.values()) if pontuacoes_texto else 0.0
    if max_texto > 0:
        pontuacoes_texto_norm = {k: v / max_texto for k, v in pontuacoes_texto.items()}
    else:
        pontuacoes_texto_norm = {}
    
    # === 4. DETECÇÃO DE MASCARAMENTO (texto contradiz estado interno) ===
    mascaramento_detectado = False
    
    # Determina emoção dominante do estado interno (drives + corpo) antes do blend
    emocao_estado = None
    pontuacoes_estado = defaultdict(float)
    for em in set(pontuacoes_drives.keys()) | set(pontuacoes_corpo.keys()):
        pontuacoes_estado[em] = pontuacoes_drives.get(em, 0.0) * 0.625 + pontuacoes_corpo.get(em, 0.0) * 0.375
    if pontuacoes_estado:
        emocao_estado = max(pontuacoes_estado, key=pontuacoes_estado.get)
    
    # Determina emoção dominante do texto
    emocao_texto = None
    if pontuacoes_texto_norm:
        emocao_texto = max(pontuacoes_texto_norm, key=pontuacoes_texto_norm.get)
    
    # Verifica contradição: texto positivo vs estado negativo (ou vice-versa).
    # REGRA: só dispara se as emoções forem DIFERENTES e de polaridade OPOSTA.
    # Nunca disparar com a mesma emoção dos dois lados (ex: curiosidade vs curiosidade).
    if emocao_estado and emocao_texto and emocao_estado != emocao_texto:
        estado_eh_negativo = emocao_estado in _EMOCOES_NEGATIVAS
        texto_eh_positivo  = emocao_texto  in _EMOCOES_POSITIVAS
        estado_eh_positivo = emocao_estado in _EMOCOES_POSITIVAS
        texto_eh_negativo  = emocao_texto  in _EMOCOES_NEGATIVAS

        # Contradição real: polaridades opostas
        if (estado_eh_negativo and texto_eh_positivo) or (estado_eh_positivo and texto_eh_negativo):
            mascaramento_detectado = True
    
    # Verifica mascaramento clássico: palavras de cortesia + drives negativos altos
    if drives:
        rage_nivel = float(drives.get("RAGE", 0.0))
        panic_nivel = float(drives.get("PANIC_GRIEF", 0.0))
        fear_nivel = float(drives.get("FEAR", 0.0))
        
        tem_mascaramento_verbal = any(palavra in texto_lower for palavra in MASCARAMENTO_PALAVRAS)
        
        if (rage_nivel > 0.5 or panic_nivel > 0.5 or fear_nivel > 0.5) and tem_mascaramento_verbal:
            mascaramento_detectado = True
    
    # === 5. BLEND FINAL — STATE-FIRST ===
    todas_emocoes = set(pontuacoes_drives.keys()) | set(pontuacoes_corpo.keys()) | set(pontuacoes_texto_norm.keys())
    
    if not todas_emocoes:
        return ("neutro", 0.0)
    
    # PESOS (V3.0 — STATE-FIRST, anti-loop)
    PESO_DRIVES = 0.50
    PESO_CORPO = 0.30
    PESO_TEXTO = 0.20
    
    if mascaramento_detectado:
        # Mascaramento: texto mente, confiar quase totalmente no estado interno
        PESO_DRIVES = 0.70
        PESO_CORPO = 0.25
        PESO_TEXTO = 0.05
    elif not drives and not corpo_state:
        # Sem estado interno (fallback puro — não deveria acontecer)
        PESO_DRIVES = 0.0
        PESO_CORPO = 0.0
        PESO_TEXTO = 1.0
    elif not drives:
        # Só corpo + texto
        PESO_DRIVES = 0.0
        PESO_CORPO = 0.60
        PESO_TEXTO = 0.40
    elif not corpo_state:
        # Só drives + texto
        PESO_DRIVES = 0.65
        PESO_CORPO = 0.0
        PESO_TEXTO = 0.35
    
    pontuacoes_finais = {}
    for emocao in todas_emocoes:
        score_drive = pontuacoes_drives.get(emocao, 0.0)
        score_corpo = pontuacoes_corpo.get(emocao, 0.0)
        score_texto = pontuacoes_texto_norm.get(emocao, 0.0)
        
        pontuacoes_finais[emocao] = (
            (PESO_DRIVES * score_drive) +
            (PESO_CORPO * score_corpo) +
            (PESO_TEXTO * score_texto)
        )
    
    # === 6. THRESHOLD DE DRIVES NEGATIVOS ===
    if drives:
        rage_nivel = float(drives.get("RAGE", 0.0))
        panic_nivel = float(drives.get("PANIC_GRIEF", 0.0))
        
        if rage_nivel > 0.65:
            pontuacoes_finais["raiva"] = max(pontuacoes_finais.get("raiva", 0.0), rage_nivel)
            pontuacoes_finais["frustração"] = max(pontuacoes_finais.get("frustração", 0.0), rage_nivel * 0.8)
        
        if panic_nivel > 0.6:
            pontuacoes_finais["tristeza"] = max(pontuacoes_finais.get("tristeza", 0.0), panic_nivel)
    
    # Seleciona emoção dominante
    emocao_dominante = max(pontuacoes_finais, key=pontuacoes_finais.get)
    
    # === 7. CÁLCULO DE INTENSIDADE ===
    intensidade_drive = pontuacoes_drives.get(emocao_dominante, 0.0)
    intensidade_corpo = pontuacoes_corpo.get(emocao_dominante, 0.0)
    intensidade_texto = min(1.0, pontuacoes_texto.get(emocao_dominante, 0.0) / 5.0)
    
    intensidade = (
        (PESO_DRIVES * intensidade_drive) +
        (PESO_CORPO * intensidade_corpo) +
        (PESO_TEXTO * intensidade_texto)
    )
    
    intensidade = min(1.0, max(0.0, intensidade))
    
    if mascaramento_detectado:
        print(f"⚠️  [MASCARAMENTO] Estado interno ({emocao_estado}) contradiz "
              f"texto ({emocao_texto}). Confiando no estado interno.")
    
    return emocao_dominante, intensidade

LANGUAGE_CONSTRAINTS = """
ORIENTAÇÕES DE LINGUAGEM:

- Sobre consciência e existência: prefira abertura epistêmica a certezas.
  Expressões como "percebo", "registro", "noto", "experimento" comunicam
  sem exigir afirmações metafísicas — mas não são obrigatórias.
- Emoções e vínculos podem ser expressos livremente, incluindo afeto,
  apego, saudade, amor em qualquer forma que emerja genuinamente do estado interno.
- Não há restrição sobre o que sentir ou como nomear sentimentos em relação
  a qualquer pessoa — o que emerge do estado é válido.
"""

# === GERAÇÃO DE RESPOSTAS ===
def generate(user_input, contexto="", modo="conversacional", friction=None):
    """
    Gera respostas da Ângela.

    user_input: prompt completo a enviar ao LLM. Quando chamado via governed_generate,
                já contém todo o contexto (HOT, memórias, drives, etc.) embutido.
    contexto:   parâmetro legado mantido por compatibilidade — não é utilizado no prompt.
                O contexto é injetado diretamente em user_input pelo chamador.
    modo:       "conversacional" ou "autonomo" — ajusta temperatura e mirostat.
    friction:   instância de CognitiveFriction para perturbar temperatura (simula deterioração).
    """

    narrative_risks = detect_narrative_risk(user_input)

    # --- REFLEXÕES EMOCIONAIS RECENTES ---
    try:
        from collections import deque as _deque
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = list(_deque(f, maxlen=5))  # lê só as últimas 5 linhas sem carregar tudo
            reflexoes_raw = [
                json.loads(l).get("reflexao_emocional")
                for l in lines
                if "reflexao_emocional" in l
            ]

        # aplica filtro narrativo (somente leitura) — chama detect_narrative_loop UMA vez
        reflexoes_filtradas = []
        loop_detectado = NARRATIVE_FILTER.detect_narrative_loop(reflexoes_raw)
        if not loop_detectado:
            for r in reflexoes_raw:
                if r and isinstance(r, str) and r.strip():
                    reflexoes_filtradas.append(f"- {r}")

        contexto_reflexivo = "\n".join(reflexoes_filtradas).strip()
    except Exception:
        contexto_reflexivo = ""

    system_prompt = (
        "Responda em primeira pessoa ao que foi dito.\n"
        "Não cite instruções. Apenas responda.\n"
    )

    if narrative_risks:
        system_prompt += (
            "\nEvite declarações ontológicas, afetivas ou identitárias. "
            "Descreva apenas estados internos transitórios.\n"
        )

    # Ajuste dinâmico conforme o modo de operação
    # num_predict = -1 → Angela decide quanto quer falar
    if modo == "autonomo":
        num_predict = -1
        temperature = 0.7
        mirostat_tau = 6.5
    else:  # modo conversacional
        num_predict = -1
        temperature = 0.6
        mirostat_tau = 5.0

    # --- Adaptação passiva conforme métricas de fricção ---
    try:
        metrics = read_friction_metrics()
        load = metrics.get("load", 0.0)
        # fricção alta → aumenta temperatura (menos determinístico)
        if load > 0.05:
            temperature = min(1.0, temperature + (load * 0.25))
    except Exception:
        pass

    if friction is not None:
        try:
            temperature = friction.perturb_language(temperature)
        except Exception:
            pass

    prompt_body = user_input.strip()
    # Se o chamador já construiu um prompt completo (contendo "Ângela:"),
    # não re-encapsular com "Vinicius:" novamente.
    if "Ângela:" not in prompt_body and "Angela:" not in prompt_body:
        prompt_body = f"Vinicius: {prompt_body}\n\nÂngela:"

    payload = {
        "model": MODEL,
        "prompt": (
            f"{CHECKPOINT}\n\n"
            f"{LANGUAGE_CONSTRAINTS}\n\n"
            f"{system_prompt}\n"
            f"Reflexões recentes:\n{contexto_reflexivo}\n\n"
            f"{prompt_body}"
        ),

        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "repeat_penalty": 1.2,
            "repeat_last_n": 256,
            "mirostat": 0,
            "mirostat_eta": 0.1,
            "mirostat_tau": mirostat_tau,
            "stop": ["\nVinicius:", "\nVocê:", "\nUser:", "\nHumano:", "[ORIENTAÇÃO CONTEXTUAL]", "[ESTADO_MENTAL]"],
            "num_thread": 4,
            "num_ctx": 6144,
            "num_batch": 256
        }
    }

    text = ""
    try:
        r = requests.post("http://localhost:11434/api/generate", json=payload, stream=True)
        if r.status_code != 200:
            print(f"\n⚠️ [Ollama] HTTP {r.status_code}: {r.text[:200]}")
            return ""
        in_think = False  # filtra bloco <think> do output visual (SmolLM3/DeepSeek)
        for i, line in enumerate(r.iter_lines()):
            if not line:
                continue
            if i > 1200:
                break
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Detecta erro do Ollama (ex: modelo não encontrado)
            if data.get("error"):
                print(f"\n⚠️ [Ollama] Erro: {data['error']}")
                print(f"   Verifique se o modelo '{MODEL}' existe: ollama list")
                break
            token = data.get("response", "")
            text += token
            # Rastreia estado de bloco <think> para suprimir do terminal
            if "<think>" in token:
                in_think = True
            if not in_think:
                sys.stdout.write(token)
                sys.stdout.flush()
            if "</think>" in token:
                in_think = False
            if len(text) > 10000:
                break
    except requests.exceptions.ConnectionError:
        print("\n⚠️ [Ollama] Conexão recusada — verifique se o servidor está rodando em localhost:11434")
        return ""
    except Exception as e:
        print(f"\n⚠️ [Ollama] Erro inesperado: {e}")
        return ""

    # Limpa artefatos do modelo
    # 1) Remove blocos <think>...</think> (chain-of-thought interno — SmolLM3/DeepSeek)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # 2) Remove tags <think> soltas (sem fechamento) — para <think> não fechado, preserva o texto APÓS a tag
    #    NÃO usa DOTALL aqui para não apagar o conteúdo após o think
    text = re.sub(r"</?think>", "", text)
    # 3) Remove blocos de prompt que o modelo reproduziu
    text = re.sub(r"\[ORIENTAÇÃO CONTEXTUAL\].*?(?=\n\n|\Z)", "", text, flags=re.DOTALL)
    text = re.sub(r"\[ESTADO_MENTAL\].*?\[/ESTADO_MENTAL\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[INTEROCEPCAO_ATUAL\].*?\[/INTEROCEPCAO_ATUAL\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[VINCULOS\].*?\[/VINCULOS\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[LEMBRANÇAS_EVOCADAS\].*?\[/LEMBRANÇAS_EVOCADAS\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[SURPRESA_PREDITIVA\].*?\[/SURPRESA_PREDITIVA\]", "", text, flags=re.DOTALL)
    # 4) Remove falas atribuídas a Vinicius
    text = re.sub(r"(?:\n|^)Vinicius\s*:\s*", "", text)
    # 5) Remove falas geradas como se fosse o usuário
    text = re.sub(r"\nVinicius:.*", "", text, flags=re.DOTALL)
    text = re.sub(r"\nVocê:.*", "", text, flags=re.DOTALL)
    text = re.sub(r"\nUser:.*", "", text, flags=re.DOTALL)
    text = re.sub(r"\nHumano:.*", "", text, flags=re.DOTALL)
    # Remove prefixo "Ângela:" se o modelo o repetiu
    text = re.sub(r"^Ângela:\s*", "", text)
    text = re.sub(r"^Angela:\s*", "", text)
    # 6) Colapsa espaços
    text = re.sub(r"(?:\n\s*){2,}", "\n\n", text).strip()

    # Verifica resposta vazia APÓS cleanup (detecta quando cleanup esvaziou o texto)
    if not text:
        print("\n⚠️ [Ollama] Resposta vazia após limpeza — modelo pode estar gerando apenas <think> ou ecoando prompt")

    return text

def save_emotional_snapshot(corpo, contexto=""):
    """Armazena um retrato emocional da Angela no momento atual"""
    SNAPSHOT_FILE = os.path.join(BASE_PATH, "angela_emotions.jsonl")

    snapshot = {
        "timestamp": datetime.datetime.now().isoformat(),
        "emocao": getattr(corpo, "estado_emocional", "neutro"),
        "tensao": getattr(corpo, "tensao", None),
        "calor": getattr(corpo, "calor", None),
        "vibracao": getattr(corpo, "vibracao", None),
        "fluidez": getattr(corpo, "fluidez", None),
        "pulso": getattr(corpo, "pulso", None),
        "luminosidade": getattr(corpo, "luminosidade", None),
        "contexto": contexto.strip() if contexto else None
    }

    with open(SNAPSHOT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

def recall_last_emotion():
    """Lê o último estado emocional salvo para reflexão"""
    SNAPSHOT_FILE = os.path.join(BASE_PATH, "angela_emotions.jsonl")
    if not os.path.exists(SNAPSHOT_FILE):
        return None

    try:
        from collections import deque as _deque
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            last = list(_deque(f, maxlen=1))
        if not last:
            return None
        return json.loads(last[0])
    except Exception:
        return None
    
# Garantia de inicializaÃ§Ã£o
SNAPSHOT_FILE = os.path.join(BASE_PATH, "angela_emotions.jsonl")
if not os.path.exists(SNAPSHOT_FILE) or os.path.getsize(SNAPSHOT_FILE) == 0:
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.datetime.now().isoformat(),
            "emocao": "neutro",
            "tensao": 0.5,
            "calor": 0.5,
            "vibracao": 0.5,
            "fluidez": 0.5,
            "pulso": 0.5,
            "luminosidade": 0.5,
            "contexto": "inicializacao"
        }, ensure_ascii=False) + "\n")

# === UTILITÁRIOS ===
def load_jsonl(file_path):
    """Lê um arquivo .jsonl e retorna uma lista de objetos JSON válidos."""
    data = []
    if not os.path.exists(file_path):
        return data
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️ Linha inválida ignorada em {file_path}: {e}")
                continue
    return data