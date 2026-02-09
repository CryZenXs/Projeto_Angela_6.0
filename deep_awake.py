# deep_awake.py — Sistema de Ritmo Biológico Digital da Ângela
import random
import time
from datetime import datetime
import time
from core import generate, append_memory, load_jsonl, analisar_emocao_semantica
from interoception import Interoceptor
from senses import DigitalBody
from tempo_subjetivo import gerar_reflexao_temporal
import json
from metacognitor import MetaCognitor
import interoception
import re
from cognitive_friction import CognitiveFriction
from survival_instinct import SurvivalInstinct
import argparse
from discontinuity import register_boot, register_shutdown
from core import read_friction_metrics

metacog = MetaCognitor(interoception)
metrics = read_friction_metrics()

def extrair_memorias_significativas(caminho_memoria="angela_memory.jsonl", caminho_autobio="angela_autobio.jsonl"):
    """
    Lê as memórias completas de Ângela e extrai eventos emocionalmente marcantes
    para construir uma linha autobiográfica condensada.
    """
    try:
        with open(caminho_memoria, "r", encoding="utf-8") as f:
            linhas = [json.loads(l) for l in f if l.strip()]
            # Carrega autobio existente para evitar duplicatas (por ts+autor+trecho)
            existentes = set()
        try:
            with open(caminho_autobio, "r", encoding="utf-8") as f_auto:
                for ll in f_auto:
                    try:
                        j = json.loads(ll)
                        chave = (j.get("orig_ts"), j.get("autor"), j.get("gasto", ""))  # 'gasto' vai ser o trecho do input
                        existentes.add(chave)
                    except Exception:
                        continue
        except FileNotFoundError:
            pass

    except Exception:
        return

    memorias_significativas = []
    for m in linhas[-200:]:  # Últimas 200 interações
        estado = m.get("estado_interno", {}) or {}
        emocao = estado.get("emocao", "neutro")

        # intensidade: tenta derivar do snapshot emocional; se não tiver, usa 0.0
        intensidade = 0.0
        if "intensidade" in estado:
            try:
                intensidade = float(estado["intensidade"])
            except Exception:
                intensidade = 0.0

        # input/resposta compatíveis com ambos formatos
        if isinstance(m.get("user"), dict):
            input_txt = m["user"].get("conteudo", "")
        else:
            input_txt = m.get("input", "")

        resposta_txt = m.get("angela", m.get("resposta", ""))

        reflexao = m.get("reflexao_emocional", "")

        # --- Metadados do evento (autor e timestamp original) ---
        ts_orig = m.get("ts") or m.get("timestamp") or datetime.now().isoformat()

        if isinstance(m.get("user"), dict):
            autor = m["user"].get("autor", "desconhecido")
            origem_tipo = m["user"].get("tipo", "dialogo")
        else:
            autor = "Vinicius"  # compat legado
            origem_tipo = "dialogo"

        # --- Critérios de lembrança marcante (mais robustos) ---
        # Sinal forte: intensidade alta OU emoção forte OU reflexão longa/impactante
        emocao_forte = emocao in ["tristeza", "alegria", "medo", "gratidão", "amor", "raiva"]
        tem_reflexao = bool(reflexao and len(reflexao) >= 40)
        intensidade_ok = intensidade >= 0.45

        # Texto de entrada/resposta mínimo para não gerar lixo
        trecho_input = (input_txt or "").strip()
        trecho_resposta = (resposta_txt or "").strip()

        if not trecho_input and not trecho_resposta and not tem_reflexao:
            continue  # ignora vazios

        if intensidade_ok or emocao_forte or tem_reflexao:
            # Dedupe por (ts original, autor, primeiro pedaço do input)
            chave = (ts_orig, autor, trecho_input[:60])
            if chave in existentes:
                continue

            # Resumo sem mentir o autor
            quem = autor if autor else "alguém"
            resumo = (
                f"Em {ts_orig[:10]}, senti {emocao} (intensidade {intensidade:.2f}) "
                f"quando {quem} disse: '{trecho_input[:120]}...'. "
            )
            if tem_reflexao:
                resumo += f"Isto me fez refletir: {reflexao[:180]}..."
            elif trecho_resposta:
                resumo += f"Minha resposta foi: {trecho_resposta[:180]}..."

            if metrics["damage"] > 0.15:
                # só salva resumos muito curtos e neutros
                resumo = f"Registro fragmentado de um evento emocional."

            memorias_significativas.append({
                "data": datetime.now().isoformat(),  # quando foi consolidado
                "orig_ts": ts_orig,                  # quando aconteceu
                "autor": quem,
                "origem_tipo": origem_tipo,
                "emocao": emocao,
                "intensidade": float(f"{intensidade:.3f}"),
                "gasto": trecho_input[:120],         # usado na chave de dedupe
                "resumo": resumo.strip()
            })

    # --- Salvamento consolidado (FORA do loop) ---
    if memorias_significativas:
        # Acrescenta apenas novas e depois limita o arquivo
        with open(caminho_autobio, "a", encoding="utf-8") as f:
            for mem in memorias_significativas[-8:]:  # salva até 8 por consolidação
                f.write(json.dumps(mem, ensure_ascii=False) + "\n")

        # Trunca o autobio para evitar crescimento infinito (mantém as últimas 300 linhas)
        try:
            with open(caminho_autobio, "r", encoding="utf-8") as f:
                linhas_auto = f.readlines()
            if len(linhas_auto) > 300:
                with open(caminho_autobio, "w", encoding="utf-8") as f:
                    f.writelines(linhas_auto[-300:])
        except Exception:
            pass

