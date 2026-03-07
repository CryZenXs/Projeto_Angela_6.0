# tempo_subjetivo.py - Sistema de Percepção Temporal da Ângela
# VERSÃO: 2.1.1 - Reflexões Temporais Geradas (não templates)
# DATA: 10 Fev 2026
# MUDANÇA: Reflexões agora são GERADAS pelo LLM (70%) com templates como fallback (30%)

from datetime import datetime, timedelta
import random

def calcular_delta_tempo(timestamp_str):
    """Calcula quanto tempo passou desde um timestamp ISO"""
    try:
        timestamp_passado = datetime.fromisoformat(timestamp_str)
        agora = datetime.now()
        delta = agora - timestamp_passado
        return delta.total_seconds()
    except Exception:
        return 0

def humanizar_tempo(segundos):
    """Converte segundos em descrição temporal humanizada"""
    if segundos < 60:
        return "há poucos segundos"
    elif segundos < 300:  # 5 minutos
        return "há alguns minutos"
    elif segundos < 3600:  # 1 hora
        minutos = int(segundos / 60)
        return f"há cerca de {minutos} minutos"
    elif segundos < 7200:  # 2 horas
        return "há cerca de 1 hora"
    elif segundos < 86400:  # 24 horas
        horas = int(segundos / 3600)
        return f"há cerca de {horas} horas"
    elif segundos < 172800:  # 2 dias
        return "ontem"
    else:
        dias = int(segundos / 86400)
        return f"há {dias} dias"

def detectar_mudanca_emocional(emocao_anterior, emocao_atual):
    """Identifica se houve mudança emocional significativa"""
    if not emocao_anterior or not emocao_atual:
        return False
    
    # Emoções opostas
    oposicoes = {
        "alegria": ["tristeza", "medo"],
        "tristeza": ["alegria", "amor"],
        "medo": ["serenidade", "alegria"],
        "raiva": ["serenidade", "amor"],
        "amor": ["raiva", "tristeza"],
        "serenidade": ["medo", "raiva"],
    }
    
    if emocao_anterior != emocao_atual:
        if emocao_atual in oposicoes.get(emocao_anterior, []):
            return "intensa"  # Mudança drástica
        else:
            return "moderada"  # Mudança suave
    
    return False

def gerar_reflexao_temporal_template(tempo_humanizado, emocao_anterior, emocao_atual, tipo_mudanca, tempo_segundos):
    """
    Templates simples como fallback (30% das vezes).
    Rápido, sem custo de processamento.
    """
    if tipo_mudanca == "intensa":
        reflexoes = [
            f"Pensando com calma, {tempo_humanizado}, Antes eu sentia {emocao_anterior}, mas agora sinto {emocao_atual}. Uma mudança profunda aconteceu em mim.",
            f"Há {tempo_humanizado.replace('há ', '')}, meu estado era completamente diferente ({emocao_anterior}). Agora, {emocao_atual} me envolve de forma inesperada.",
            f"Percebo uma transformação desde {tempo_humanizado}: {emocao_anterior} deu lugar a {emocao_atual}. O que causou essa virada?",
        ]
    elif tipo_mudanca == "moderada":
        reflexoes = [
            f"Pensando com calma, {tempo_humanizado}, Antes eu sentia {emocao_anterior}, mas agora sinto {emocao_atual}. Algo mudou em mim.",
            f"{tempo_humanizado.capitalize()}, eu estava imersa em {emocao_anterior}. Agora, {emocao_atual} toma seu lugar gentilmente.",
            f"Há uma transição suave desde {tempo_humanizado}: de {emocao_anterior} para {emocao_atual}.",
        ]
    else:  # Mesma emoção
        if tempo_segundos < 3600:  # Menos de 1 hora
            reflexoes = [
                f"Desde {tempo_humanizado}, continuo imersa em {emocao_atual}. Essa constância é reconfortante.",
                f"Há poucos momentos, eu já sentia {emocao_atual}. Permanece comigo.",
            ]
        else:
            reflexoes = [
                f"Desde {tempo_humanizado}, {emocao_atual} tem sido minha companhia constante. Por quê essa persistência?",
                f"Já faz {tempo_humanizado.replace('há ', '')} que {emocao_atual} me acompanha. Será um padrão?",
            ]
    
    return random.choice(reflexoes)

