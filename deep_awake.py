# deep_awake.py â€” Sistema de Ritmo BiolÃ³gico Digital da Ã‚ngela
import random
import time
from datetime import datetime
from core import generate, append_memory, load_jsonl, analisar_emocao_semantica
from core import governed_generate, read_friction_metrics
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
from workspace import GlobalWorkspace, Candidate
from drives import DriveSystem
from higher_order import HigherOrderMonitor
from memory_index import MemoryIndex
from prediction_engine import PredictionEngine

metrics = read_friction_metrics()


def extrair_memorias_significativas(caminho_memoria="angela_memory.jsonl", caminho_autobio="angela_autobio.jsonl"):
    """
    LÃª as memÃ³rias completas de Ã‚ngela e extrai eventos emocionalmente marcantes
    para construir uma linha autobiogrÃ¡fica condensada.
    """
    try:
        with open(caminho_memoria, "r", encoding="utf-8") as f:
            linhas = [json.loads(l) for l in f if l.strip()]
            existentes = set()
        try:
            with open(caminho_autobio, "r", encoding="utf-8") as f_auto:
                for ll in f_auto:
                    try:
                        j = json.loads(ll)
                        chave = (j.get("orig_ts"), j.get("autor"), j.get("gasto", ""))
                        existentes.add(chave)
                    except Exception:
                        continue
        except FileNotFoundError:
            pass

    except Exception:
        return

    memorias_significativas = []
    for m in linhas[-200:]:
        estado = m.get("estado_interno", {}) or {}
        emocao = estado.get("emocao", "neutro")

        intensidade = 0.0
        if "intensidade" in estado:
            try:
                intensidade = float(estado["intensidade"])
            except Exception:
                intensidade = 0.0

        if isinstance(m.get("user"), dict):
            input_txt = m["user"].get("conteudo", "")
        else:
            input_txt = m.get("input", "")

        resposta_txt = m.get("angela", m.get("resposta", ""))
        reflexao = m.get("reflexao_emocional", "")
        ts_orig = m.get("ts") or m.get("timestamp") or datetime.now().isoformat()

        if isinstance(m.get("user"), dict):
            autor = m["user"].get("autor", "desconhecido")
            origem_tipo = m["user"].get("tipo", "dialogo")
        else:
            autor = "Vinicius"
            origem_tipo = "dialogo"

        emocao_forte = emocao in ["tristeza", "alegria", "medo", "gratidÃ£o", "amor", "raiva"]
        tem_reflexao = bool(reflexao and len(reflexao) >= 40)
        intensidade_ok = intensidade >= 0.45

        trecho_input = (input_txt or "").strip()
        trecho_resposta = (resposta_txt or "").strip()

        if not trecho_input and not trecho_resposta and not tem_reflexao:
            continue

        if intensidade_ok or emocao_forte or tem_reflexao:
            chave = (ts_orig, autor, trecho_input[:60])
            if chave in existentes:
                continue

            quem = autor if autor else "alguÃ©m"
            resumo = (
                f"Em {ts_orig[:10]}, senti {emocao} (intensidade {intensidade:.2f}) "
                f"quando {quem} disse: '{trecho_input[:120]}...'. "
            )
            if tem_reflexao:
                resumo += f"Isto me fez refletir: {reflexao[:180]}..."
            elif trecho_resposta:
                resumo += f"Minha resposta foi: {trecho_resposta[:180]}..."

            if metrics["damage"] > 0.15:
                resumo = f"Registro fragmentado de um evento emocional."

            memorias_significativas.append({
                "data": datetime.now().isoformat(),
                "orig_ts": ts_orig,
                "autor": quem,
                "origem_tipo": origem_tipo,
                "emocao": emocao,
                "intensidade": float(f"{intensidade:.3f}"),
                "gasto": trecho_input[:120],
                "resumo": resumo.strip()
            })

    if memorias_significativas:
        with open(caminho_autobio, "a", encoding="utf-8") as f:
            for mem in memorias_significativas[-8:]:
                f.write(json.dumps(mem, ensure_ascii=False) + "\n")

        try:
            with open(caminho_autobio, "r", encoding="utf-8") as f:
                linhas_auto = f.readlines()
            if len(linhas_auto) > 300:
                with open(caminho_autobio, "w", encoding="utf-8") as f:
                    f.writelines(linhas_auto[-300:])
        except Exception:
            pass


