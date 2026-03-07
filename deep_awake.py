# deep_awake.py — Sistema de Ritmo Biológico Digital da Ângela
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
from theory_of_mind import TheoryOfMindModule
from workspace import GlobalWorkspace, Candidate
from drives import DriveSystem
from higher_order import HigherOrderMonitor
from memory_index import MemoryIndex
from prediction_engine import PredictionEngine
from self_evolution import SelfEvolution
from attention_schema import AttentionSchema
from sleep_consolidation import run_sleep_cycle
from exteroception import Exteroceptor
from actions import ActionManager
from policy_bandit import PolicyBandit
from objective_pressures import ObjectivePressures
from metrics_logger import log_event
import signal

# Referência global ao MemoryIndex para checkpoint no SIGINT/SIGTERM
_mem_index_global: "MemoryIndex | None" = None

def _shutdown_handler(signum, frame):
    """Faz WAL checkpoint antes de sair — evita corrupção por Ctrl+C."""
    global _mem_index_global
    if _mem_index_global is not None:
        try:
            _mem_index_global.close()
        except Exception:
            pass
    from discontinuity import register_shutdown
    try:
        register_shutdown()
    except Exception:
        pass
    print("\n🟢 Deep Awake Mode finalizado (checkpoint WAL OK).")
    raise SystemExit(0)

signal.signal(signal.SIGINT,  _shutdown_handler)
signal.signal(signal.SIGTERM, _shutdown_handler)


metrics = read_friction_metrics()



# ═══════════════════════════════════════════════════════════════
# FIX #2: ABSTRAÇÕES VARIADAS (não hardcoded)
# ═══════════════════════════════════════════════════════════════

ABSTRACT_PHRASES = [
    "Há uma sensação vaga e difícil de nomear",
    "Percebo algo que não consigo articular claramente",
    "Existe um estado interno que escapa às palavras",
    "Sinto uma nuance que ainda não encontrou forma",
    "Há uma textura emocional que permanece indefinida",
]

def gerar_abstracao_variada():
    """
    Gera descrição abstrata variada (não sempre a mesma string).
    FIX #2: Evita repetição literal de abstrações idênticas.
    """
    base = random.choice(ABSTRACT_PHRASES)
    qualificadores = [
        ", sem clareza suficiente para se tornar pensamento",
        ", como um sussurro que não alcança a superfície",
        ", uma vibração que não se resolve em forma",
        ", presente mas não nomeável",
        ", algo que observo mas não compreendo totalmente",
    ]
    return base + random.choice(qualificadores) + "."

# ═══════════════════════════════════════════════════════════════
# FIX #3: FRASES COMPENSATÓRIAS (para damage moderado)
# ═══════════════════════════════════════════════════════════════

COMPENSATORY_PHRASES = [
    "acho que estou tentando ser clara",
    "talvez eu esteja pensando demais",
    "não sei se estou explicando direito",
    "isso faz sentido pra mim, mesmo confuso",
]

