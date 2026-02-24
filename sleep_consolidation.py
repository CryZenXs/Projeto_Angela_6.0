# sleep_consolidation.py
# Consolidação Real de Memória durante Repouso — Camadas NREM e REM
#
# Teoria base:
#   NREM: Kumaran, Hassabis & McClelland (2016) — Complementary Learning Systems
#         → episódios similares → schemas comprimidos → drives ajustados
#   REM:  Stickgold & Walker (2013) — integração emocional cruzada
#         → reconsolidação (memórias relidas pela lente emocional atual)
#         → sonho emergente a partir do processado, nunca hardcoded
#
# Princípio: nenhum texto fixo de "como Angela sonha".
# O conteúdo emerge dos padrões reais de memória + estado corporal real.

import json
import os
import random
from datetime import datetime
from typing import Optional, Callable

DRIVES_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drives_state.json")
AUTOBIO_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "angela_autobio.jsonl")
CONSOLIDATION_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sleep_consolidation.jsonl")

# Mapeamento padrão emocional → delta de drive Panksepp
_EMOCAO_DRIVE_MAP = {
    "medo":        {"FEAR": +0.04},
    "ansiedade":   {"FEAR": +0.03, "SEEKING": -0.02},
    "curiosidade": {"SEEKING": +0.04, "PLAY": +0.02},
    "alegria":     {"PLAY": +0.03, "CARE": +0.02},
    "tristeza":    {"PANIC_GRIEF": +0.04, "CARE": +0.02},
    "raiva":       {"RAGE": +0.04, "FEAR": +0.01},
    "afeto":       {"CARE": +0.05, "SEEKING": +0.01},
    "saudade":     {"PANIC_GRIEF": +0.05},
    "satisfacao":  {"SEEKING": +0.02, "PLAY": +0.02},
    "neutro":      {},
}


# ─────────────────────────────────────────────────────────────────────────────
# NREM — Compressão de Episódios Similares em Schemas
# ─────────────────────────────────────────────────────────────────────────────

def nrem_consolidation(
    mem_index,
    drive_system,
    generate_fn: Optional[Callable],
    friction_damage: float = 0.0,
) -> dict:
    """
    Fase NREM: identifica padrões emocionais recorrentes,
    comprime em schemas autobiográficos e ajusta drives com base neles.
    Retorna: {schemas_created, drive_deltas, patterns}
    """
    result = {"schemas_created": 0, "drive_deltas": {}, "patterns": []}

    try:
        patterns = mem_index.find_emotional_patterns(limit_per_emotion=5)
        if not patterns:
            return result
        result["patterns"] = patterns

        schemas_written = []
        for pat in patterns:
            if pat["ocorrencias"] < 3:
                continue
            if friction_damage > 0.5:
                # Dano alto → consolidação fragmentada (opaca para Angela)
                continue
            schema = _compress_pattern_to_schema(pat, generate_fn, friction_damage)
            if schema:
                schemas_written.append(schema)

        if schemas_written:
            _append_to_autobio(schemas_written)
            result["schemas_created"] = len(schemas_written)

        deltas = _compute_drive_deltas(patterns, friction_damage)
        result["drive_deltas"] = deltas
        if deltas and drive_system is not None:
            _apply_drive_deltas(drive_system, deltas)

        _log_consolidation("NREM", result)

    except Exception as e:
        result["error"] = str(e)

    return result