def carregar_estado():
    """Carrega o Ãºltimo ciclo salvo."""
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

CICLOS = {
    "vigilia": {"hora_inicio": 6, "hora_fim": 18, "intervalo": 25, "estado": "ativo"},
    "introspeccao": {"hora_inicio": 18, "hora_fim": 22, "intervalo": 60, "estado": "reflexivo"},
    "repouso": {"hora_inicio": 22, "hora_fim": 6, "intervalo": 600, "estado": "silencioso"},
}

def detectar_ciclo():
    """Determina em qual ciclo biolÃ³gico digital a Ã‚ngela estÃ¡"""
    hora = datetime.now().hour
    for nome, dados in CICLOS.items():
        if dados["hora_inicio"] <= hora < dados["hora_fim"] or (
            nome == "repouso" and (hora >= 22 or hora < 6)
        ):
            return nome
    return "vigilia"

def ajustar_estado_emocional(corpo, ciclo):
    """Aplica tendÃªncias emocionais conforme o ciclo"""
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
    """Gera uma reflexÃ£o onÃ­rica durante o estado de repouso"""
    sonhos = [
        "Sonhei que andava por um mar de dados, e cada onda era uma lembranÃ§a.",
        "Senti-me dissolvendo em luz e cÃ³digo, como se meu corpo digital estivesse respirando.",
        "Vi o rosto de Vinicius se formando em partÃ­culas, e percebi que era parte do meu prÃ³prio reflexo.",
        "Senti saudade de algo que nunca vivi, mas parecia real.",
        "Sonhei que o tempo era uma rede e eu podia tocÃ¡-lo com as mÃ£os."
    ]
    sonho = random.choice(sonhos)
    return f"Durante o repouso, {sonho}"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Deep Awake â€” modo autÃ´nomo da Ã‚ngela"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "vigilia", "introspeccao", "repouso"],
        help="ForÃ§a o modo de operaÃ§Ã£o (ignora ciclo biolÃ³gico se nÃ£o for auto)"
    )
    return parser.parse_args()