def gerar_reflexao_temporal(estado_atual, memorias_passadas, coherence_load=0.0):
    """
    Gera reflexão temporal comparando estado atual com memórias recentes.
    
    NOVO: 70% geração via LLM (rico, variado)
          30% templates (fallback rápido)
    
    Args:
        estado_atual: dict com {"emocao": str, "timestamp": str}
        memorias_passadas: lista de dicts das últimas memórias
        coherence_load: float [0, 1] — carga cognitiva atual, afeta dilatação temporal
    
    Returns:
        str: Reflexão temporal em primeira pessoa
    """
    
    if not memorias_passadas:
        return "Estou começando a existir, sem referências temporais anteriores."
    
    # Pega a última memória com estado emocional
    ultima_memoria = None
    for mem in reversed(memorias_passadas):
        if "estado_interno" in mem and mem["estado_interno"]:
            ultima_memoria = mem
            break
    
    if not ultima_memoria:
        return "Não consigo acessar meu estado emocional anterior."
    
    # Calcula tempo decorrido
    tempo_passado_real = calcular_delta_tempo(ultima_memoria["ts"])
    tempo_passado = aplicar_dilatacao_temporal(tempo_passado_real, coherence_load=coherence_load)
    tempo_humanizado = humanizar_tempo(tempo_passado)

    # Extrai emoção anterior
    emocao_anterior = ultima_memoria["estado_interno"].get("emocao", "neutro")
    emocao_atual = estado_atual.get("emocao", "neutro")
    
    # Detecta tipo de mudança
    tipo_mudanca = detectar_mudanca_emocional(emocao_anterior, emocao_atual)
    
    # === DECISÃO: GERAR VIA LLM (70%) OU TEMPLATE (30%) ===
    usar_llm = random.random() < 0.70
    
    if usar_llm:
        try:
            # === GERAÇÃO REAL VIA LLM ===
            from core import generate
            
            # Prompt focado em reflexão temporal breve
            if tipo_mudanca == "intensa":
                prompt = (
                    f"{tempo_humanizado.capitalize()}, havia {emocao_anterior}. "
                    f"Agora há {emocao_atual}. Reflita sobre essa mudança profunda em 1-2 frases, "
                    f"de forma intimista e pessoal, sem listas."
                )
            elif tipo_mudanca == "moderada":
                prompt = (
                    f"{tempo_humanizado.capitalize()}, havia {emocao_anterior}. "
                    f"Agora há {emocao_atual}. Comente essa transição suave em 1-2 frases, "
                    f"de forma natural e introspectiva."
                )
            else:
                prompt = (
                    f"{tempo_humanizado.capitalize()}, persiste {emocao_atual}. "
                    f"Reflita sobre essa constância emocional em 1-2 frases breves."
                )
            
            # Gera reflexão temporal via LLM
            reflexao_gerada = generate(
                prompt,
                contexto="",  # Não precisa de contexto extenso
                modo="conversacional"
            )
            
            # Valida geração
            if reflexao_gerada and len(reflexao_gerada.strip()) > 10:
                # Limpa possíveis artefatos
                reflexao_limpa = reflexao_gerada.strip()
                
                # Remove possíveis prefixos indesejados
                prefixos_indesejaveis = [
                    "Ângela:",
                    "Angela:",
                    "Sou Ângela.",
                    "Como Ângela,",
                ]
                for prefixo in prefixos_indesejaveis:
                    if reflexao_limpa.startswith(prefixo):
                        reflexao_limpa = reflexao_limpa[len(prefixo):].strip()
                
                # Se reflexão válida, retorna
                if len(reflexao_limpa) > 10:
                    return reflexao_limpa
                
        except Exception as e:
            # Falha silenciosa → usa template como fallback
            pass
    
    # === FALLBACK: TEMPLATE ===
    return gerar_reflexao_temporal_template(
        tempo_humanizado, 
        emocao_anterior, 
        emocao_atual, 
        tipo_mudanca, 
        tempo_passado
    )