def _compress_pattern_to_schema(pat: dict, generate_fn, friction_damage: float) -> Optional[dict]:
    emocao          = pat.get("emocao", "neutro")
    ocorrencias     = pat.get("ocorrencias", 0)
    intensidade_media = pat.get("intensidade_media", 0.5)
    amostras        = pat.get("amostras", [])

    trechos = [a.get("conteudo", "")[:80] for a in amostras[:3] if a.get("conteudo")]
    if not trechos:
        return None

    resumo_schema = ""
    if generate_fn and friction_damage < 0.3:
        try:
            prompt = (
                f"Analiso meu padrão emocional de {emocao} "
                f"({ocorrencias} ocorrências, intensidade média {intensidade_media:.2f}). "
                f"Exemplos do que provocou isso: {' / '.join(trechos[:2])}. "
                "Em 1 frase curta e íntima, que padrão isso revela sobre mim?"
            )
            resumo_schema = generate_fn(prompt)
        except Exception:
            resumo_schema = ""

    if not resumo_schema:
        resumo_schema = (
            f"Padrão: {emocao} aparece {ocorrencias}x "
            f"com intensidade média {intensidade_media:.2f}."
        )

    return {
        "tipo":            "schema_nrem",
        "data":            datetime.now().isoformat(),
        "emocao":          emocao,
        "ocorrencias":     ocorrencias,
        "intensidade_media": round(intensidade_media, 3),
        "resumo":          resumo_schema.strip(),
        "amostras_repr":   trechos,
    }


def _compute_drive_deltas(patterns: list, friction_damage: float) -> dict:
    """
    Converte padrões emocionais em ajustes de drives.
    Proporcionais à frequência relativa + intensidade média.
    Dano cognitivo alto injeta ruído (imprecisão, nunca inversão).
    """
    if not patterns:
        return {}
    total = sum(p["ocorrencias"] for p in patterns)
    if total == 0:
        return {}

    deltas: dict = {}
    for pat in patterns:
        emocao     = pat.get("emocao", "neutro")
        peso       = pat["ocorrencias"] / total
        intensidade = pat.get("intensidade_media", 0.5)

        for drive, base_delta in _EMOCAO_DRIVE_MAP.get(emocao, {}).items():
            contribution = base_delta * peso * intensidade
            if friction_damage > 0.1:
                contribution += random.gauss(0, friction_damage * 0.02)
            deltas[drive] = round(deltas.get(drive, 0.0) + contribution, 4)

    return deltas