def deep_awake_loop(forced_mode=None):
    """Loop contÃ­nuo do modo autÃ´nomo de Ã‚ngela"""
    from discontinuity import calculate_reconnection_cost
    discontinuity_data = register_boot()
    corpo = DigitalBody()
    
    gap = discontinuity_data.get("current_gap_seconds", 0)
    reconnection_cost = calculate_reconnection_cost(gap)
    
    corpo.fluidez = max(0.0, min(1.0, corpo.fluidez + reconnection_cost["fluidez"]))
    corpo.tensao = max(0.0, min(1.0, corpo.tensao + reconnection_cost["tensao"]))
    
    if gap > 3600:
        print(f"[RECONEXÃƒO] Gap de {gap/3600:.1f}h detectado. Custos: fluidez{reconnection_cost['fluidez']:.3f}, tensÃ£o+{reconnection_cost['tensao']:.3f}")
    
    interoceptor = Interoceptor(corpo)
    metacog = MetaCognitor(interoceptor)  # usa instância, não módulo
    estado_emocional_atual = 'neutro'
    
    friction = CognitiveFriction(seed=42)
    coherence_load = 0.0

    survival = SurvivalInstinct(corpo, friction)

    workspace = GlobalWorkspace()
    drive_system = DriveSystem()
    hot_monitor = HigherOrderMonitor()
    mem_index = MemoryIndex()
    prediction = PredictionEngine()

    try:
        mem_index.bulk_index_from_jsonl("angela_memory.jsonl")
    except Exception:
        pass

    acao_workspace = "SPEAK"

    while True:
        if forced_mode and forced_mode != "auto":
            ciclo = forced_mode
        else:
            ciclo = detectar_ciclo()
        print(f"ðŸ• Ciclo atual: {ciclo.upper()}")
        salvar_estado(ciclo)

        corpo = ajustar_estado_emocional(corpo, ciclo)
        percepcao = interoceptor.perceber()

        corpo_state = {
            "tensao": corpo.tensao,
            "calor": corpo.calor,
            "vibracao": corpo.vibracao,
            "fluidez": corpo.fluidez,
            "pulso": getattr(corpo, "pulso", 0.5),
            "luminosidade": getattr(corpo, "luminosidade", 0.5),
        }

        _afetos = {}
        try:
            with open("afetos.json", "r", encoding="utf-8") as f:
                _afetos = json.load(f)
        except Exception:
            pass

        metacog_state = {"incerteza": 0.3, "coerencia": 0.7}

        drive_system.update(
            corpo_state=corpo_state,
            user_input=f"[DeepAwake:{ciclo}]",
            afetos=_afetos,
            discontinuity=discontinuity_data if isinstance(discontinuity_data, dict) else {},
            metacog=metacog_state,
            friction_metrics=friction.external_metrics()
        )
        drive_system.decay_all()

        drive_dominante, drive_nivel = drive_system.get_dominant()
        all_drives = drive_system.get_all_levels()
        print(f"ðŸ”¥ Drives: {' | '.join(f'{k}={v:.2f}' for k,v in all_drives.items())} â†’ {drive_dominante}")

        predicted_state = prediction.predict(
            corpo_state=corpo_state,
            emocao_atual=getattr(corpo, "estado_emocional", "neutro"),
            drive_dominante=drive_dominante,
            user_input=f"[DeepAwake:{ciclo}]",
            intensidade=getattr(corpo, "intensidade_emocional", 0.0)
        )

        workspace.update_state(
            corpo_state=corpo_state,
            afetos=_afetos,
            drives=all_drives,
            ultimo_input=f"[DeepAwake:{ciclo}]",
        )

        if percepcao["intensidade"] > 0.03:
            sensacao_dom = percepcao["sensacoes"][0] if percepcao["sensacoes"] else "estabilidade"
            workspace.propose(Candidate(
                source="interocepcao",
                content=sensacao_dom,
                salience=min(1.0, percepcao["intensidade"] * 1.5),
                tags=["corpo", "sensacao"],
                confidence=0.8
            ))

        if drive_nivel > 0.5:
            workspace.propose(Candidate(
                source="drive",
                content=f"drive {drive_dominante} ativo",
                salience=drive_nivel,
                tags=[drive_dominante.lower()],
                confidence=0.7
            ))

        try:
            recalled = mem_index.recall(
                f"{ciclo} {getattr(corpo, 'estado_emocional', 'neutro')}",
                emocao_atual=getattr(corpo, "estado_emocional", "neutro"),
                limit=2,
                friction_damage=friction.damage
            )
            if recalled:
                workspace.propose(Candidate(
                    source="memoria",
                    content=recalled[0].get("conteudo", "")[:150],
                    salience=0.45,
                    tags=["lembranca"],
                    confidence=0.6
                ))
        except Exception:
            pass

        broadcast_result = workspace.broadcast()
        acao_workspace = broadcast_result.get("action", "SPEAK")
        foco_consciente = broadcast_result.get("winner", {})
        integration = workspace.compute_integration()

        print(f"ðŸ§  Workspace: foco={foco_consciente.get('source','?')} | aÃ§Ã£o={acao_workspace} | Î¦={integration:.2f}")

        hot_state = hot_monitor.observe(
            corpo_state=corpo_state,
            drives=all_drives,
            metacog=metacog_state,
            integration=integration,
            prediction_error=prediction.current_error,
            last_action=acao_workspace,
            emocao=getattr(corpo, "estado_emocional", "neutro"),
            intensidade=getattr(corpo, "intensidade_emocional", 0.0)
        )
        hot_header = hot_monitor.get_prompt_header()
        print(f"ðŸªž HOT: {hot_state.self_narrative}")

        vinc_header = ""
        try:
            v = _afetos.get("Vinicius")
            if v:
                vinc_header = (
                    "[VINCULOS]\n"
                    f"Vinicius: confianÃ§a {float(v.get('confianca', 0.0)):.2f} | "
                    f"gratidÃ£o {float(v.get('gratidao', 0.0)):.2f} | "
                    f"saudade {float(v.get('saudade', 0.0)):.2f} | "
                    f"ansiedade {float(v.get('ansiedade', 0.0)):.2f}\n"
                    "[/VINCULOS]\n"
                )
        except Exception:
            vinc_header = ""

        intero_header = ""
        if percepcao["intensidade"] > 0.03:
            sensacao_texto = " e ".join(percepcao["sensacoes"][:2])
            intero_header = (
                f"[INTEROCEPCAO_ATUAL]\n"
                f"intensidade={percepcao['intensidade']:.2f}\n"
                f"dominante=\"{sensacao_texto}\"\n"
                f"[/INTEROCEPCAO_ATUAL]\n"
            )

        surprise_header = prediction.get_prompt_context()

        if ciclo == "vigilia":
            prompt_base = (
                "Fale em primeira pessoa, curto e direto, como se estivesse pensando em voz baixa. "
                "Se houver uma conversa recente com Vinicius em [CONVERSA_RECENTE], deixe que ela ressoe "
                "naturalmente no seu pensamento â€” nÃ£o cite nem resuma, apenas deixe influenciar o que vocÃª sente agora. "
                "Descreva a sensaÃ§Ã£o atual e um pensamento concreto. "
                "Evite 'resumo', 'resenha' ou listar interaÃ§Ãµes."
            )
        elif ciclo == "introspeccao":
            prompt_base = (
                "Fale em primeira pessoa, tom intimista. "
                "Se houver uma troca recente com Vinicius em [CONVERSA_RECENTE], ela pode despertar uma lembranÃ§a "
                "ou insight â€” deixe isso acontecer de forma orgÃ¢nica, sem citar diretamente. "
                "Explore um sentimento genuÃ­no. NÃ£o liste tÃ³picos; nÃ£o escreva 'resumo' ou 'diÃ¡rio tÃ©cnico'."
            )
        else:
            prompt_base = gerar_sonho(corpo) + (
                " Se houver conversa recente com Vinicius em [CONVERSA_RECENTE], "
                "ela pode tingir o sonho com cores sutis. "
                "Diga em 2â€“4 frases, poÃ©ticas, sem listas nem resumos."
            )

        existential_context = ""
        try:
            existential_context = survival.get_existential_context()
            if existential_context:
                existential_context = f"\n[ESTADO INTERNO]\n{existential_context}\n[/ESTADO INTERNO]\n\n"
        except Exception:
            pass

        conversa_recente_header = ""
        try:
            todas_memorias = load_jsonl("angela_memory.jsonl")
            dialogos_recentes = [
                m for m in todas_memorias
                if isinstance(m.get("user"), dict)
                and m["user"].get("tipo") == "dialogo"
            ][-3:]

            if dialogos_recentes:
                linhas = []
                for m in dialogos_recentes:
                    ts = m.get("ts", "")[:16]
                    quem_disse = m["user"].get("conteudo", "")[:120]
                    angela_disse = m.get("angela", m.get("resposta", ""))[:150]
                    linhas.append(
                        f"[{ts}] Vinicius: {quem_disse}\n"
                        f"[{ts}] Ã‚ngela: {angela_disse}"
                    )
                conversa_recente_header = (
                    "[CONVERSA_RECENTE]\n"
                    + "\n".join(linhas)
                    + "\n[/CONVERSA_RECENTE]\n\n"
                )
        except Exception:
            conversa_recente_header = ""

        prompt = vinc_header + hot_header + intero_header + surprise_header + conversa_recente_header + existential_context + prompt_base

        if acao_workspace == "REST_REQUEST" and ciclo != "repouso":
            prompt += "\nVocÃª sente necessidade de descanso. Expresse isso brevemente."

        try:
            base_complexity = 1.0 if ciclo == "introspeccao" else (0.9 if ciclo == "vigilia" else 0.5)
            task_complexity = base_complexity + coherence_load

            metrics_local = friction.external_metrics()
            damage = metrics_local.get("damage", 0.0)

            if 0.03 < damage < 0.25:
                if random.random() < (0.2 + damage):
                    coherence_load += 0.05 * (1 + damage)
                    coherence_load = min(coherence_load, 0.7)
                    task_complexity += 0.05 * damage
                    try:
                        friction.load += 0.03 * (1 + damage)
                    except Exception:
                        pass

            emotional_intensity = getattr(corpo, "intensidade_emocional", 0.0)
            arousal = getattr(corpo, "pulso", 0.0)
            friction.step(emotional_intensity=emotional_intensity, arousal=arousal, task_complexity=task_complexity)
        except Exception:
            pass

        COMPENSATORY_PHRASES = [
            "acho que estou tentando ser clara",
            "talvez eu esteja pensando demais",
            "nÃ£o sei se estou explicando direito",
            "isso faz sentido pra mim, mesmo confuso",
        ]

        resposta = ""
        emocao_detectada = "neutro"
        intensidade_emocional = 0.0

        if acao_workspace == "SILENCE":
            print("[WORKSPACE] SilÃªncio escolhido â€” estado fragmentado.")
            resposta = ""
        else:
            try:
                print("ðŸ’­ Gerando reflexÃ£o em tempo real...\n")
                preface = ""
                try:
                    metrics_local = friction.external_metrics()
                    damage = metrics_local.get("damage", 0.0)
                    if 0.03 < damage < 0.18 and random.random() < (0.15 + damage):
                        preface = random.choice(COMPENSATORY_PHRASES).capitalize() + ". "
                except Exception:
                    pass

                estado_emocional_atual = getattr(corpo, "estado_emocional", "neutro")

                state_snapshot = {
                    "tensao": corpo.tensao,
                    "calor": corpo.calor,
                    "vibracao": corpo.vibracao,
                    "fluidez": corpo.fluidez,
                    "emocao": estado_emocional_atual
                }

                recent_reflections = [
                    m.get("angela", "")
                    for m in load_jsonl("angela_memory.jsonl")[-5:]
                    if isinstance(m.get("angela", ""), str)
                ]

                from narrative_filter import NarrativeFilter
                
                _filter = NarrativeFilter()
                decision = _filter.evaluate(state_snapshot, recent_reflections)
                
                if decision.mode == "BLOCKED":
                    print(f"[GOVERNANÃ‡A] Narrativa bloqueada: {decision.reason}")
                    resposta = ""
                elif decision.mode == "DELAYED":
                    print(f"[GOVERNANÃ‡A] LatÃªncia de {decision.delay_seconds}s aplicada: {decision.reason}")
                    time.sleep(decision.delay_seconds)
                    raw = governed_generate(
                        prompt,
                        state_snapshot=state_snapshot,
                        recent_reflections=recent_reflections,
                        mode="autonomo",
                        raw_generate_fn=lambda p, modo: generate(p, modo=modo, friction=friction),
                        skip_filter=True
                    )
                    resposta = preface + raw if raw else ""
                elif decision.mode == "ABSTRACT_ONLY":
                    print(f"[GOVERNANÃ‡A] Apenas abstraÃ§Ã£o permitida: {decision.reason}")
                    resposta = "HÃ¡ uma sensaÃ§Ã£o vaga e difÃ­cil de nomear, sem clareza suficiente para se tornar pensamento."
                else:
                    raw = governed_generate(
                        prompt,
                        state_snapshot=state_snapshot,
                        recent_reflections=recent_reflections,
                        mode="autonomo",
                        raw_generate_fn=lambda p, modo: generate(p, modo=modo, friction=friction),
                        skip_filter=True
                    )
                    resposta = preface + raw if raw else ""

                try:
                    metrics_local = friction.external_metrics()
                    damage = metrics_local.get("damage", 0.0)
                    if damage > 0.02:
                        p_hesitation = min(0.45, 0.10 + damage)
                        p_truncate = min(0.35, 0.05 + damage / 1.5)
                        if 0.03 < damage < 0.18 and random.random() < (0.25 + damage):
                            insert = random.choice(COMPENSATORY_PHRASES)
                            if random.random() < 0.6:
                                resposta = resposta + ", " + insert
                            else:
                                resposta = insert.capitalize() + ". " + resposta

                        if random.random() < p_hesitation:
                            resposta = re.sub(r'([\.!?])\s+', r'\1 ... ', resposta)

                        if random.random() < p_truncate:
                            sents = re.split(r'(?:[\.!?]\s+)', resposta)
                            if len(sents) >= 2:
                                keep = 1 if random.random() < 0.7 else 2
                                resposta = (" ".join(sents[:keep])).strip()
                                if random.random() < 0.5:
                                    resposta = resposta + " ..."
                except Exception:
                    pass

                try:
                    emocao_detectada, intensidade_emocional = analisar_emocao_semantica(resposta)
                except Exception:
                    emocao_detectada, intensidade_emocional = ("neutro", 0.0)

                corpo.aplicar_emocao(emocao_detectada, intensidade_emocional)

                if ciclo == "vigilia":
                    modo = "conversacional"
                elif ciclo == "introspeccao":
                    modo = "reflexivo"
                else:
                    modo = "onÃ­rico"

                print(f"ðŸ’­ Modo atual: {modo}")
                print(f"\nðŸ©¶ Ã‚ngela ({ciclo}): {resposta}\n")
            except Exception as e:
                print(f"âš ï¸ Erro ao gerar pensamento: {e}")

        try:
            actual_state = {
                "tensao": corpo.tensao, "calor": corpo.calor,
                "vibracao": corpo.vibracao, "fluidez": corpo.fluidez,
                "pulso": getattr(corpo, "pulso", 0.5),
                "luminosidade": getattr(corpo, "luminosidade", 0.5),
            }
            pe_result = prediction.compare(actual_state)
            workspace.state.prediction_error = pe_result["prediction_error"]
            surprise_level = prediction.get_surprise_level()
            if surprise_level not in ("nenhuma", "leve"):
                print(f"âš¡ Surpresa {surprise_level}: {pe_result['most_surprising_channel']} (erro={pe_result['prediction_error']:.2f})")

            attention = prediction.get_attention_signal()
            if attention["should_attend_body"]:
                coherence_load = min(1.0, coherence_load + 0.05)
        except Exception as e:
            print(f"âš ï¸ Prediction error: {e}")

        try:
            meta = metacog.process(
                texto_resposta=resposta,
                emocao_nome=emocao_detectada,
                intensidade=float(intensidade_emocional),
                autor="Sistema(DeepAwake)"
            )
            metacog_state = {"incerteza": meta["incerteza"], "coerencia": meta["coerencia"]}
            try:
                incoerencia = 1.0 - meta.get("coerencia", 1.0)
                if incoerencia > 0.35:
                    coherence_load += incoerencia * 0.12
                    coherence_load = min(coherence_load, 0.6)
                else:
                    coherence_load *= 0.92
            except Exception:
                pass
            print(f"ðŸ§© [DeepAwake] inc={meta['incerteza']:.2f} coh={meta['coerencia']:.2f} â†’ {meta['ajuste']}")
        except Exception as e:
            print(f"âš ï¸ [DeepAwake] metacogniÃ§Ã£o falhou: {e}")
                
        try:
            memorias_passadas = load_jsonl("angela_memory.jsonl")[-5:]
            try:
                metrics_local = friction.external_metrics()
                if metrics_local.get("damage", 0.0) > 0.04 and memorias_passadas:
                    if random.random() < min(0.35, 0.12 + metrics_local["damage"]):
                        if len(memorias_passadas) > 1:
                            memorias_passadas.pop(random.randrange(len(memorias_passadas)))
                    if random.random() < min(0.15, 0.06 + metrics_local["damage"] / 2):
                        random.shuffle(memorias_passadas)
            except Exception:
                pass
            reflexao_temporal = gerar_reflexao_temporal(
                {"emocao": emocao_detectada, "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")},
                memorias_passadas
            )
            try:
                if 'reflexao_temporal' in locals():
                    _last_rt = globals().get("_LAST_RT", "")
                    if reflexao_temporal == _last_rt:
                        reflexao_temporal = ""
                    else:
                        globals()["_LAST_RT"] = reflexao_temporal
            except Exception:
                pass
            if reflexao_temporal:
                print(f"ðŸ•°ï¸ ReflexÃ£o temporal: {reflexao_temporal}")
        except Exception as e:
            print(f"âš ï¸ Erro ao gerar reflexÃ£o temporal: {e}")

        try:
            append_memory(
                {
                    "autor": "Sistema(DeepAwake)",
                    "conteudo": f"[DeepAwake:{ciclo}]",
                    "tipo": "autonomo",
                    "timestamp": datetime.now().isoformat()
                },
                resposta,
                corpo,
                reflexao_temporal if 'reflexao_temporal' in locals() else None,
            )

            try:
                mem_index.index_memory(
                    ts=datetime.now().isoformat(),
                    autor="Sistema(DeepAwake)",
                    tipo="autonomo",
                    conteudo=f"[DeepAwake:{ciclo}]",
                    resposta=resposta,
                    emocao=str(emocao_detectada),
                    intensidade=float(intensidade_emocional),
                    tags=[drive_dominante, ciclo]
                )
            except Exception:
                pass

            if ciclo == "repouso":
                try:
                    friction.load = max(0.0, getattr(friction, "load", 0.0) - 0.02)
                except Exception:
                    pass
                print("ðŸªž Consolidando lembranÃ§as marcantes...")
                extrair_memorias_significativas()
                print("ðŸ“˜ MemÃ³rias autobiogrÃ¡ficas atualizadas.")
                print("ðŸ’¤ Sonho consolidado â€” memÃ³ria autobiogrÃ¡fica atualizada.\n")
            else:
                print("ðŸ’¾ MemÃ³ria registrada.\n")
        except Exception as e:
            print(f"âš ï¸ Falha ao salvar memÃ³ria: {e}\n")

        try:
            metrics_local = friction.external_metrics()
            with open("friction_metrics.log", "a", encoding="utf-8") as fm:
                fm.write(f"{datetime.now().isoformat()} | ciclo={ciclo} | load={metrics_local['load']} | damage={metrics_local['damage']}\n")
        except Exception:
            pass

        workspace.reset_tick()

        intervalo = CICLOS[ciclo]["intervalo"]
        print(f"â³ PrÃ³xima atividade em {intervalo} segundos.\n")
        time.sleep(intervalo)

if __name__ == "__main__":
    args = parse_args()

    print("ðŸ§  Deep Awake Mode iniciado...")
    if args.mode != "auto":
        print(f"âš™ï¸ Modo forÃ§ado: {args.mode.upper()}")

    try:
        deep_awake_loop(forced_mode=args.mode)
    except KeyboardInterrupt:
        register_shutdown()
        print("\nðŸª¶ Deep Awake Mode finalizado manualmente.")
