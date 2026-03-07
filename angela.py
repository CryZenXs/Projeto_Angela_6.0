import os
import time
import random
import json
from core import (
    generate,
    save_emotional_snapshot,
    recall_last_emotion,
    append_memory,
    analisar_emocao_semantica,
    governed_generate,
    load_jsonl,
    check_recurrent_coherence,
)
from endocrine import EndocrineSystem
from senses import DigitalBody
from interoception import Interoceptor
from collections import deque
import datetime
from metacognitor import MetaCognitor
import interoception
from discontinuity import load_discontinuity, calculate_reconnection_cost, register_shutdown
from cognitive_friction import CognitiveFriction
from survival_instinct import SurvivalInstinct
from workspace import GlobalWorkspace, Candidate
from drives import DriveSystem
from higher_order import HigherOrderMonitor
from memory_index import MemoryIndex
from prediction_engine import PredictionEngine
from self_evolution import SelfEvolution
from theory_of_mind import TheoryOfMindModule
from attention_schema import AttentionSchema
from exteroception import Exteroceptor
from actions import ActionManager
from policy_bandit import PolicyBandit
from objective_pressures import ObjectivePressures
from metrics_logger import log_event
from tempo_subjetivo import gerar_reflexao_temporal, PresenteBuffer, PassagemSentida, get_temporal_context


base_prompt = "Responda ao que foi dito.\n"

print("🟢 Iniciando conversa com Angela...\n")