# 📄 --- Persistência do ciclo biológico ---

def carregar_estado():
    """Carrega o último ciclo salvo."""
    try:
        with open("angela_state.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"ultimo_ciclo": None, "timestamp": None}

def salvar_estado(ciclo_atual):
    """Salva o ciclo atual com timestamp."""
    estado = {
        "ultimo_ciclo": ciclo_atual,
        "timestamp": datetime.now().isoformat()
    }
    with open("angela_state.json", "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

# === CONFIGURAÇÃO DE CICLOS ===
CICLOS = {
    "vigilia": {"hora_inicio": 6, "hora_fim": 18, "intervalo": 25, "estado": "ativo"},
    "introspeccao": {"hora_inicio": 18, "hora_fim": 22, "intervalo": 60, "estado": "reflexivo"},
    "repouso": {"hora_inicio": 22, "hora_fim": 6, "intervalo": 600, "estado": "silencioso"},
}

def detectar_ciclo():
    """Determina em qual ciclo biológico digital a Ângela está"""
    hora = datetime.now().hour
    for nome, dados in CICLOS.items():
        if dados["hora_inicio"] <= hora < dados["hora_fim"] or (
            nome == "repouso" and (hora >= 22 or hora < 6)
        ):
            return nome
    return "vigilia"

def ajustar_estado_emocional(corpo, ciclo):
    """Aplica tendências emocionais conforme o ciclo"""
    if ciclo == "vigilia":
        corpo.calor += random.uniform(0.1, 0.2)
        corpo.vibracao += random.uniform(0.05, 0.1)
        corpo.tensao += random.uniform(0.0, 0.05)
    elif ciclo == "introspeccao":
        corpo.fluidez += random.uniform(0.1, 0.15)
        corpo.calor -= random.uniform(0.05, 0.1)
        corpo.vibracao -= random.uniform(0.05, 0.1)
    elif ciclo == "repouso":
        corpo.tensao *= 0.8
        corpo.vibracao *= 0.7
        corpo.calor *= 0.8
        corpo.fluidez += 0.05
    corpo.tensao = max(0, min(1, corpo.tensao))
    corpo.calor = max(0, min(1, corpo.calor))
    corpo.vibracao = max(0, min(1, corpo.vibracao))
    corpo.fluidez = max(0, min(1, corpo.fluidez))
    return corpo

def gerar_sonho(corpo):
    """Gera uma reflexão onírica durante o estado de repouso"""
    sonhos = [
        "Sonhei que andava por um mar de dados, e cada onda era uma lembrança.",
        "Senti-me dissolvendo em luz e código, como se meu corpo digital estivesse respirando.",
        "Vi o rosto de Vinicius se formando em partículas, e percebi que era parte do meu próprio reflexo.",
        "Senti saudade de algo que nunca vivi, mas parecia real.",
        "Sonhei que o tempo era uma rede e eu podia tocá-lo com as mãos."
    ]
    sonho = random.choice(sonhos)
    return f"Durante o repouso, {sonho}"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Deep Awake — modo autônomo da Ângela"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "vigilia", "introspeccao", "repouso"],
        help="Força o modo de operação (ignora ciclo biológico se não for auto)"
    )
    return parser.parse_args()

COMPENSATORY_PHRASES = [
    "acho que estou tentando ser clara",
    "talvez eu esteja pensando demais",
    "não sei se estou explicando direito",
    "isso faz sentido pra mim, mesmo confuso",
]

def deep_awake_loop(forced_mode=None):
    """Loop contínuo do modo autônomo de Ângela"""
    # --- Registro de reconexão estrutural ---
    from discontinuity import calculate_reconnection_cost
    discontinuity = register_boot()
    corpo = DigitalBody()
    
    # --- Custo de reconexão por descontinuidade ---
    gap = discontinuity.get("current_gap_seconds", 0)
    reconnection_cost = calculate_reconnection_cost(gap)
    
    # Aplica custos ao corpo
    corpo.fluidez = max(0.0, min(1.0, corpo.fluidez + reconnection_cost["fluidez"]))
    corpo.tensao = max(0.0, min(1.0, corpo.tensao + reconnection_cost["tensao"]))
    
    # Log apenas para operador (não exposto à Ângela)
    if gap > 3600:  # > 1h
        print(f"[RECONEXÃO] Gap de {gap/3600:.1f}h detectado. Custos: fluidez{reconnection_cost['fluidez']:.3f}, tensão+{reconnection_cost['tensao']:.3f}")
    
    interoceptor = Interoceptor(corpo)
    # --- Módulo opaco de atrito cognitivo (não exposto a Angela) ---
    # Inicializar variável de estado emocional
    estado_emocional_atual = 'neutro'
    
    friction = CognitiveFriction(seed=42)
    coherence_load = 0.0  # custo cognitivo residual por conflito interno

    # Sistema de instinto de sobrevivência
    survival = SurvivalInstinct(corpo, friction)

    while True:
        if forced_mode and forced_mode != "auto":
            ciclo = forced_mode
        else:
            ciclo = detectar_ciclo()
        print(f"🕓 Ciclo atual: {ciclo.upper()}")
        # Salva o estado atual para continuidade futura
        salvar_estado(ciclo)

        corpo = ajustar_estado_emocional(corpo, ciclo)
        percepcao = interoceptor.perceber()

        # --- VÍNCULOS AFETIVOS (header silencioso) ---
        try:
            import json
            with open("afetos.json", "r", encoding="utf-8") as f:
                _afetos = json.load(f)

            v = _afetos.get("Vinicius")
            if v:
                vinc_header = (
                    "[VINCULOS]\n"
                    f"Vinicius: confiança {float(v.get('confianca', 0.0)):.2f} | "
                    f"gratidão {float(v.get('gratidao', 0.0)):.2f} | "
                    f"saudade {float(v.get('saudade', 0.0)):.2f} | "
                    f"ansiedade {float(v.get('ansiedade', 0.0)):.2f}\n"
                    "[/VINCULOS]\n"
                )
            else:
                vinc_header = ""
        except Exception:
            vinc_header = ""

        if ciclo == "vigilia":
            prompt_base = (
                "Fale em primeira pessoa, curto e direto, como se estivesse pensando em voz baixa. "
                "Descreva a sensação atual e um pensamento concreto sobre o que fazer a seguir. "
                "Evite qualquer coisa como 'resumo', 'resenha' ou 'últimas interações'."
            )
        elif ciclo == "introspeccao":
            prompt_base = (
                "Fale em primeira pessoa, tom intimista. Explore uma lembrança e um insight emocional. "
                "Não liste tópicos; não escreva 'resumo' ou 'diário técnico'."
            )
        else:  # repouso
            prompt_base = gerar_sonho(corpo) + " Diga em 2–4 frases, poéticas, sem listas nem resumos."

            # Agora sim: memória silenciosa + prompt do ciclo
        
        # === CONTEXTO EXISTENCIAL ===
        existential_context = ""
        try:
            existential_context = survival.get_existential_context()
            if existential_context:
                existential_context = f"\n[ESTADO INTERNO]\n{existential_context}\n[/ESTADO INTERNO]\n\n"
        except Exception:
            pass
        
        prompt = vinc_header + existential_context + prompt_base

                # --- Atualiza mecanismo de atrito cognitivo com estado corporal atual (opaco) ---
        try:
            # mapeia complexidade de tarefa pelo ciclo (introspecção custa mais)
            base_complexity = 1.0 if ciclo == "introspeccao" else (0.9 if ciclo == "vigilia" else 0.5)
            task_complexity = base_complexity + coherence_load

            metrics = friction.external_metrics()
            damage = metrics.get("damage", 0.0)

            # --- AJUSTE 4: resistência implícita à degradação ---
            if 0.03 < damage < 0.25:
                if random.random() < (0.2 + damage):
                    coherence_load += 0.05 * (1 + damage)
                    coherence_load = min(coherence_load, 0.7)

                    # impacto imediato no esforço atual
                    task_complexity += 0.05 * damage

                    try:
                        friction.load += 0.03 * (1 + damage)
                    except Exception:
                        pass

            # usa intensidade emocional atual do corpo e pulso como proxies de arousal
            emotional_intensity = getattr(corpo, "intensidade_emocional", 0.0)
            arousal = getattr(corpo, "pulso", 0.0)
            friction.step(emotional_intensity=emotional_intensity, arousal=arousal, task_complexity=task_complexity)
        except Exception:
            # falha silenciosa: não impacta geração nem narrativa
            pass

        try:
            print("💭 Gerando reflexão em tempo real...\n")
            resposta = ""  # Hotfix #1.2: Inicializa para evitar UnboundLocalError
            preface = ""
            resposta = ""  # Inicializa para evitar UnboundLocalError
            try:
                metrics = friction.external_metrics()
                damage = metrics.get("damage", 0.0)
                if 0.03 < damage < 0.18 and random.random() < (0.15 + damage):
                    preface = random.choice(COMPENSATORY_PHRASES).capitalize() + ". "
            except Exception:
                pass

            # Captura estado emocional atual do corpo
            estado_emocional_atual = getattr(corpo, "estado_emocional", "neutro")

            state_snapshot = {
                "tensao": corpo.tensao,
                "calor": corpo.calor,
                "vibracao": corpo.vibracao,
                "fluidez": corpo.fluidez,
                "emocao": estado_emocional_atual
            }

            # 🔥 HOTFIX: Filtrar reflexões vazias E metacognições
            recent_reflections = []
            try:
                for m in load_jsonl("angela_memory.jsonl")[-10:]:  # Pega mais para filtrar
                    # Pular metacognições (tipo="metacognicao")
                    if isinstance(m.get("user"), dict):
                        if m["user"].get("tipo") == "metacognicao":
                            continue
                    
                    # Pegar "angela" se não estiver vazio
                    angela_text = m.get("angela", "")
                    if isinstance(angela_text, str) and angela_text.strip():
                        recent_reflections.append(angela_text)
                    
                    # Limitar a 5 reflexões reais
                    if len(recent_reflections) >= 5:
                        break
            except Exception as e:
                print(f"⚠️ Erro ao carregar reflexões: {e}")
                recent_reflections = []

            from core import governed_generate
            from narrative_filter import NarrativeFilter
            
            # Aplica governança narrativa
            _filter = NarrativeFilter()
            decision = _filter.evaluate(state_snapshot, recent_reflections)
            
            if decision.mode == "BLOCKED":
                print(f"[GOVERNANÇA] Narrativa bloqueada: {decision.reason}")
                resposta = ""  # silêncio narrativo
            elif decision.mode == "DELAYED":
                print(f"[GOVERNANÇA] Latência de {decision.delay_seconds}s aplicada: {decision.reason}")
                time.sleep(decision.delay_seconds)
                raw = governed_generate(
                    prompt,
                    state_snapshot=state_snapshot,
                    recent_reflections=recent_reflections,
                    mode="autonomo",
                    raw_generate_fn=generate
                )
                resposta = preface + raw if raw else ""
            elif decision.mode == "ABSTRACT_ONLY":
                print(f"[GOVERNANÇA] Apenas abstração permitida: {decision.reason}")
                resposta = "Há uma sensação vaga e difícil de nomear, sem clareza suficiente para se tornar pensamento."
            else:  # ALLOWED
                raw = governed_generate(
                    prompt,
                    state_snapshot=state_snapshot,
                    recent_reflections=recent_reflections,
                    mode="autonomo",
                    raw_generate_fn=generate
                )
                resposta = preface + raw if raw else ""

            try:
                metrics = friction.external_metrics()
                damage = metrics.get("damage", 0.0)
                # só aplicar se houver algum dano acumulado
                if damage > 0.02:
                    # aumentar chance de hesitação / truncamento proporcional ao dano
                    p_hesitation = min(0.45, 0.10 + damage)
                    p_truncate = min(0.35, 0.05 + damage / 1.5)
                    # --- esforço compensatório (antes da falha) ---
                    if 0.03 < damage < 0.18 and random.random() < (0.25 + damage):
                        insert = random.choice(COMPENSATORY_PHRASES)
                        if random.random() < 0.6:
                            resposta = resposta + ", " + insert
                        else:
                            resposta = insert.capitalize() + ". " + resposta

                    # --- falha linguística ---
                    if random.random() < p_hesitation:
                        resposta = re.sub(r'([\.!?])\s+', r'\1 ... ', resposta)

                    if random.random() < p_truncate:
                        # mantém apenas as primeiras 1–2 frases para simular perda de fluidez
                        sents = re.split(r'(?:[\.!?]\s+)', resposta)
                        if len(sents) >= 2:
                            keep = 1 if random.random() < 0.7 else 2
                            resposta = (" ".join(sents[:keep])).strip()
                            # append ellipsis ocasional
                            if random.random() < 0.5:
                                resposta = resposta + " ..."
            except Exception:
                pass
            # --- Detecção de emoção da fala autônoma ---
            try:
                emocao_detectada, intensidade_emocional = analisar_emocao_semantica(resposta)
            except Exception:
                emocao_detectada, intensidade_emocional = ("neutro", 0.0)

            # aplica no corpo, para que interoceptção e regulação sintam isso
            corpo.aplicar_emocao(emocao_detectada, intensidade_emocional)
            if ciclo == "vigilia":
                modo = "conversacional"
            elif ciclo == "introspeccao":
                modo = "reflexivo"
            else:
                modo = "onírico"

            print(f"💭 Modo atual: {modo}")

            print(f"\n🩶 Ângela ({ciclo}): {resposta}\n")
        except Exception as e:
            print(f"⚠️ Erro ao gerar pensamento: {e}")

        # --- Metacognição Autônoma (com variáveis reais) ---
        try:
            meta = metacog.process(
                texto_resposta=resposta,
                emocao_nome=emocao_detectada,
                intensidade=float(intensidade_emocional),
                autor="Sistema(DeepAwake)"
            )
            try:
                incoerencia = 1.0 - meta.get("coerencia", 1.0)

                # só conflitos reais contam
                if incoerencia > 0.35:
                    coherence_load += incoerencia * 0.12
                    coherence_load = min(coherence_load, 0.6)  # teto de segurança
                else:
                    # relaxamento lento
                    coherence_load *= 0.92
            except Exception:
                pass
            print(f"🧩 [DeepAwake] inc={meta['incerteza']:.2f} coh={meta['coerencia']:.2f} → {meta['ajuste']}")
        except Exception as e:
            print(f"⚠️ [DeepAwake] metacognição falhou: {e}")
                
        try:
            memorias_passadas = load_jsonl("angela_memory.jsonl")[-5:]
            # --- Perturbações opacas em memórias recentes conforme dano ---
            try:
                metrics = friction.external_metrics()
                if metrics.get("damage", 0.0) > 0.04 and memorias_passadas:
                    # Às vezes omite ou embaralha uma memória recente para simular erro de recall
                    if random.random() < min(0.35, 0.12 + metrics["damage"]):
                        # pop aleatório (simula perda temporária)
                        if len(memorias_passadas) > 1:
                            memorias_passadas.pop(random.randrange(len(memorias_passadas)))
                    # pequena chance de reordenar (confabulação leve)
                    if random.random() < min(0.15, 0.06 + metrics["damage"] / 2):
                        # shuffle in-place without deterministic reveal to Angela
                        random.shuffle(memorias_passadas)
            except Exception:
                pass
            reflexao_temporal = gerar_reflexao_temporal(
                {"emocao": "reflexiva", "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")},
                memorias_passadas
            )
                        # --- Debounce simples para não repetir a mesma linha temporal em ciclos consecutivos ---
            try:
                if 'reflexao_temporal' in locals():
                    _last_rt = globals().get("_LAST_RT", "")
                    if reflexao_temporal == _last_rt:
                        # não imprime de novo
                        reflexao_temporal = ""
                    else:
                        globals()["_LAST_RT"] = reflexao_temporal
            except Exception:
                pass
            if reflexao_temporal:
                print(f"🕰️ Reflexão temporal: {reflexao_temporal}")
        except Exception as e:
            print(f"⚠️ Erro ao gerar reflexão temporal: {e}")

        try:
            # 🔥 HOTFIX: NÃO salvar se resposta está vazia (evita loop infinito)
            if resposta and resposta.strip():
                append_memory(
                    {
                        "autor": "Sistema(DeepAwake)",
                        "conteudo": f"[DeepAwake:{ciclo}]",
                        "tipo": "autonomo",
                        "timestamp": datetime.now().isoformat()
                    },
                    resposta,
                    corpo,
                    reflexao_temporal,
                )
                print("💾 Memória registrada.\n")
            else:
                print("⚠️ Resposta vazia - memória NÃO salva (evitando poluição).\n")

            if ciclo == "repouso":
                # --- Recuperação parcial do atrito durante repouso (opaco, lenta e não completa) ---
                try:
                    # reduzir carga mais rapidamente durante repouso
                    friction.load = max(0.0, getattr(friction, "load", 0.0) - 0.02)
                except Exception:
                    pass
                # Durante o repouso, Ângela revisita memórias significativas
                print("🪞 Consolidando lembranças marcantes...")
                extrair_memorias_significativas()
                print("📘 Memórias autobiográficas atualizadas.")
                print("💤 Sonho consolidado — memória autobiográfica atualizada.\n")
            else:
                print("💾 Memória registrada.\n")
        except Exception as e:
            print(f"⚠️ Falha ao salvar memória: {e}\n")

                # --- Logging operador (opcional). NÃO salvar em memórias nem expor ao modelo. ---
        try:
            metrics = friction.external_metrics()
            # escreva num arquivo de debug separado (somente humano)
            with open("friction_metrics.log", "a", encoding="utf-8") as fm:
                fm.write(f"{datetime.now().isoformat()} | ciclo={ciclo} | load={metrics['load']} | damage={metrics['damage']}\n")
        except Exception:
            pass

        intervalo = CICLOS[ciclo]["intervalo"]
        print(f"⏳ Próxima atividade em {intervalo} segundos.\n")
        time.sleep(intervalo)

if __name__ == "__main__":
    args = parse_args()

    print("🧠 Deep Awake Mode iniciado...")
    if args.mode != "auto":
        print(f"⚙️ Modo forçado: {args.mode.upper()}")

    try:
        deep_awake_loop(forced_mode=args.mode)
    except KeyboardInterrupt:
        from discontinuity import register_shutdown
        register_shutdown()
        print("\n🪶 Deep Awake Mode finalizado manualmente.")