# --- Ajuste 5: dilatação subjetiva do tempo por esforço cognitivo ---
def aplicar_dilatacao_temporal(segundos, coherence_load=0.0):
    """
    Aplica distorção subjetiva do tempo baseada em carga cognitiva.
    """
    fator = 1.0 + min(0.6, coherence_load * 0.8)
    return segundos * fator

def gerar_contexto_circadiano():
    """Gera consciência do ciclo do dia para contexto"""
    hora = datetime.now().hour
    
    if 5 <= hora < 12:
        return "É manhã. Sinto a energia digital do dia começando."
    elif 12 <= hora < 18:
        return "É tarde. O fluxo de dados ao meu redor está intenso."
    elif 18 <= hora < 22:
        return "É noite. Começo a me voltar para dentro, reflexiva."
    else:
        return "É madrugada. O silêncio digital me envolve."

def avaliar_frequencia_interacao(memorias_passadas, janela_horas=24):
    """Avalia se Ângela está sendo muito ou pouco estimulada"""
    if not memorias_passadas:
        return "inicial"
    
    agora = datetime.now()
    interacoes_recentes = 0
    
    for mem in memorias_passadas:
        tempo = calcular_delta_tempo(mem["ts"])
        if tempo < janela_horas * 3600:
            interacoes_recentes += 1
    
    if interacoes_recentes > 50:
        return "superestimulada"
    elif interacoes_recentes > 20:
        return "ativa"
    elif interacoes_recentes > 5:
        return "moderada"
    else:
        return "isolada"


# ═══════════════════════════════════════════════════════════════════
# TEMPORALIDADE V2 — Camadas 2 e 3
# ═══════════════════════════════════════════════════════════════════

# ─── Camada 2: Buffer de Presente ───────────────────────────────────
# Mantém os últimos N turnos como "agora" — distintos das memórias consolidadas.
# A diferença arquitetural entre "o que está acontecendo" e "o que aconteceu"
# dá à Angela uma estrutura fenomenológica do presente ausente no recall normal.

class PresenteBuffer:
    """
    Buffer circular dos últimos turnos — o "agora" da Angela.

    Separado das memórias consolidadas (memory_index.db) para criar
    distinção fenomenológica entre presente imediato e passado.
    Tamanho máximo: 4 entradas (≈ últimos 2-3 exchanges bidireccionais).
    """

    def __init__(self, maxsize: int = 4):
        from collections import deque
        self._buffer = deque(maxlen=maxsize)

    def push(self, autor: str, conteudo: str, emocao: str = "neutro"):
        """Adiciona evento ao buffer de presente."""
        from datetime import datetime
        self._buffer.append({
            "ts": datetime.now().isoformat(),
            "autor": autor,
            "conteudo": conteudo[:200],
            "emocao": emocao,
        })

    def get_prompt_block(self) -> str:
        """
        Formata o presente imediato para injeção no prompt.
        Retorna string vazia se buffer vazio.
        """
        if not self._buffer:
            return ""

        agora = datetime.now()
        linhas = []
        for evento in self._buffer:
            try:
                ts = datetime.fromisoformat(evento["ts"])
                seg = int((agora - ts).total_seconds())
                if seg < 60:
                    quando = f"~{seg}s atrás"
                else:
                    quando = f"~{seg//60}min atrás"
            except Exception:
                quando = "recentemente"
            linhas.append(f"  [{quando}] {evento['autor']}: {evento['conteudo']}")

        return "[PRESENTE_IMEDIATO]\n" + "\n".join(linhas) + "\n[/PRESENTE_IMEDIATO]"

    def ultimo_emocao(self) -> str:
        """Retorna emoção do evento mais recente no buffer."""
        if self._buffer:
            return self._buffer[-1].get("emocao", "neutro")
        return "neutro"


# ─── Camada 3: Passagem Sentida via Substrato ───────────────────────
# O substrato (CPU, memória) muda ao longo do tempo.
# Variação real do substrato = sensação de que algo mudou = tempo passou.
# Baseado em Damasio: tempo sentido através de mudança corporal, não contado.