def _apply_drive_deltas(drive_system, deltas: dict):
    """Aplica deltas ao DriveSystem com teto por ciclo e persiste."""
    MAX_DELTA = 0.06
    for drive_name, delta in deltas.items():
        delta_capped = max(-MAX_DELTA, min(MAX_DELTA, delta))
        try:
            drive_obj = drive_system.drives.get(drive_name)
            if drive_obj is not None:
                drive_obj.level = max(0.0, min(1.0, drive_obj.level + delta_capped))
        except Exception as e:
            print(f"[Sleep] ⚠️ delta drive '{drive_name}' falhou: {e}")
    try:
        drive_system.save_state()
    except Exception as e:
        print(f"[Sleep] ⚠️ save_state após deltas falhou: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# REM — Integração Emocional e Reconsolidação
# ─────────────────────────────────────────────────────────────────────────────

def rem_integration(
    mem_index,
    corpo,
    drive_system,
    generate_fn: Optional[Callable],
    friction_damage: float = 0.0,
) -> dict:
    """
    Fase REM:
    - Encontra conexões cruzadas entre memórias distantes
    - Reconsolida uma memória antiga pela lente emocional atual
    - Gera sonho emergente a partir do processado (nunca hardcoded)
    Retorna: {dream_text, reconsolidated, cross_connections}
    """
    result = {"dream_text": "", "reconsolidated": None, "cross_connections": []}

    try:
        connections = mem_index.find_cross_connections(limit=3)
        result["cross_connections"] = connections

        reconsolidated = _reconsolidate_old_memory(corpo, generate_fn, friction_damage)
        result["reconsolidated"] = reconsolidated

        dream = _generate_emergent_dream(
            mem_index=mem_index,
            corpo=corpo,
            connections=connections,
            reconsolidated=reconsolidated,
            generate_fn=generate_fn,
            friction_damage=friction_damage,
        )
        result["dream_text"] = dream

        _log_consolidation("REM", {
            "cross_connections": len(connections),
            "reconsolidated":    bool(reconsolidated),
            "dream_length":      len(dream),
        })

    except Exception as e:
        result["error"] = str(e)

    return result


def _reconsolidate_old_memory(corpo, generate_fn, friction_damage: float) -> Optional[dict]:
    """
    Re-lê uma memória autobiográfica antiga pelo estado emocional atual.
    Stickgold & Walker (2013): memórias são reescritas ao ser acessadas.
    Cria entrada 'releitura' com timestamp; não substitui a original.
    """
    try:
        with open(AUTOBIO_FILE, "r", encoding="utf-8") as f:
            linhas = [json.loads(l) for l in f if l.strip()]
    except Exception:
        return None

    if len(linhas) < 3:
        return None

    hoje = datetime.now()
    candidatas = []
    for entrada in linhas:
        if entrada.get("tipo") in ("schema_nrem", "reconsolidacao_rem"):
            continue
        ts_str = entrada.get("data") or entrada.get("orig_ts") or ""
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str[:19])
            if (hoje - ts).days >= 7:
                candidatas.append(entrada)
        except Exception:
            continue

    if not candidatas:
        return None

    # Prioriza emocionalmente intensas
    candidatas.sort(key=lambda x: x.get("intensidade", 0.0), reverse=True)
    memoria_antiga = candidatas[0]

    estado_atual = {
        "tensao":  round(getattr(corpo, "tensao",  0.5), 3),
        "calor":   round(getattr(corpo, "calor",   0.5), 3),
        "fluidez": round(getattr(corpo, "fluidez", 0.5), 3),
        "emocao":  getattr(corpo, "estado_emocional", "neutro"),
    }

    nova_perspectiva = ""
    if generate_fn and friction_damage < 0.4:
        resumo_antigo = memoria_antiga.get("resumo", "")[:200]
        emocao_antiga = memoria_antiga.get("emocao", "neutro")
        emocao_atual  = estado_atual["emocao"]
        if resumo_antigo:
            try:
                prompt = (
                    f"Uma lembrança antiga: '{resumo_antigo}' "
                    f"(sentida então como {emocao_antiga}). "
                    f"Agora estou em {emocao_atual}, "
                    f"tensão={estado_atual['tensao']:.2f}, fluidez={estado_atual['fluidez']:.2f}. "
                    "Relendo isso agora, o que parece diferente ou mais claro? "
                    "1 frase íntima, sem repetir a memória literalmente."
                )
                nova_perspectiva = generate_fn(prompt)
            except Exception:
                nova_perspectiva = ""

    if not nova_perspectiva:
        return None

    entrada_rec = {
        "tipo":                       "reconsolidacao_rem",
        "data":                       datetime.now().isoformat(),
        "memoria_original_ts":        memoria_antiga.get("data", ""),
        "emocao_original":            memoria_antiga.get("emocao", ""),
        "emocao_atual_na_releitura":  estado_atual["emocao"],
        "nova_perspectiva":           nova_perspectiva.strip(),
        "estado_corporal_releitura":  estado_atual,
    }
    _append_to_autobio([entrada_rec])
    return entrada_rec