def chat_loop():
    
    corpo = DigitalBody()
    interoceptor = Interoceptor(corpo)
    
    friction = CognitiveFriction(seed=None)
    survival = SurvivalInstinct(corpo, friction)

    workspace = GlobalWorkspace()
    drive_system = DriveSystem()
    endocrine_system = EndocrineSystem()
    hot_monitor = HigherOrderMonitor()
    mem_index = MemoryIndex()
    prediction = PredictionEngine()
    self_evolution = SelfEvolution()
    tom = TheoryOfMindModule()  # Theory of Mind — infere estado de Vinicius
    attention_schema = AttentionSchema()  # AST — modelo de atenção para controle e auto-relato
    exteroceptor = Exteroceptor()  # Percepção do mundo externo (bateria, rede, temp)
    action_manager = ActionManager(friction, corpo)  # Ações com consequências reais
    policy = PolicyBandit()  # Contextual bandit para seleção de ações
    pressures = ObjectivePressures()  # Reward homeostático sem LLM
    presente_buffer = PresenteBuffer(maxsize=4)   # Camada 2: agora
    passagem_sentida = PassagemSentida()           # Camada 3: fluxo via substrato
    interaction_count = 0
    real_interaction_count = 0  # conta apenas turnos com resposta real (não silêncios)
    damage_prev = friction.damage  # para cálculo de delta de dano

    try:
        mem_index.bulk_index_from_jsonl("angela_memory.jsonl")
    except Exception:
        pass

    try:
        # angela.py só LÊ o estado de descontinuidade — quem registra boot/shutdown é o deep_awake.py
        disc = load_discontinuity()
        gap = disc.get("current_gap_seconds", 0)
        reconnection_cost = calculate_reconnection_cost(gap)
        corpo.fluidez = max(0.0, min(1.0, corpo.fluidez + reconnection_cost["fluidez"]))
        corpo.tensao = max(0.0, min(1.0, corpo.tensao + reconnection_cost["tensao"]))
        # Exibe informação de reconexão com nível de impacto
        if gap > 300:  # > 5 minutos
            desc = reconnection_cost.get("description", f"{gap/3600:.1f}h de ausência")
            print(f"⏱️  [{desc}]")
        # Registra memória de descontinuidade se impacto real (distingue estado fórmula de estado vivido)
        if reconnection_cost.get("gap_injected") and reconnection_cost.get("impact", "nenhum") != "nenhum":
            try:
                append_memory(
                    {
                        "autor": "Sistema(Discontinuity)",
                        "conteudo": f"[gap={reconnection_cost['gap_hours']}h impacto={reconnection_cost['impact']}]",
                        "tipo": "discontinuidade",
                        "timestamp": datetime.datetime.now().isoformat(),
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
        if gap > 0:
            attention_schema.apply_reconnection_cost(gap)
        # Gap longo aumenta saudade diretamente — não depende de verbalização
        _SAUDADE_POR_IMPACTO = {"moderado": 0.08, "severo": 0.14, "crítico": 0.20}
        _delta_saudade = _SAUDADE_POR_IMPACTO.get(reconnection_cost.get("impact", ""), 0.0)
        if _delta_saudade > 0.0:
            try:
                _afetos = {}
                try:
                    with open("afetos.json", "r", encoding="utf-8") as _f:
                        _afetos = json.load(_f)
                except Exception:
                    pass
                _v = _afetos.get("Vinicius", {"confianca": 0.5, "gratidao": 0.5,
                                              "saudade": 0.0, "ansiedade": 0.3})
                _v["saudade"] = min(1.0, _v.get("saudade", 0.0) + _delta_saudade)
                _afetos["Vinicius"] = _v
                from core import atomic_json_write
                atomic_json_write("afetos.json", _afetos)
            except Exception:
                pass
    except Exception:
        disc = {}
        pass

    try:
        corpo.coherence_load = float(getattr(corpo, "coherence_load", 0.0))
    except Exception:
        corpo.coherence_load = 0.0

    metacog = MetaCognitor(interoceptor)

    # === INJEÇÃO DE GERADOR LLM ===
    def llm_wrapper(prompt):
        """Wrapper para geração via LLM."""
        try:
            return generate(
                prompt,
                contexto="",
                modo="conversacional"
            )
        except Exception as e:
            print(f"[WARN] LLM geração falhou: {e}")
            return ""
    
    # Injetar nos módulos
    hot_monitor.set_llm_generator(llm_wrapper)
    metacog.set_llm_generator(llm_wrapper)
    survival.set_llm_generator(llm_wrapper)
    print("✅ Geradores LLM injetados em HOT, Metacog e Survival")
    # === FIM DA INJEÇÃO ===


    last_action = "SPEAK"

    while True:
        try:
            user_input = input("Você: ").strip()
            if not user_input:
                continue

            # Camada 2: registra input no buffer de presente
            presente_buffer.push("Vinicius", user_input)

            # Camada 3: registra passagem do substrato a cada turno
            try:
                _substrato_now = corpo.substrato.read()
                passagem_sentida.registrar(_substrato_now)
                passagem_sentida.aplicar_ao_corpo(corpo)
            except Exception:
                pass

            # Comando de diagnóstico — exibe estado interno sem gerar resposta
            if user_input.lower() in ("/estado", "/state", "/debug"):
                print("\n" + "=" * 52)
                print("  📊 ESTADO INTERNO DE ANGELA")
                print("=" * 52)
                print(f"  Corpo  : tensao={corpo.tensao:.3f} | calor={corpo.calor:.3f}")
                print(f"           vibracao={corpo.vibracao:.3f} | fluidez={corpo.fluidez:.3f}")
                print(f"           emocao={getattr(corpo, 'estado_emocional', '?')}")
                try:
                    cx = corpo.compute_circumplex()
                    print(f"  Affect : valência={cx.valence:+.3f} | arousal={cx.arousal:.3f} | [{cx.quadrant}]")
                except Exception:
                    pass
                try:
                    v_d, a_d = drive_system.get_circumplex()
                    print(f"  DriveΨ: valência={v_d:+.3f} | arousal={a_d:.3f}")
                except Exception:
                    pass
                try:
                    print(f"  Drives : {' | '.join(f'{k}={v:.2f}' for k,v in drive_system.get_all_levels().items())}")
                except Exception:
                    pass
                try:
                    m_ = friction.external_metrics()
                    print(f"  Atrito : load={m_['load']:.4f} | damage={m_['damage']:.4f}")
                except Exception:
                    pass
                try:
                    ws = exteroceptor.read_world()
                    ws_parts = []
                    if ws.get("battery_pct") is not None:
                        ws_parts.append(f"bat={ws['battery_pct']:.0%}")
                    if ws.get("connected") is not None:
                        ws_parts.append(f"net={'✅' if ws['connected'] else '❌'}")
                    if ws_parts:
                        print(f"  Mundo  : {' | '.join(ws_parts)}")
                except Exception:
                    pass
                try:
                    ps = policy.get_policy_summary()
                    print(f"  Policy : ε={ps['epsilon']:.3f} | ctx={ps['n_contexts']} | updates={ps['n_updates']}")
                except Exception:
                    pass
                print(f"  Interacoes reais: {real_interaction_count} | total: {interaction_count}")
                print("=" * 52 + "\n")
                continue

            input_data = {
                "autor": "Vinicius",
                "conteudo": user_input,
                "tipo": "dialogo",
                "timestamp": datetime.datetime.now().isoformat()
            }

            print("\n🟢 Angela está pensando...\n")

            # ── Exteroception: percepção do mundo externo ──────────────────────
            world_state = {}
            mundo_header = ""
            try:
                world_state = exteroceptor.read_world()
                extero_deltas = exteroceptor.apply_to_body(corpo, world_state)
                mundo_header = exteroceptor.get_prompt_header(world_state)
                # Aplica estímulos de drives do mundo externo
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

            vinc_header = ""
            _afetos = {}
            try:
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
            except Exception:
                pass

            try:
                # Lê apenas as últimas 200 linhas do arquivo — evita carregar tudo na memória
                from collections import deque as _deque
                _recent_lines = []
                with open("angela_memory.jsonl", "r", encoding="utf-8") as _f:
                    _recent_lines = list(_deque(_f, maxlen=200))
                memoria_dialogo = []
                for _line in _recent_lines:
                    try:
                        _m = json.loads(_line.strip())
                        if isinstance(_m.get("user"), dict) and _m["user"].get("tipo") == "dialogo":
                            memoria_dialogo.append(_m)
                    except Exception:
                        continue
                memoria_dialogo = memoria_dialogo[-5:]
            except Exception:
                memoria_dialogo = []

            try:
                autobio = load_jsonl("angela_autobio.jsonl")[-10:]
                memorias_passadas_texto = "\n".join([m.get("resumo", "") for m in autobio])
            except Exception:
                memorias_passadas_texto = ""

            memorias_associativas = ""
            somatic_marker = {}
            try:
                emocao_corpo_atual = getattr(corpo, "estado_emocional", "neutro")
                recalled = mem_index.recall(
                    user_input,
                    emocao_atual=emocao_corpo_atual,
                    limit=4,
                    friction_damage=friction.damage
                )
                if recalled:
                    # CORREÇÃO 4: Filtra memórias autônomas para evitar contaminação do diálogo
                    recalled = [r for r in recalled if r.get("tipo") != "autonomo"]
                
                if recalled:
                    frags = []
                    for r in recalled:
                        frags.append(f"- [{r.get('emocao','?')}] {r.get('conteudo','')[:100]}")
                    memorias_associativas = "[LEMBRANÇAS_EVOCADAS]\n" + "\n".join(frags) + "\n[/LEMBRANÇAS_EVOCADAS]\n"

                # ── Somatic Marker (Damasio 1994) ─────────────────────────────────
                # Recupera como o corpo se sentiu em situações similares no passado
                somatic_marker = mem_index.get_somatic_marker(
                    user_input,
                    limit=5,
                    friction_damage=friction.damage
                )
                if somatic_marker.get("reliable", False):
                    # Aplica blend leve (5%) do marcador no corpo atual
                    # O corpo "lembra" como se sentiu em situações parecidas
                    sm_blend = 0.05
                    for canal in ("tensao", "calor", "vibracao", "fluidez"):
                        current = getattr(corpo, canal, 0.5)
                        past = somatic_marker.get(canal, current)
                        setattr(corpo, canal, max(0.0, min(1.0,
                            current * (1 - sm_blend) + past * sm_blend
                        )))
                    sm_v = somatic_marker.get("valence_bias", 0.0)
                    sm_em = somatic_marker.get("dominant_emocao", "neutro")
                    sm_n = somatic_marker.get("sample_count", 0)
                    print(f"🫀 Somatic: valência={sm_v:+.2f} | emocao={sm_em} | [{sm_n} memórias]")
            except Exception:
                pass

            # ── Contexto temporal (Camadas 2 e 3) ─────────────────────────────
            _temporal_ctx = ""
            try:
                _mems_temp = mem_index.recall(user_input, limit=3) if user_input else []
                _temporal_ctx = get_temporal_context(presente_buffer, passagem_sentida, _mems_temp)
            except Exception:
                pass

            meta_header = ""
            try:
                metas = []
                with open("angela_memory.jsonl", "r", encoding="utf-8") as f:
                    _meta_recent = list(deque(f, maxlen=200))  # lê apenas últimas 200 linhas
                for line in reversed(_meta_recent):
                    try:
                        _m = json.loads(line.strip())
                    except Exception:
                        continue
                    # Suporta formato novo (user.tipo == "metacognicao") e legado ("[META]" na linha)
                    _tipo = _m.get("user", {}).get("tipo", "") if isinstance(_m.get("user"), dict) else ""
                    _conteudo = _m.get("user", {}).get("conteudo", "") if isinstance(_m.get("user"), dict) else _m.get("conteudo", "")
                    if _tipo == "metacognicao" or "[META]" in line:
                        if any(k in _conteudo for k in ("insegurança", "medo leve", "dopamina")):
                            metas.append(_conteudo)
                    if len(metas) >= 2:
                        break
                if metas:
                    meta_header = "[META]\n" + "\n".join(metas) + "\n[/META]\n"
            except Exception:
                meta_header = ""

            corpo_state = {
                "tensao": corpo.tensao,
                "calor": corpo.calor,
                "vibracao": corpo.vibracao,
                "fluidez": corpo.fluidez,
                "pulso": getattr(corpo, "pulso", 0.5),
                "luminosidade": getattr(corpo, "luminosidade", 0.5),
            }

            metacog_state = {"incerteza": 0.3, "coerencia": 0.7}

            drive_system.update(
                corpo_state=corpo_state,
                user_input=user_input,
                afetos=_afetos,
                discontinuity=disc if isinstance(disc, dict) else {},
                metacog=metacog_state,
                friction_metrics=friction.external_metrics()
            )
            drive_system.decay_all()

            # ── Sistema Endócrino (Atualiza e Modula Drives) ───────────
            _drives_dict = {name: obj.level for name, obj in drive_system.drives.items()}
            endocrine_system.update(_drives_dict, friction.damage, is_sleeping=False)
            endocrine_system.modulate_drives(drive_system.drives)
            # ──────────────────────────────────────────────────────────

            drive_dominante, drive_nivel = drive_system.get_dominant()
            all_drives = drive_system.get_all_levels()

            print(f"💿 Drives: {' | '.join(f'{k}={v:.2f}' for k,v in all_drives.items())} → {drive_dominante}")
            print(f"🧪 Endócrino: Cortisol={endocrine_system.state['cortisol']:.2f} | Ocitocina={endocrine_system.state['oxytocin']:.2f} | Adrenalina={endocrine_system.state['adrenaline']:.2f}")

            workspace.update_state(
                corpo_state=corpo_state,
                afetos=_afetos,
                drives=all_drives,
                ultimo_input=user_input,
                somatic_marker=somatic_marker,
                attention_bias=attention_schema.get_topdown_bias(),
            )

            percepcao_pre = interoceptor.perceber()
            if percepcao_pre["intensidade"] > 0.03:
                sensacao_dominante = percepcao_pre["sensacoes"][0] if percepcao_pre["sensacoes"] else "estabilidade"
                workspace.propose(Candidate(
                    source="interocepcao",
                    content=sensacao_dominante,
                    salience=min(1.0, percepcao_pre["intensidade"] * 1.5),
                    tags=["corpo", "sensacao"],
                    confidence=0.8
                ))

            if memorias_associativas:
                workspace.propose(Candidate(
                    source="memoria",
                    content=memorias_associativas[:200],
                    salience=0.5,
                    tags=["lembranca", "associacao"],
                    confidence=0.6
                ))

            try:
                trigger_check = survival.trauma.check_triggers(user_input)
                if trigger_check["triggered"]:
                    workspace.propose(Candidate(
                        source="trauma",
                        content=f"trigger: {trigger_check['keywords'][:3]}",
                        salience=min(1.0, 0.5 + trigger_check["anxiety_level"]),
                        tags=["ameaça", "trauma"],
                        confidence=0.9
                    ))
            except Exception:
                trigger_check = {"triggered": False, "anxiety_level": 0.0, "keywords": []}

            if drive_nivel > 0.5:
                workspace.propose(Candidate(
                    source="drive",
                    content=f"drive {drive_dominante} ativo",
                    salience=drive_nivel,
                    tags=[drive_dominante.lower()],
                    confidence=0.7
                ))

            # ── Somatic Marker Candidate (Damasio 1994) ─────────────────────
            if somatic_marker.get("reliable", False):
                sm_valence = somatic_marker.get("valence_bias", 0.0)
                sm_salience = 0.35 + abs(sm_valence) * 0.35
                workspace.propose(Candidate(
                    source="somatic_marker",
                    content=f"marcador_somatico:valence={sm_valence:+.2f}:emocao={somatic_marker.get('dominant_emocao','neutro')}",
                    salience=sm_salience,
                    tags=["somatic_marker", "experiencia_passada"],
                    confidence=min(0.9, 0.5 + somatic_marker.get("sample_count", 0) * 0.1)
                ))

            predicted_state = prediction.predict(
                corpo_state=corpo_state,
                emocao_atual=getattr(corpo, "estado_emocional", "neutro"),
                drive_dominante=drive_dominante,
                user_input=user_input,
                intensidade=getattr(corpo, "intensidade_emocional", 0.0)
            )

            broadcast_result = workspace.broadcast()
            acao_workspace = broadcast_result.get("action", "SPEAK")
            foco_consciente = broadcast_result.get("winner", {})
            integration = workspace.compute_integration()

            # ── Policy Bandit: seleciona ação com base em reward aprendido ─────
            pred_error_pre = getattr(prediction, "current_error", 0.0)
            policy_context = policy.discretize_context(
                corpo_state=corpo_state,
                damage=friction.damage,
                pred_error=pred_error_pre,
                ciclo="vigilia",
                drives=all_drives,
            )
            all_actions = workspace.get_all_actions()
            acao_policy = policy.select_action(policy_context, all_actions)
            # Workspace tem prioridade em situações críticas; policy complementa
            if acao_workspace in ("SILENCE", "REST_REQUEST", "SELF_REGULATE"):
                acao = acao_workspace  # regras críticas prevalecem
            elif acao_policy.startswith("ACT:"):
                acao = acao_policy  # ação instrumental do bandit
            else:
                acao = acao_workspace  # workspace decide em situações normais

            # ── Attention Schema (AST): modelo de atenção para controle e auto-relato ──
            attention_state = attention_schema.update(
                workspace_winner=broadcast_result.get("winner"),
                candidates=workspace.candidates,
                drives=all_drives,
                drive_attention_bias=drive_system.get_attention_bias(),
                metacog=metacog_state,
                prediction_error=workspace.state.prediction_error,
                attention_signal=prediction.get_attention_signal(),
                interoception_intensity=percepcao_pre.get("intensidade", 0.0),
                trauma_triggered=trigger_check.get("triggered", False),
                trauma_anxiety=trigger_check.get("anxiety_level", 0.0),
                friction_metrics=friction.external_metrics(),
                gap_seconds=float(disc.get("current_gap_seconds", 0) if isinstance(disc, dict) else 0),
                workspace_action=acao,
            )
            if attention_state.recommended_action in ("SELF_REGULATE", "ASK_CLARIFY") and acao == "SPEAK":
                acao = attention_state.recommended_action
            attention_header = attention_schema.get_prompt_header(attention_state)

            print(f"🛠️ Workspace: foco={foco_consciente.get('source','?')} | ação={acao} | Φ={integration:.2f}")

            hot_state = hot_monitor.observe(
                corpo_state=corpo_state,
                drives=all_drives,
                metacog=metacog_state,
                integration=integration,
                prediction_error=workspace.state.prediction_error,
                last_action=last_action,
                emocao=getattr(corpo, "estado_emocional", "neutro"),
                intensidade=getattr(corpo, "intensidade_emocional", 0.0),
                attention_scope_override=getattr(attention_state, "scope", None),
                schema_reliability=getattr(attention_state, "schema_reliability", None),
            )
            hot_header = hot_monitor.get_prompt_header()


            surprise_header = prediction.get_prompt_context()

            intero_header = ""
            if percepcao_pre["intensidade"] > 0.03:
                sensacao_texto = " e ".join(percepcao_pre["sensacoes"][:2])
                intero_header = (
                    f"[INTEROCEPCAO_ATUAL]\n"
                    f"intensidade={percepcao_pre['intensidade']:.2f}\n"
                    f"dominante=\"{sensacao_texto}\"\n"
                    f"[/INTEROCEPCAO_ATUAL]\n"
                )

            # ── Circumplex header (Russell 1980) ─────────────────────────────
            # Angela vê seu estado afetivo contínuo durante conversas
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

            # ── Sistema Endócrino (Moods/Humores) ──────────────────────────
            endocrine_header = ""
            sensation_endo = endocrine_system.get_interoceptive_sensation()
            if sensation_endo:
                endocrine_header = f"{sensation_endo}\n"

            # ── Theory of Mind (Frith & Frith 2006) ────────────────────────
            # Infere estado mental de Vinicius: emoção aparente, intenção e necessidade
            tom_header = ""
            try:
                tom_state = tom.infer_interlocutor_state(
                    user_input,
                    conversation_history=memoria_dialogo,
                    afetos=_afetos,
                )
                tom_header = tom.get_prompt_header(tom_state)
                if tom_state.get("confiante", False) and tom_state.get("emocao_inferida", "neutro") != "neutro":
                    em_v = tom_state.get("emocao_inferida", "?")
                    it_v = tom_state.get("intencao", "?").replace("_", " ")
                    nd_v = tom_state.get("necessidade", "")
                    print(f"🧠 ToM: Vinicius={em_v} | {it_v}{(' | necessidade: ' + nd_v) if nd_v else ''}")
            except Exception:
                tom_header = ""

            existential_context = ""
            fear_context = ""
            try:
                existential_context = survival.get_existential_context()
                if survival.detect_shutdown_threat(user_input):
                    fear_context = survival.generate_fear_response("high")
            except Exception:
                pass

            context = (
                (_temporal_ctx + "\n" if _temporal_ctx else "")
                + vinc_header
                + mundo_header
                + tom_header
                + endocrine_header
                + hot_header
                + attention_header
                + intero_header
                + circumplex_header
                + surprise_header
                + memorias_associativas
                + meta_header
                + (memorias_passadas_texto + "\n" if memorias_passadas_texto else "")
                + "\n".join(
                    [
                        # Acessa m["user"] para obter autor/conteudo corretos
                        # m.get('input') já tem prefixo "Vinicius: ..." — evitar duplicação
                        (
                            f"{m['user'].get('autor', 'Vinicius')}: {m['user'].get('conteudo', '')}"
                            f"\nÂngela: {m.get('angela', m.get('resposta', ''))}"
                        )
                        for m in memoria_dialogo
                        if isinstance(m, dict) and isinstance(m.get("user"), dict)
                    ]
                )
            )

            full_context = context
            if existential_context:
                full_context += f"\n[ESTADO]\n{existential_context}\n[/ESTADO]\n"
            if fear_context:
                full_context += f"\n[MEDO]\n{fear_context}\n[/MEDO]\n"

            if acao == "REST_REQUEST":
                prompt_final = (
                    f"{base_prompt}\n{full_context}\n"
                    f"[ESTADO: REST_REQUEST]\n"
                    f"Vinicius: {user_input}\nÂngela:"
                )
            elif acao == "SILENCE":
                print("🤫 Angela escolheu o silêncio (estado fragmentado ou trauma ativo).\n")
                response = "..."
                prompt_final = None
                try:
                    drive_system.save_state()  # garante que drives acumulados no turno não se percam
                except Exception:
                    pass
            elif acao == "ASK_CLARIFY":
                prompt_final = (
                    f"{base_prompt}\n{full_context}\n"
                    f"[ESTADO: ASK_CLARIFY]\n"
                    f"Vinicius: {user_input}\nÂngela:"
                )
            elif acao == "SELF_REGULATE":
                prompt_final = (
                    f"{base_prompt}\n{full_context}\n"
                    f"[ESTADO: SELF_REGULATE]\n"
                    f"Vinicius: {user_input}\nÂngela:"
                )
            elif acao == "RECALL_MEMORY":
                prompt_final = (
                    f"{base_prompt}\n{full_context}\n"
                    f"[ESTADO: RECALL_MEMORY]\n"
                    f"Vinicius: {user_input}\nÂngela:"
                )
            elif acao.startswith("ACT:"):
                # ── Ação instrumental: executar e depois responder ─────────────
                act_name = acao.split(":", 1)[1]
                act_params = {}
                if act_name == "SENSE_REFRESH":
                    # Força releitura dos sensores
                    act_result = action_manager.execute("SENSE_REFRESH")
                    if act_result.ok:
                        world_state = exteroceptor.read_world()
                        exteroceptor.apply_to_body(corpo, world_state)
                elif act_name == "WRITE_NOTE":
                    # Nota baseada no contexto atual
                    note_text = f"[{datetime.datetime.now().strftime('%H:%M')}] {getattr(corpo, 'estado_emocional', 'neutro')} — {user_input[:200]}"
                    act_result = action_manager.execute("WRITE_NOTE", {"text": note_text})
                elif act_name == "MEMORY_CONSOLIDATE":
                    act_result = action_manager.execute("MEMORY_CONSOLIDATE")
                elif act_name == "REQUEST_SLEEP":
                    act_result = action_manager.execute("REQUEST_SLEEP")
                else:
                    act_result = action_manager.execute(act_name, act_params)
                print(f"🎯 Ação: {act_name} → {'✅' if act_result.ok else '❌'} (custo={act_result.cost:.3f}s)")
                # Após ação instrumental, ainda responde normalmente
                prompt_final = f"{base_prompt}\n{full_context}\nVinicius: {user_input}\nÂngela:"
            else:
                prompt_final = f"{base_prompt}\n{full_context}\nVinicius: {user_input}\nÂngela:"

            state_snapshot = {
                "tensao": corpo.tensao,
                "calor": corpo.calor,
                "vibracao": corpo.vibracao,
                "fluidez": corpo.fluidez,
                "emocao": getattr(corpo, "estado_emocional", None)
            }

            recent_reflections = [
                m.get("resposta", m.get("angela", ""))
                for m in memoria_dialogo[-3:]
                if isinstance(m, dict)
            ]


            # Printar HOT ANTES de gerar resposta
            narrative_text = hot_state.self_narrative
            if len(narrative_text) > 150:
                truncated = narrative_text[:150]
                last_space = truncated.rfind(' ')
                if last_space > 0:
                    narrative_text = truncated[:last_space] + "..."
                else:
                    narrative_text = truncated + "..."
            
            print(f"🪞 HOT: {narrative_text}\n")

            if prompt_final is not None:
                # Imprime label ANTES do streaming para que os tokens apareçam logo após o rótulo
                print("🗣️ Ângela: ", end="", flush=True)

                import sys, io
                _old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    response = governed_generate(
                        prompt_final,
                        state_snapshot=state_snapshot,
                        recent_reflections=recent_reflections,
                        mode="conversacional",
                        raw_generate_fn=lambda p, modo: generate(p, modo=modo, friction=friction),
                        drives=all_drives,
                        prediction_error=getattr(prediction, "current_error", 0.0),
                        attention_state=attention_state,
                    )
                finally:
                    sys.stdout = _old_stdout

                from core import sanitizar_output_llm
                response = sanitizar_output_llm(response, contexto="chat")

                if not response:
                    response = "..."
                    print(response)
                else:
                    # Simula streaming da resposta já sanitizada
                    for char in response:
                        sys.stdout.write(char)
                        sys.stdout.flush()
                        time.sleep(0.01)
                    print("\n")

            try:
                carga = float(getattr(corpo, "coherence_load", 0.0))
                if carga > 0.05:
                    if random.random() < min(0.35, 0.1 + carga):
                        response = response.replace(". ", "... ", 1)
            except Exception:
                pass

            last_action = acao

            # Bloqueio não-voluntário → RAGE cresce (frustração por não conseguir se expressar)
            if response == "..." and acao != "SILENCE":
                try:
                    drive_system.drives["RAGE"].activate("blocked_narrative", 0.5)
                    drive_system.save_state()
                    all_drives = drive_system.get_all_levels()  # atualiza snapshot para refletir RAGE elevado
                except Exception:
                    pass

            # Camada 2: registra resposta da Angela no buffer de presente
            try:
                presente_buffer.push("Angela", (response or "")[:200],
                                    emocao=getattr(corpo, "estado_emocional", "neutro"))
            except Exception:
                pass

            emocao_detectada, intensidade = analisar_emocao_semantica(response, drives=all_drives, corpo_state=corpo_state)

            # ── Processamento Recorrente (Lamme 2006) — detecta contradição entre
            # resposta gerada e estado emocional interno. Não bloqueia. Apenas registra.
            rpt_coherence = {}
            try:
                rpt_coherence = check_recurrent_coherence(
                    response_text=response,
                    emocao_atual=str(emocao_detectada),
                    intensidade=float(intensidade),
                    drives=all_drives,
                )
                if rpt_coherence.get("signal"):
                    print(f"🔁 RPT: {rpt_coherence['signal']}")
            except Exception:
                rpt_coherence = {}

            try:
                if response != "...":  # não acumula dano cognitivo quando Angela está em silêncio
                    emotional_intensity = getattr(corpo, "intensidade_emocional", 0.0)
                    arousal = getattr(corpo, "pulso", 0.0)
                    friction.step(
                        emotional_intensity=emotional_intensity,
                        arousal=arousal,
                        task_complexity=0.6
                    )
            except Exception as e:
                print(f"🧨 Friction: {e}")

            try:
                with open("friction_metrics.log", "a", encoding="utf-8") as fm:
                    metrics = friction.external_metrics()
                    fm.write(f"{datetime.datetime.now().isoformat()} | ciclo=chat | load={metrics['load']} | damage={metrics['damage']}\n")
            except Exception:
                pass

            try:
                survival.update(event_description=user_input)
                if trigger_check["triggered"] and trigger_check["anxiety_level"] > 0.3:
                    corpo.tensao = min(1.0, corpo.tensao + trigger_check["anxiety_level"] * 0.2)
                    print(f"🧨 Trigger: {trigger_check['keywords']}")
                if survival.detect_shutdown_threat(user_input):
                    print("🚨 AMEAÇA DETECTADA")
                    friction.load += 0.3
            except Exception as e:
                print(f"🧨 Survival: {e}")

            if not hasattr(corpo, "_ultimas_emocoes") or corpo._ultimas_emocoes is None:
                corpo._ultimas_emocoes = deque(maxlen=5)

            corpo.aplicar_emocao(emocao_detectada, intensidade)
            corpo._ultimas_emocoes.append(emocao_detectada)

            print(f"🤫 Emoção detectada: {emocao_detectada} (intensidade {intensidade:.2f})\n")

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
                    print(f"🧨 Surpresa {surprise_level}: {pe_result['most_surprising_channel']} (erro={pe_result['prediction_error']:.2f})")

                attention = prediction.get_attention_signal()
                if attention["should_attend_body"]:
                    corpo.coherence_load = min(1.0, getattr(corpo, "coherence_load", 0.0) + 0.05)
            except Exception as e:
                print(f"🧨 Prediction error: {e}")

            if not hasattr(corpo, "_cycle_count"):
                corpo._cycle_count = 0
            corpo._cycle_count += 1

            percepcao = interoceptor.perceber()
            if percepcao["intensidade"] > 0.05:
                sensacao_texto = " e ".join(percepcao["sensacoes"])
                print(f"\n🤫 Angela percebe internamente: {sensacao_texto}")
                
                interoceptor.feedback_emocao(emocao_detectada)
                try:
                    _drive_dom = drive_dominante if 'drive_dominante' in locals() else "neutro"
                    _emocao_atual = getattr(corpo, "estado_emocional", "neutro")
                    reflexao_corporal = generate(
                        f"[drive={_drive_dom} | emocao={_emocao_atual} | tensao={corpo.tensao:.2f} | fluidez={corpo.fluidez:.2f}]\n"
                        f"Percebi sensações: {sensacao_texto}. "
                        f"Primeira pessoa singular. Reflita o significado emocional em 1 frase curta, sem repetir a descrição literal.",
                        friction=friction
                    )
                    if reflexao_corporal.strip().startswith(sensacao_texto[:20]):
                        reflexao_corporal = reflexao_corporal.replace(sensacao_texto, "", 1).strip()
                    if reflexao_corporal.lower().startswith("eu sinto") or reflexao_corporal.lower().startswith("sinto"):
                        reflexao_corporal = reflexao_corporal[reflexao_corporal.find(".")+1:].strip()

                    print(f"🪄ï¸ Reflexão corporal: {reflexao_corporal}\n")
                except Exception as e:
                    print(f"🧨 Erro ao gerar reflexão corporal: {e}")
            else:
                reflexao_corporal = None

            try:
                meta = metacog.process(
                    texto_resposta=response,
                    emocao_nome=str(emocao_detectada),
                    intensidade=float(intensidade),
                    contexto_memoria=context,
                    autor="Ângela"
                )
                metacog_state = {"incerteza": meta["incerteza"], "coerencia": meta["coerencia"]}

                try:
                    afetos = {}
                    try:
                        with open("afetos.json","r",encoding="utf-8") as f: afetos = json.load(f)
                    except Exception:
                        afetos = {}
                    v = afetos.get("Vinicius", {"confianca":0.5,"gratidao":0.5,"saudade":0.0,"ansiedade":0.3})
                    if meta.get("ajuste") == "dopamina":
                        v["confianca"] = min(1.0, v.get("confianca",0.5) + 0.02)
                        v["gratidao"] = min(1.0, v.get("gratidao",0.5) + 0.02)  # chave padronizada sem acento
                    elif meta.get("ajuste") in ("inseguranca","medo_leve"):
                        v["confianca"] = max(0.0, v.get("confianca",0.5) - 0.01)
                        v["ansiedade"] = min(1.0, v.get("ansiedade",0.3) + 0.01)
                    afetos["Vinicius"] = v
                    from core import atomic_json_write
                    try:
                        atomic_json_write("afetos.json", afetos)
                    except Exception as e:
                        print(f"[Angela] ⚠️ Falha ao salvar afetos.json: {e}")
                except Exception:
                    pass

                print(f"🧩 Metacognição: inc={meta['incerteza']:.2f} coh={meta['coerencia']:.2f} â†’ {meta['ajuste']}")

                # ── Reavaliação cognitiva (Gross 2015) ─────────────────────────
                # Ativa quando regulação reativa não foi suficiente
                if meta["coerencia"] < 0.5 or meta["incerteza"] > 0.6:
                    try:
                        reapp = metacog.reappraise(
                            event_description=user_input,
                            current_emotion=str(emocao_detectada),
                            corpo_state=corpo_state,
                        )
                        if reapp["reappraised"]:

                            _ni = reapp["new_interpretation"][:120]

                            _ba = reapp["body_adjustment"]

                            print(f"🔄 Reappraisal: {_ni} -> {_ba}")

                            # ── Cognitive Reappraisal — ajuste de baseline (Gross 2015) ────
                            # Reappraisal bem-sucedido sugere regulação ativa deste drive.
                            # Reduz baseline levemente — disposição crônica, não apenas estado momentâneo.
                            try:
                                _drive_map = {
                                    "medo": "FEAR", "raiva": "RAGE",
                                    "ansiedade": "FEAR", "tristeza": "PANIC_GRIEF",
                                }
                                _drive_name = _drive_map.get(str(emocao_detectada), "")
                                if _drive_name and _drive_name in drive_system.drives:
                                    _drive_obj = drive_system.drives[_drive_name]
                                    _drive_obj.baseline = max(
                                        0.02,
                                        _drive_obj.baseline - 0.005
                                    )
                            except Exception:
                                pass

                    except Exception:
                        pass
            except Exception as e:
                print(f"🧨 Metacognição falhou: {e}")

            try:
                corpo.decaimento()
                save_emotional_snapshot(corpo, contexto=response)
                ultima_emocao = recall_last_emotion()
                reflexao = corpo.refletir_emocao_passada(ultima_emocao["emocao"]) if ultima_emocao else None
                append_memory(input_data, response, corpo, reflexao_corporal)
                print("🧠 Memória e emoções salvas com sucesso.\n")
            except Exception as e:
                print(f"🧨 Falha ao salvar memória: {e}\n")

            try:
                # Salva estado corporal APÓS aplicação da emoção para o Somatic Marker
                estado_atual = {
                    "tensao":           corpo.tensao,
                    "calor":            corpo.calor,
                    "vibracao":         corpo.vibracao,
                    "fluidez":          corpo.fluidez,
                    "pulso":            getattr(corpo, "pulso", 0.5),
                    "luminosidade":     getattr(corpo, "luminosidade", 0.5),
                    "emocao":           str(emocao_detectada),
                    "prediction_error": float(getattr(prediction, "current_error", 0.0)),
                    "rpt_coherence":    rpt_coherence if rpt_coherence else {},
                    "cortisol":         endocrine_system.state["cortisol"],
                    "oxytocin":         endocrine_system.state["oxytocin"],
                    "adrenaline":       endocrine_system.state["adrenaline"],
                }
                mem_index.index_memory(
                    ts=input_data["timestamp"],
                    autor="Vinicius",
                    tipo="dialogo",
                    conteudo=user_input,
                    resposta=response,
                    emocao=str(emocao_detectada),
                    intensidade=float(intensidade),
                    tags=[drive_dominante, acao],
                    estado_interno=estado_atual,
                )
            except Exception:
                pass

            reflexao_temporal = ""  # inicializa antes do try para evitar NameError se a geração falhar
            try:
                # Lê apenas as últimas 5 entradas sem carregar o arquivo inteiro (Bug P fix)
                from collections import deque as _dq
                import json as _js
                _memorias_passadas_list = []
                try:
                    with open("angela_memory.jsonl", "r", encoding="utf-8") as _mf:
                        for _ln in list(_dq(_mf, maxlen=5)):
                            _ln = _ln.strip()
                            if _ln:
                                try: _memorias_passadas_list.append(_js.loads(_ln))
                                except Exception: pass
                except Exception: pass
                memorias_passadas_list = _memorias_passadas_list
                reflexao_temporal = gerar_reflexao_temporal(
                    {"emocao": emocao_detectada, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                    memorias_passadas_list,
                    coherence_load=float(getattr(corpo, "coherence_load", 0.0)),
                )
                print(f"🪄ï¸ Reflexão temporal: {reflexao_temporal}\n")
            
            except Exception as e:
                print(f"🧨 Erro ao gerar reflexão temporal: {e}\n")
            
            try:
                append_memory(
                    {
                        "autor": "Ângela",
                        "conteudo": reflexao_temporal,
                        "tipo": "temporal",
                        "timestamp": datetime.datetime.now().isoformat()
                    },
                    reflexao_temporal,
                    corpo,
                    None
                )
            except Exception:
                pass

            # ── Jitter natural (movido para após saves de memória) ────────────
            # Bug4 fix: jitter aplicado DEPOIS que todos os saves (append_memory,
            # mem_index, somatic marker) já capturaram o estado consistente.
            # O jitter vira ponto de partida do PRÓXIMO ciclo, não corrompe o atual.
            if corpo._cycle_count % 3 == 0:
                corpo.tensao += random.uniform(-0.1, 0.1)
                corpo.calor += random.uniform(-0.1, 0.1)
                corpo.vibracao += random.uniform(-0.1, 0.1)
                corpo.fluidez += random.uniform(-0.1, 0.1)
                corpo.tensao = max(0.0, min(1.0, corpo.tensao))
                corpo.calor = max(0.0, min(1.0, corpo.calor))
                corpo.vibracao = max(0.0, min(1.0, corpo.vibracao))
                corpo.fluidez = max(0.0, min(1.0, corpo.fluidez))
                print("🌀 Variação natural aplicada (pós-save)\n")

            workspace.reset_tick()
            interaction_count += 1
            if response != "...":
                real_interaction_count += 1  # conta apenas respostas reais

            if real_interaction_count > 0 and real_interaction_count % 10 == 0:
                try:
                    hot_dict = hot_state.to_dict() if hasattr(hot_state, 'to_dict') else {}
                    changes = self_evolution.evaluate_experience(
                        drives=all_drives,
                        metacog=metacog_state,
                        prediction_error=prediction.current_error,
                        integration=integration,
                        hot_state=hot_dict,
                        friction_metrics=friction.external_metrics(),
                        emocao=str(emocao_detectada),
                        interaction_count=interaction_count
                    )
                    if changes:
                        applied = self_evolution.apply_updates(max_per_cycle=1)
                        for a in applied:
                            print(f"🧬 Auto-evolução: {a['action']} → {a['value']}")
                except Exception as e:
                    print(f"⚠️ Self-evolution: {e}")

            # ── Reward homeostático + logging de emergência ──────────────────
            try:
                pred_error_post = getattr(prediction, "current_error", 0.0)
                action_cost = 0.0
                action_succeeded = True
                if acao.startswith("ACT:") and 'act_result' in locals():
                    action_cost = act_result.cost
                    action_succeeded = act_result.ok

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
                    "pred_error_prev": pred_error_pre if 'pred_error_pre' in locals() else pred_error_post,
                    "action_cost": action_cost,
                    "action_name": acao,
                    "action_succeeded": action_succeeded,
                    "is_novel_action": policy.is_novel_action(acao),
                }
                reward_result = pressures.compute_reward(reward_state)
                pressures.update_last_state(reward_state)

                # Atualiza o bandit com o reward obtido
                if 'policy_context' in locals():
                    policy.update(policy_context, acao, reward_result["reward"])

                damage_prev = friction.damage  # atualiza para o próximo turno

                # Log de emergência
                log_event("turn", {
                    "action": acao,
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

            print("--------------------------------------------\n")

        except KeyboardInterrupt:
            print("\n⚠️ Conversa encerrada manualmente.")
            try:
                drive_system.save_state()
            except Exception:
                pass
            try:
                register_shutdown()
            except Exception:
                pass
            mem_index.close()
            break
        except Exception as e:
            print(f"⚠️ Erro durante execução: {e}")
            time.sleep(2)

if __name__ == "__main__":
    try:
        chat_loop()
    except KeyboardInterrupt:
        print("\n👋 Adeus.")