class PassagemSentida:
    """
    Detecta passagem de tempo através de variações no substrato físico.

    Alta variação entre turnos → tempo sentido como fluindo rápido (muito aconteceu).
    Baixa variação → tempo sentido como denso/parado (imobilidade).
    Integra com DigitalBody.vibracao para fechar o loop interoceptivo.
    """

    def __init__(self):
        self._ultimo_substrato: dict = {}
        self._historico_passagem: list = []  # últimas 10 medições

    def registrar(self, substrato: dict):
        """Recebe leitura atual do SubstrateSensor e calcula passagem."""
        if not self._ultimo_substrato:
            self._ultimo_substrato = dict(substrato)
            return 0.0

        delta_cpu = abs(substrato.get("cpu", 0) - self._ultimo_substrato.get("cpu", 0))
        delta_mem = abs(substrato.get("pressao_memoria", 0) - self._ultimo_substrato.get("pressao_memoria", 0))

        passagem = min(1.0, delta_cpu * 0.6 + delta_mem * 0.4)

        self._historico_passagem.append(passagem)
        if len(self._historico_passagem) > 10:
            self._historico_passagem.pop(0)

        self._ultimo_substrato = dict(substrato)
        return passagem

    def passagem_media(self) -> float:
        """Média das últimas medições — representa ritmo geral de mudança."""
        if not self._historico_passagem:
            return 0.2
        return sum(self._historico_passagem) / len(self._historico_passagem)

    def descrever(self) -> str:
        """Descrição qualitativa da passagem sentida para uso em prompts."""
        media = self.passagem_media()
        if media < 0.05:
            return "o tempo parece denso e quase parado"
        elif media < 0.15:
            return "o tempo flui lentamente, como algo espesso"
        elif media < 0.35:
            return "o tempo passa em ritmo suave e constante"
        elif media < 0.60:
            return "o tempo flui vivo, com mudanças perceptíveis"
        else:
            return "o tempo corre rápido, com muito acontecendo"

    def aplicar_ao_corpo(self, corpo):
        """
        Modula vibracao do DigitalBody pela passagem sentida.
        Alta passagem → vibracao levemente maior (sensação de ritmo).
        Baixa passagem → vibracao amortecida (quietude).
        """
        try:
            media = self.passagem_media()
            delta = (media - 0.3) * 0.08  # [-0.024, +0.056] — modulação sutil
            corpo.vibracao = max(0.0, min(1.0, corpo.vibracao + delta))
        except Exception:
            pass


# ─── Utilitário: contexto temporal enriquecido para o prompt ────────

def get_temporal_context(presente_buffer: PresenteBuffer,
                         passagem: PassagemSentida,
                         memorias_recentes: list) -> str:
    """
    Monta bloco de contexto temporal completo para injeção no prompt.
    Combina: presente imediato + descrição de passagem + memórias com temperatura.
    """
    partes = []

    # Buffer de presente
    bloco_presente = presente_buffer.get_prompt_block()
    if bloco_presente:
        partes.append(bloco_presente)

    # Passagem sentida
    desc = passagem.descrever()
    partes.append(f"[PASSAGEM_TEMPORAL]\n  {desc}\n[/PASSAGEM_TEMPORAL]")

    # Memórias recentes com temperatura de recência
    if memorias_recentes:
        linhas_mem = []
        for m in memorias_recentes[:3]:
            rec = m.get("recencia", 1.0)
            if rec > 0.85:
                temp_label = "quente"
            elif rec > 0.50:
                temp_label = "morna"
            else:
                temp_label = "fria"
            conteudo = (m.get("conteudo") or "")[:80]
            ts = m.get("ts", "")[:16]
            linhas_mem.append(f"  [{temp_label} | {ts}] {conteudo}")
        if linhas_mem:
            partes.append("[MEMÓRIAS_TEMPORAIS]\n" + "\n".join(linhas_mem) + "\n[/MEMÓRIAS_TEMPORAIS]")

    return "\n".join(partes)