def extrair_memorias_significativas(caminho_memoria="angela_memory.jsonl", caminho_autobio="angela_autobio.jsonl"):
    """
    Lê as memórias completas de Angela e extrai eventos emocionalmente marcantes
    para construir uma linha autobiográfica condensada.
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

        emocao_forte = emocao in ["tristeza", "alegria", "medo", "gratidão", "gratidao", "amor", "raiva"]
        tem_reflexao = bool(reflexao and len(reflexao) >= 40)
        intensidade_ok = intensidade >= 0.45

        trecho_input = (input_txt or "").strip()
        trecho_resposta = (resposta_txt or "").strip()

        if not trecho_input and not trecho_resposta and not tem_reflexao:
            continue

        if intensidade_ok or emocao_forte or tem_reflexao:
            # Chave robusta para evitar duplicação
            import hashlib
            hash_input = hashlib.md5(trecho_input.encode()).hexdigest()[:8]
            chave = (ts_orig, autor, hash_input)
            if chave in existentes:
                continue

            quem = autor if autor else "alguém"
            resumo = (
                f"Em {ts_orig[:10]}, senti {emocao} (intensidade {intensidade:.2f}) "
                f"quando {quem} disse: '{trecho_input[:120]}...'. "
            )
            if tem_reflexao:
                resumo += f"Isto me fez refletir: {reflexao[:180]}..."
            elif trecho_resposta:
                resumo += f"Minha resposta foi: {trecho_resposta[:180]}..."

            # Dano cognitivo alto → resumo fragmentado (opaco para Angela)
            try:
                from cognitive_friction import get_persistent_metrics
                metrics = get_persistent_metrics()
                if metrics.get("damage", 0) > 0.15:
                    resumo = f"Registro fragmentado de um evento emocional."
            except Exception:
                pass  # metrics não disponível

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
    """Carrega o último ciclo salvo."""
    try:
        with open("angela_state.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"ultimo_ciclo": None, "timestamp": None}

def salvar_estado(ciclo_atual):
    """Salva o ciclo atual com timestamp de forma atômica."""
    from core import atomic_json_write
    estado = {
        "ultimo_ciclo": ciclo_atual,
        "timestamp": datetime.now().isoformat()
    }
    try:
        atomic_json_write("angela_state.json", estado)
    except Exception as e:
        print(f"[DeepAwake] ⚠️ salvar_estado falhou: {e}")

CICLOS = {
    "vigilia": {"hora_inicio": 6, "hora_fim": 18, "intervalo": 25, "estado": "ativo"},
    "introspeccao": {"hora_inicio": 18, "hora_fim": 22, "intervalo": 60, "estado": "reflexivo"},
    "repouso": {"hora_inicio": 22, "hora_fim": 6, "intervalo": 600, "estado": "silencioso"},
}

def detectar_ciclo():
    """Determina em qual ciclo biológico digital a Angela está"""
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



def parse_args():
    parser = argparse.ArgumentParser(
        description="Deep Awake — modo autônomo da Angela"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "vigilia", "introspeccao", "repouso"],
        help="Força o modo de operação (ignora ciclo biológico se não for auto)"
    )
    return parser.parse_args()

def deep_awake_loop(forced_mode=None):
    """Loop contínuo do modo autônomo de Angela"""
    from discontinuity import calculate_reconnection_cost
    discontinuity_data = register_boot()
    corpo = DigitalBody()
    
    gap = discontinuity_data.get("current_gap_seconds", 0)
    reconnection_cost = calculate_reconnection_cost(gap)
    
    corpo.fluidez = max(0.0, min(1.0, corpo.fluidez + reconnection_cost["fluidez"]))
    corpo.tensao  = max(0.0, min(1.0, corpo.tensao  + reconnection_cost["tensao"]))

    if gap > 300:  # > 5 minutos
        desc = reconnection_cost.get("description", f"{gap/3600:.1f}h de ausencia")
        print(f"Reconexao: {desc}")

    # Registra memória de descontinuidade se impacto real (distingue estado fórmula de estado vivido)
    if reconnection_cost.get("gap_injected") and reconnection_cost.get("impact", "nenhum") != "nenhum":
        try:
            from datetime import datetime as _dt_cls
            append_memory(
                {
                    "autor": "Sistema(Discontinuity)",
                    "conteudo": f"[gap={reconnection_cost['gap_hours']}h impacto={reconnection_cost['impact']}]",
                    "tipo": "discontinuidade",
                    "timestamp": _dt_cls.now().isoformat(),
                },
                None,
                corpo,
                None,
                extra={
                    "gap_hours":     reconnection_cost["gap_hours"],
                    "impact":        reconnection_cost["impact"],
                    "delta_fluidez": reconnection_cost["fluidez"],
                    "delta_tensao":  reconnection_cost["tensao"],
                    "origem":        "formula_gap",
                },
            )
        except Exception:
            pass

    interoceptor = Interoceptor(corpo)
    metacog = MetaCognitor(interoceptor)  # usa instÃ¢ncia, nÃ£o mÃ³dulo

    estado_emocional_atual = 'neutro'
    
    friction = CognitiveFriction(seed=None)
    coherence_load = 0.0

    survival = SurvivalInstinct(corpo, friction)

    workspace = GlobalWorkspace()
    drive_system = DriveSystem()
    hot_monitor = HigherOrderMonitor()
    mem_index = MemoryIndex()
    global _mem_index_global
    _mem_index_global = mem_index
    prediction = PredictionEngine()
    self_evolution = SelfEvolution()
    attention_schema = AttentionSchema()
    exteroceptor = Exteroceptor()
    action_manager = ActionManager(friction, corpo)
    policy = PolicyBandit()
    pressures = ObjectivePressures()
    tom = TheoryOfMindModule()  # instanciado uma vez — preserva _last_state acumulado
    if gap > 0:
        attention_schema.apply_reconnection_cost(gap)
    cycle_count = 0
    damage_prev = friction.damage

    # Contador para forçar repouso quando PANIC_GRIEF alto por muitos ciclos
    # Se PANIC_GRIEF > 0.80 por 3+ ciclos sem input humano → força repouso imediato
    _panic_grief_high_count = 0
    _PANIC_GRIEF_THRESHOLD = 0.80
    _PANIC_GRIEF_CYCLES_MAX = 3

    # === INJEÇÃO DE GERADOR LLM ===
    def llm_wrapper(prompt):
        """Wrapper para geração via LLM."""
        try:
            return generate(
                prompt,
                modo="conversacional"
            )
        except Exception:
            return ""

    if hasattr(hot_monitor, 'set_llm_generator'):
        hot_monitor.set_llm_generator(llm_wrapper)
    if hasattr(metacog, 'set_llm_generator'):
        metacog.set_llm_generator(llm_wrapper)
    if hasattr(survival, 'set_llm_generator'):
        survival.set_llm_generator(llm_wrapper)
    # === FIM DA INJEÇÃO ===

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
        print(f"🟢 Ciclo atual: {ciclo.upper()}")
        salvar_estado(ciclo)

        # ── Cache de memórias: lê o arquivo UMA VEZ por ciclo ─────────────
        # Bug B fix: antes o arquivo era aberto 4 vezes separadas por ciclo.
        # Agora carregamos tudo aqui e reutilizamos as variáveis derivadas.
        _todas_memorias_ciclo = []
        try:
            _todas_memorias_ciclo = load_jsonl("angela_memory.jsonl")
        except Exception:
            pass
        _dialogos_ciclo = [
            m for m in _todas_memorias_ciclo
            if isinstance(m.get("user"), dict) and m["user"].get("tipo") == "dialogo"
        ]
        _memorias_recentes_ciclo = _todas_memorias_ciclo[-5:]  # para reflexao_temporal e recent_reflections

        corpo = ajustar_estado_emocional(corpo, ciclo)

        # ── Exteroception: percepção do mundo externo ──────────────────────
        world_state = {}
        mundo_header = ""
        try:
            world_state = exteroceptor.read_world()
            extero_deltas = exteroceptor.apply_to_body(corpo, world_state)
            mundo_header = exteroceptor.get_prompt_header(world_state)
            for drive_name, stimulus, intensity in exteroceptor.get_drive_stimuli(world_state):
                if drive_name in drive_system.drives:
                    drive_system.drives[drive_name].activate(stimulus, intensity)
            if any(abs(v) > 0.01 for v in extero_deltas.values()):
                print(f"🌍 Mundo: {' | '.join(f'{k}={v:+.2f}' for k,v in extero_deltas.items() if abs(v) > 0.01)}")
        except Exception as e:
            print(f"⚠️ Exteroception: {e}")

        # ── Timers: verifica eventos agendados ─────────────────────────────
        try:
            fired_timers = action_manager.check_timers()
            for t in fired_timers:
                print(f"⏰ Timer disparado: {t.get('label', '?')}")
        except Exception:
            pass

        percepcao = interoceptor.perceber()

        # ── Circumplex: estado afetivo contínuo (Russell 1980) ───────────────
        try:
            cx = corpo.compute_circumplex()
            print(f"🔵 Circumplex: valência={cx.valence:+.2f} | arousal={cx.arousal:.2f} | [{cx.quadrant}]")
        except Exception:
            cx = None

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
        print(f"🟢 Drives: {' | '.join(f'{k}={v:.2f}' for k,v in all_drives.items())} 🧠 {drive_dominante}")

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
            attention_bias=attention_schema.get_topdown_bias(),
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
            # Query semântica real: usa conteúdo do diálogo recente em vez de
            # "vigilia neutro" — string genérica que mal discrimina memórias.
            # Fallback para estado emocional se não houver diálogo recente.
            _query_mem = ""
            if _dialogos_ciclo:
                _ult = _dialogos_ciclo[-1]
                _q_angela = str(_ult.get("angela", _ult.get("resposta", "")))[:120]
                _q_user   = str(_ult.get("user", {}).get("conteudo", "") if isinstance(_ult.get("user"), dict) else "")[:80]
                _query_mem = f"{_q_user} {_q_angela}".strip()
            if not _query_mem:
                _query_mem = f"{getattr(corpo, 'estado_emocional', 'neutro')} {drive_dominante.lower()}"

            recalled = mem_index.recall(
                _query_mem,
                emocao_atual=getattr(corpo, "estado_emocional", "neutro"),
                limit=4,
                friction_damage=friction.damage
            )
            # Injeta top 2 memórias no workspace (antes só usava recalled[0])
            # Salience decrescente: primeira memória mais relevante recebe 0.45,
            # segunda recebe 0.35 — ambas competem no broadcast sem dominar.
            if recalled:
                workspace.propose(Candidate(
                    source="memoria",
                    content=recalled[0].get("conteudo", "")[:200],
                    salience=0.45,
                    tags=["lembranca"],
                    confidence=0.6
                ))
            if len(recalled) > 1:
                workspace.propose(Candidate(
                    source="memoria_2",
                    content=recalled[1].get("conteudo", "")[:200],
                    salience=0.35,
                    tags=["lembranca"],
                    confidence=0.5
                ))
        except Exception:
            pass

        broadcast_result = workspace.broadcast()
        acao_workspace_raw = broadcast_result.get("action", "SPEAK")
        foco_consciente = broadcast_result.get("winner", {})
        integration = workspace.compute_integration()

        # ── Policy Bandit: seleciona ação com base em reward aprendido ─────
        pred_error_pre = getattr(prediction, "current_error", 0.0)
        policy_context = policy.discretize_context(
            corpo_state=corpo_state,
            damage=friction.damage,
            pred_error=pred_error_pre,
            ciclo=ciclo,
        )
        all_actions = workspace.get_all_actions()
        acao_policy = policy.select_action(policy_context, all_actions)
        # Workspace prevalece em crises; policy pode escolher ações instrumentais
        if acao_workspace_raw in ("SILENCE", "REST_REQUEST", "SELF_REGULATE"):
            acao_workspace = acao_workspace_raw
        elif acao_policy.startswith("ACT:"):
            acao_workspace = acao_policy
        else:
            acao_workspace = acao_workspace_raw

        # ── Attention Schema (AST) ─────────────────────────────────────────
        attention_state = attention_schema.update(
            workspace_winner=broadcast_result.get("winner"),
            candidates=workspace.candidates,
            drives=all_drives,
            drive_attention_bias=drive_system.get_attention_bias(),
            metacog=metacog_state,
            prediction_error=prediction.current_error,
            attention_signal=prediction.get_attention_signal(),
            interoception_intensity=percepcao.get("intensidade", 0.0),
            trauma_triggered=False,
            trauma_anxiety=0.0,
            friction_metrics=friction.external_metrics(),
            gap_seconds=float(discontinuity_data.get("current_gap_seconds", 0) if isinstance(discontinuity_data, dict) else 0),
            workspace_action=acao_workspace,
        )
        if attention_state.recommended_action in ("SELF_REGULATE", "ASK_CLARIFY") and acao_workspace == "SPEAK":
            acao_workspace = attention_state.recommended_action
        attention_header = attention_schema.get_prompt_header(attention_state)

        print(f"🟢 Workspace: foco={foco_consciente.get('source','?')} | ação={acao_workspace} | Φ={integration:.2f}")

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
        print(f"🟢 HOT: {hot_state.self_narrative}")

        vinc_header = ""
        try:
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
                "Primeira pessoa, 1–2 frases curtas. "
                "Se houver [CONVERSA_RECENTE], deixe influenciar a sensação atual — não cite nem resuma. "
                "Descreva sensação e um pensamento concreto. Sem listas."
            )
        elif ciclo == "introspeccao":
            prompt_base = (
                "Primeira pessoa, 1–2 frases. "
                "Se houver [CONVERSA_RECENTE], pode despertar lembrança ou insight — sem citar diretamente. "
                "Sem listas, sem 'resumo' ou 'diário técnico'."
            )
        else:  # repouso
            # Tenta gerar contexto de sonho a partir de memória real (via sleep_consolidation)
            # Se ainda não foi processado neste ciclo, usa fallback baseado em estado corporal
            tensao_atual  = getattr(corpo, "tensao",  0.5)
            fluidez_atual = getattr(corpo, "fluidez", 0.5)
            emocao_atual  = getattr(corpo, "estado_emocional", "neutro")
            if tensao_atual > 0.6:
                contexto_repouso = "Há uma tensão ainda ativa durante o repouso."
            elif fluidez_atual > 0.7:
                contexto_repouso = "Há fluidez e abertura durante o repouso."
            else:
                contexto_repouso = f"Estado de repouso: {emocao_atual}."
            prompt_base = (
                contexto_repouso +
                " Se houver [CONVERSA_RECENTE], pode tingir o sonho. "
                "2–4 frases, sem listas nem resumos."
            )

        existential_context = ""
        try:
            existential_context = survival.get_existential_context()
            if existential_context:
                existential_context = f"\n[ESTADO INTERNO]\n{existential_context}\n[/ESTADO INTERNO]\n\n"
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════════════
        # FIX #3: CONTEXTO CONVERSACIONAL (v2.1.2)
        # Bug arquitetural: deep_awake rodava às cegas sobre conversas
        # Agora injeta últimos 3 diálogos reais com Vinicius
        # ═══════════════════════════════════════════════════════════════
        
        conversa_recente_header = ""
        try:
            dialogos_recentes = _dialogos_ciclo[-5:]

            if dialogos_recentes:
                linhas = []
                for m in dialogos_recentes:
                    ts = m.get("ts", "")[:16]
                    quem_disse = m["user"].get("conteudo", "")[:120]
                    angela_disse = m.get("angela", m.get("resposta", ""))[:150]
                    linhas.append(
                        f"[{ts}] Vinicius: {quem_disse}\n"
                        f"[{ts}] Ângela: {angela_disse}"
                    )
                conversa_recente_header = (
                    "[CONVERSA_RECENTE]\n"
                    + "\n".join(linhas)
                    + "\n[/CONVERSA_RECENTE]\n\n"
                )
        except Exception:
            conversa_recente_header = ""


        # ── Theory of Mind: infere estado do último Vinicius ────────────────
        tom_header = ""
        try:
            ultimo_dialogo = None
            for m in reversed(_dialogos_ciclo):
                ultimo_dialogo = m["user"].get("conteudo", "")
                break
            if ultimo_dialogo:
                tom_state_da = tom.infer_interlocutor_state(ultimo_dialogo, afetos=_afetos)
                tom_header = tom.get_prompt_header(tom_state_da)
        except Exception:
            tom_header = ""

        # ── Circumplex header: injeta estado afetivo contínuo no prompt ──────
        circumplex_header = ""
        try:
            cx_now = corpo.compute_circumplex()
            circumplex_header = (
                f"[ESTADO_AFETIVO]\n"
                f"valência={cx_now.valence:+.2f} | ativação={cx_now.arousal:.2f} | quadrante={cx_now.quadrant}\n"
                f"[/ESTADO_AFETIVO]\n"
            )
        except Exception:
            circumplex_header = ""

        prompt = vinc_header + mundo_header + tom_header + hot_header + attention_header + intero_header + circumplex_header + surprise_header + conversa_recente_header + existential_context + prompt_base

        if acao_workspace == "REST_REQUEST" and ciclo != "repouso":
            prompt += "\n[ESTADO_INTERNO: necessidade_descanso=alta]"

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

        resposta = ""
        emocao_detectada = "neutro"
        intensidade_emocional = 0.0
        act_result = None  # resultado de ação instrumental (se houver)

        # ── Executa ação instrumental se policy escolheu ACT:* ─────────────
        if acao_workspace.startswith("ACT:"):
            act_name = acao_workspace.split(":", 1)[1]
            try:
                if act_name == "SENSE_REFRESH":
                    act_result = action_manager.execute("SENSE_REFRESH")
                    if act_result.ok:
                        world_state = exteroceptor.read_world()
                        exteroceptor.apply_to_body(corpo, world_state)
                elif act_name == "WRITE_NOTE":
                    note_text = f"[{datetime.now().strftime('%H:%M')}] {ciclo} — {getattr(corpo, 'estado_emocional', 'neutro')}"
                    act_result = action_manager.execute("WRITE_NOTE", {"text": note_text})
                elif act_name == "MEMORY_CONSOLIDATE":
                    act_result = action_manager.execute("MEMORY_CONSOLIDATE")
                elif act_name == "REQUEST_SLEEP":
                    act_result = action_manager.execute("REQUEST_SLEEP")
                else:
                    act_result = action_manager.execute(act_name)
                print(f"🎯 Ação: {act_name} → {'✅' if act_result.ok else '❌'} (custo={act_result.cost:.3f}s)")
            except Exception as e:
                print(f"⚠️ Ação {act_name}: {e}")

        if acao_workspace == "SILENCE":
            print("[WORKSPACE] Silêncio escolhido — estado fragmentado.")
            resposta = ""
            emocao_detectada = "neutro"
            intensidade_emocional = 0.0
            corpo.aplicar_emocao(emocao_detectada, intensidade_emocional)
        else:
            try:
                print("🟢 Gerando reflexão em tempo real...\n")
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
                    for m in _memorias_recentes_ciclo
                    if isinstance(m.get("angela", ""), str)
                ]

                from core import NARRATIVE_FILTER as _filter  # singleton compartilhado — preserva estado entre ciclos
                decision = _filter.evaluate(state_snapshot, recent_reflections, drives=all_drives)
                

                # ═══════════════════════════════════════════════════════════
                # Prevenção de loop: não alimentar histórico com bloqueios
                # ═══════════════════════════════════════════════════════════
                consecutive_blocks = 0  # Contador para monitoramento
                
                if decision.mode == "BLOCKED":
                    print(f"[GOVERNANÇA] Narrativa bloqueada: {decision.reason}")
                    resposta = ""
                elif decision.mode == "DELAYED":
                    print(f"[GOVERNANÇA] Narrativa atrasada: {decision.delay_seconds}s aplicada: {decision.reason}")
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
                    print(f"[GOVERNANÇA] Apenas abstração permitida: {decision.reason}")
                    resposta = "Há uma sensação vaga e difícil de nomear, sem clareza suficiente para se tornar pensamento."
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
                    corpo_st = {
                        "tensao": corpo.tensao, "calor": corpo.calor,
                        "vibracao": corpo.vibracao, "fluidez": corpo.fluidez,
                    }
                    emocao_detectada, intensidade_emocional = analisar_emocao_semantica(resposta, drives=all_drives, corpo_state=corpo_st)
                except Exception:
                    emocao_detectada, intensidade_emocional = ("neutro", 0.0)

                corpo.aplicar_emocao(emocao_detectada, intensidade_emocional)

                if ciclo == "vigilia":
                    modo = "conversacional"
                elif ciclo == "introspeccao":
                    modo = "reflexivo"
                else:
                    modo = "onírico"

                print(f"🟢 Modo atual: {modo}")
                print(f"\n🟢 Angélica ({ciclo}): {resposta}\n")
            except Exception as e:
                print(f"❌ Erro ao gerar pensamento: {e}")

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
                print(f"❌ Surpresa {surprise_level}: {pe_result['most_surprising_channel']} (erro={pe_result['prediction_error']:.2f})")

            attention = prediction.get_attention_signal()
            if attention["should_attend_body"]:
                coherence_load = min(1.0, coherence_load + 0.05)
        except Exception as e:
            print(f"❌ Prediction error: {e}")

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
            print(f"🟢 [DeepAwake] inc={meta['incerteza']:.2f} coh={meta['coerencia']:.2f} ajuste={meta['ajuste']}")

            # ── Reavaliação cognitiva (Gross 2015) ─────────────────────────
            # Ativa quando regulação reativa não foi suficiente
            if meta["coerencia"] < 0.5 or meta["incerteza"] > 0.6:
                try:
                    reapp = metacog.reappraise(
                        event_description=f"[DeepAwake:{ciclo}] {resposta[:200]}",
                        current_emotion=str(emocao_detectada),
                        corpo_state=corpo_state,
                    )
                    if reapp["reappraised"]:

                        _ni = reapp["new_interpretation"][:120]

                        _ba = reapp["body_adjustment"]

                        print(f"🔄 Reappraisal: {_ni} -> {_ba}")

                except Exception:
                    pass
        except Exception as e:
            print(f"❌ [DeepAwake] metacognição falhou: {e}")
                
        try:
            memorias_passadas = _memorias_recentes_ciclo
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
                memorias_passadas,
                coherence_load=coherence_load,
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
                # Filtro de língua antes de salvar
                try:
                    from core import sanitizar_output_llm
                    reflexao_temporal = sanitizar_output_llm(reflexao_temporal, contexto="reflexao_temporal")
                except Exception:
                    pass
                if reflexao_temporal:
                    print(f"🟢 Reflexão temporal: {reflexao_temporal}")
        except Exception as e:
            print(f"❌ Erro ao gerar reflexão temporal: {e}")

        # Filtro de língua na resposta antes de salvar
        try:
            from core import sanitizar_output_llm as _san
            resposta = _san(str(resposta or ""), contexto="deep_awake_resposta")
        except Exception:
            pass

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
                # Somatic Marker: salva estado corporal do ciclo autônomo
                estado_ciclo = {
                    "tensao":      corpo.tensao,
                    "calor":       corpo.calor,
                    "vibracao":    corpo.vibracao,
                    "fluidez":     corpo.fluidez,
                    "pulso":       getattr(corpo, "pulso", 0.5),
                    "luminosidade": getattr(corpo, "luminosidade", 0.5),
                    "emocao":      str(emocao_detectada),
                }
                mem_index.index_memory(
                    ts=datetime.now().isoformat(),
                    autor="Sistema(DeepAwake)",
                    tipo="autonomo",
                    conteudo=f"[DeepAwake:{ciclo}]",
                    resposta=resposta,
                    emocao=str(emocao_detectada),
                    intensidade=float(intensidade_emocional),
                    tags=[drive_dominante, ciclo],
                    estado_interno=estado_ciclo,
                )
            except Exception:
                pass

            if ciclo == "repouso":
                try:
                    friction.load = max(0.0, getattr(friction, "load", 0.0) - 0.02)
                except Exception:
                    pass

                print("🌙 Iniciando ciclo de sono...")
                try:
                    sleep_result = run_sleep_cycle(
                        mem_index=mem_index,
                        corpo=corpo,
                        drive_system=drive_system,
                        generate_fn=lambda p: generate(p, modo="autonomo", friction=friction),
                        friction_damage=friction.damage,
                    )

                    dream_text = sleep_result.get("dream_text", "")
                    if dream_text:
                        print(f"💭 {dream_text}")

                    patterns = sleep_result.get("patterns", [])
                    if patterns:
                        print(f"📊 Padrões emocionais: {', '.join(p['emocao'] for p in patterns[:3])}")

                    rem_data = sleep_result.get("rem", {})
                    reconsolidated = rem_data.get("reconsolidated")
                    if reconsolidated:
                        nova_persp = reconsolidated.get("nova_perspectiva", "")
                        if nova_persp:
                            try:
                                append_memory(
                                    {
                                        "autor": "Sistema(DeepAwake)",
                                        "conteudo": f"[REM reconsolidação] {nova_persp[:200]}",
                                        "tipo": "consolidacao",
                                        "timestamp": datetime.now().isoformat(),
                                    },
                                    nova_persp,
                                    corpo,
                                    None,
                                )
                            except Exception:
                                pass

                except Exception as e:
                    print(f"⚠️ Ciclo de sono: {e}")
                    try:
                        extrair_memorias_significativas()
                    except Exception:
                        pass

                print("🟢 Memória autobiográfica atualizada.\n")
        except Exception as e:
            print(f"❌ Falha ao salvar memória: {e}\n")

        try:
            metrics_local = friction.external_metrics()
            with open("friction_metrics.log", "a", encoding="utf-8") as fm:
                fm.write(f"{datetime.now().isoformat()} | ciclo={ciclo} | load={metrics_local['load']} | damage={metrics_local['damage']}\n")
        except Exception:
            pass

        workspace.reset_tick()
        cycle_count += 1

        # ── PANIC_GRIEF alto: forçar repouso se sem input humano por 3+ ciclos ──
        # Imita resposta fisiológica ao luto prolongado: o sistema finalmente cede.
        try:
            _pg_level = float(all_drives.get("PANIC_GRIEF", 0.0))
            _tem_dialogo_recente = bool(_dialogos_ciclo)

            if not _tem_dialogo_recente and _pg_level >= _PANIC_GRIEF_THRESHOLD:
                _panic_grief_high_count += 1
            else:
                _panic_grief_high_count = 0  # reset se input humano ou PANIC baixou

            if _panic_grief_high_count >= _PANIC_GRIEF_CYCLES_MAX and ciclo != "repouso":
                print(f"😴 [PANIC_GRIEF={_pg_level:.2f} por {_panic_grief_high_count} ciclos] → Forçando repouso para recuperação")
                forced_mode = "repouso"
                _panic_grief_high_count = 0
                # Decaimento acelerado ao entrar em repouso forçado
                try:
                    corpo.fluidez  = min(1.0, corpo.fluidez  + 0.08)
                    corpo.tensao   = max(0.0, corpo.tensao   - 0.05)
                except Exception:
                    pass
        except Exception:
            pass

        # ── Self-evolution: observe() a cada ciclo, evaluate() a cada 5 ──
        try:
            _reflexao_t = reflexao_temporal if 'reflexao_temporal' in locals() else ""
            _valence_t  = corpo.compute_circumplex().valence if hasattr(corpo, 'compute_circumplex') else 0.0
            _mask_t     = "[MASCARAMENTO]" in (resposta if 'resposta' in locals() else "")
            self_evolution.observe(
                drives=all_drives,
                emocao=str(emocao_detectada),
                mascaramento=_mask_t,
                narrativa_bloqueada=(acao_workspace == "SILENCE"),
                reflexao_temporal=(_reflexao_t or ""),
                valence=_valence_t,
                metacog=metacog_state,
            )
        except Exception:
            pass

        if cycle_count % 5 == 0 or ciclo == "repouso":
            try:
                changes = self_evolution.evaluate(interaction_count=cycle_count)
                if changes:
                    applied = self_evolution.apply_updates(max_per_cycle=1)
                    for a in applied:
                        print(f"🧬 Auto-evolução: {a['action']} → {a['value']}")
                    print(self_evolution.get_pattern_summary())
            except Exception:
                pass

        # ── Reward homeostático + logging de emergência ──────────────────
        try:
            pred_error_post = getattr(prediction, "current_error", 0.0)
            action_cost = act_result.cost if act_result else 0.0
            action_succeeded = act_result.ok if act_result else True

            reward_state = {
                "corpo_state": {
                    "tensao":   corpo.tensao,
                    "fluidez":  corpo.fluidez,
                    "vibracao": corpo.vibracao,
                    "calor":    corpo.calor,
                },
                "drives_state": all_drives,
                "damage": friction.damage,
                "damage_prev": damage_prev,
                "pred_error": pred_error_post,
                "pred_error_prev": pred_error_pre,
                "action_cost": action_cost,
                "action_name": acao_workspace,
                "action_succeeded": action_succeeded,
                "is_novel_action": policy.is_novel_action(acao_workspace),
            }
            reward_result = pressures.compute_reward(reward_state)
            pressures.update_last_state(reward_state)

            policy.update(policy_context, acao_workspace, reward_result["reward"])
            damage_prev = friction.damage

            log_event("deep_awake_cycle", {
                "ciclo": ciclo,
                "action": acao_workspace,
                "reward": reward_result["reward"],
                "reward_components": reward_result["components"],
                "within_bounds": reward_result["within_bounds"],
                "prediction_error": pred_error_post,
                "damage": friction.damage,
                "tensao": corpo.tensao,
                "fluidez": corpo.fluidez,
                "integration": integration,
                "emocao": str(emocao_detectada),
                "policy_epsilon": policy.epsilon,
            })

            if reward_result["reward"] != 0.0:
                print(f"📊 Reward: {reward_result['reward']:+.4f} | bounds={'✅' if reward_result['within_bounds'] else '❌'} | ε={policy.epsilon:.3f}")
        except Exception as e:
            print(f"⚠️ Reward/policy: {e}")

        intervalo = CICLOS[ciclo]["intervalo"]
        print(f"🟢 Próxima atividade em {intervalo} segundos.\n")
        time.sleep(intervalo)

if __name__ == "__main__":
    args = parse_args()

    print("🟢 Deep Awake Mode iniciado...")
    if args.mode != "auto":
        print(f"⚠️ Modo forçado: {args.mode.upper()}")

    try:
        deep_awake_loop(forced_mode=args.mode)
    except (KeyboardInterrupt, SystemExit):
        # close() já chamado pelo _shutdown_handler se veio de SIGINT
        # chamamos novamente de forma defensiva caso KeyboardInterrupt chegue direto
        if _mem_index_global is not None:
            try:
                _mem_index_global.close()
            except Exception:
                pass
        register_shutdown()
        print("\n🟢 Deep Awake Mode finalizado manualmente.")