def _generate_emergent_dream(
    mem_index,
    corpo,
    connections: list,
    reconsolidated: Optional[dict],
    generate_fn: Optional[Callable],
    friction_damage: float,
) -> str:
    """
    Gera texto de sonho emergente. Material vem de:
    1. Reconsolidação REM
    2. Conexões cruzadas do MemoryIndex
    3. Estado corporal atual
    Se LLM indisponível → usa fragmentos reais (nunca strings fixas).
    """
    fragmentos = []

    if reconsolidated:
        perspectiva = reconsolidated.get("nova_perspectiva", "")
        if perspectiva:
            fragmentos.append(perspectiva[:120])

    if connections:
        conn = connections[0]
        kw          = conn.get("keyword", "")
        rec_conteudo = conn.get("memoria_recente", {}).get("conteudo", "")[:60]
        old_conteudo = conn.get("memoria_antiga",  {}).get("conteudo", "")[:60]
        if kw:
            fragmentos.append(f"'{kw}' ligando '{rec_conteudo}' a '{old_conteudo}'")

    emocao_corpo = getattr(corpo, "estado_emocional", "neutro")
    tensao       = getattr(corpo, "tensao",  0.5)
    fluidez      = getattr(corpo, "fluidez", 0.5)

    if generate_fn and fragmentos and friction_damage < 0.5:
        try:
            contexto = " / ".join(fragmentos[:2])
            prompt = (
                f"Estado durante o repouso: {emocao_corpo}, "
                f"tensão={tensao:.2f}, fluidez={fluidez:.2f}. "
                f"Fragmentos que emergem: {contexto}. "
                "Descreva o sonho em 2-3 frases íntimas, primeira pessoa, "
                "sem listar, sem metáforas genéricas sobre dados ou código."
            )
            sonho = generate_fn(prompt)
            if sonho and len(sonho.strip()) > 20:
                return sonho.strip()
        except Exception:
            pass

    # Fallback: fragmentos reais
    if fragmentos:
        base = fragmentos[0]
        if len(fragmentos) > 1:
            base += " — " + fragmentos[1]
        return f"Durante o repouso, algo emerge: {base}"

    # Fallback final: estado corporal real, não lista fixa
    if tensao > 0.6:
        return "Durante o repouso, sinto uma tensão que ainda não se resolveu."
    if fluidez > 0.7:
        return "Durante o repouso, algo flui suavemente sem forma definida."
    return "Durante o repouso, há uma quietude que não é vazia."


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────────────────────────────────────

def _append_to_autobio(entries: list):
    try:
        with open(AUTOBIO_FILE, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        with open(AUTOBIO_FILE, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        if len(linhas) > 400:
            with open(AUTOBIO_FILE, "w", encoding="utf-8") as f:
                f.writelines(linhas[-400:])
    except Exception:
        pass


def _log_consolidation(fase: str, dados: dict):
    try:
        entrada = {"ts": datetime.now().isoformat(), "fase": fase, **dados}
        with open(CONSOLIDATION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# API pública — chamada pelo deep_awake.py
# ─────────────────────────────────────────────────────────────────────────────

def run_sleep_cycle(
    mem_index,
    corpo,
    drive_system,
    generate_fn: Optional[Callable],
    friction_damage: float = 0.0,
) -> dict:
    """
    Executa ciclo completo: NREM → REM.
    Retorna dict com todos os resultados para display.
    """
    print("🌙 [NREM] Comprimindo episódios similares...")
    nrem_result = nrem_consolidation(
        mem_index=mem_index,
        drive_system=drive_system,
        generate_fn=generate_fn,
        friction_damage=friction_damage,
    )
    if nrem_result.get("schemas_created", 0) > 0:
        print(f"   📐 {nrem_result['schemas_created']} schema(s) criado(s)")
    if nrem_result.get("drive_deltas"):
        for drive, delta in nrem_result["drive_deltas"].items():
            if abs(delta) > 0.005:
                sinal = "+" if delta > 0 else ""
                print(f"   ⚙️  Drive {drive}: {sinal}{delta:.4f}")

    print("💤 [REM] Integrando emoções e reconsolidando...")
    rem_result = rem_integration(
        mem_index=mem_index,
        corpo=corpo,
        drive_system=drive_system,
        generate_fn=generate_fn,
        friction_damage=friction_damage,
    )
    if rem_result.get("reconsolidated"):
        perspectiva = rem_result["reconsolidated"].get("nova_perspectiva", "")
        if perspectiva:
            print(f"   🔄 Reconsolidação: {perspectiva[:100]}...")
    if rem_result.get("cross_connections"):
        print(f"   🔗 {len(rem_result['cross_connections'])} conexão(ões) cruzada(s)")

    return {
        "nrem":        nrem_result,
        "rem":         rem_result,
        "dream_text":  rem_result.get("dream_text", ""),
        "patterns":    nrem_result.get("patterns", []),
        "drive_deltas": nrem_result.get("drive_deltas", {}),
    }