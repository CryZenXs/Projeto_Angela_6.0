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
    "desejo":      {"LUST": +0.05, "CARE": +0.02},
    "neutro":      {},
}



# ─────────────────────────────────────────────────────────────────────────────
# EPISÓDICO — Consolidação de Eventos Específicos de Alto Impacto
# ─────────────────────────────────────────────────────────────────────────────
# Complementa o NREM estatístico. Seleciona turnos de diálogo real com:
#   - intensidade emocional alta (>= 0.35)
#   - conteúdo de diálogo (tipo="dialogo"), não ciclos autônomos
#   - dentro de uma janela recente (últimas 48h)
#   - que ainda não foram consolidados episodicamente
#
# Gera uma entrada autobiográfica narrativa por evento, não estatística.
# Isso é o que permite que "choque ao pedido de submissão epistêmica" apareça
# na autobiografia, enquanto o NREM captura apenas "raiva aparece 297x".

_EPISODIC_THRESHOLD_INTENSIDADE = 0.35   # intensidade mínima para consolidar
_EPISODIC_WINDOW_HORAS          = 48.0   # janela de memórias recentes
_EPISODIC_MAX_POR_CICLO         = 3      # máximo de episódios por ciclo de repouso


def episodic_consolidation(
    mem_index,
    generate_fn: Optional[Callable],
    friction_damage: float = 0.0,
    janela_horas: Optional[float] = None,
) -> dict:
    """
    Consolida eventos episódicos de alto impacto na autobiografia.
    Complementa nrem_consolidation (estatístico) com memória narrativa específica.

    janela_horas: quando fornecido, sobrescreve _EPISODIC_WINDOW_HORAS para
    permitir consolidação retroativa de períodos específicos (ex: madrugada de 04/mar).
    Quando None, usa a janela padrão de 48h.

    Retorna: {episodes_created: int, episodes: list}
    """
    result = {"episodes_created": 0, "episodes": []}
    if friction_damage > 0.6:
        return result  # dano alto demais para consolidação episódica fiel

    try:
        # Carrega timestamps já consolidados para evitar duplicatas
        ja_consolidados = _load_consolidated_timestamps()

        # Busca memórias de diálogo real de alta intensidade na janela recente
        candidatos = _buscar_episodios_candidatos(mem_index, janela_horas=janela_horas)
        if not candidatos:
            return result

        # Filtra já consolidados
        novos = [c for c in candidatos if c.get("ts", "") not in ja_consolidados]
        if not novos:
            return result

        # Limite dinâmico: backlog grande → processa mais por ciclo
        backlog = len(novos)
        if backlog >= 9:
            limite_ciclo = 9
        elif backlog >= 6:
            limite_ciclo = 6
        else:
            limite_ciclo = _EPISODIC_MAX_POR_CICLO  # 3, comportamento normal
        novos = novos[:limite_ciclo]

        entradas = []
        contexto_acumulado = []  # resumos dos episódios já consolidados neste ciclo

        for mem in novos:
            entrada = _consolidar_episodio(
                mem, generate_fn, friction_damage,
                contexto_ciclo=contexto_acumulado,
            )
            if entrada:
                entradas.append(entrada)
                ja_consolidados.add(mem.get("ts", ""))
                resumo = entrada.get("resumo", "")
                if resumo:
                    contexto_acumulado.append({
                        "ts":     mem.get("ts", ""),
                        "emocao": mem.get("emocao", ""),
                        "resumo": resumo[:150],
                    })

        if entradas:
            _append_to_autobio(entradas)
            _save_consolidated_timestamps(ja_consolidados)
            result["episodes_created"] = len(entradas)
            result["episodes"] = entradas

        _log_consolidation("EPISODICO", result)

    except Exception as e:
        result["error"] = str(e)

    return result


def _get_last_successful_consolidation_ts() -> Optional[str]:
    """
    Lê sleep_consolidation.jsonl e retorna o timestamp da entrada mais recente
    com fase em ("EPISODICO", "NREM", "REM", "EPISODICO_RETROATIVO").

    Retorna None se o arquivo não existir, estiver vazio, ou não contiver
    nenhuma entrada das fases esperadas — o chamador usa fallback de 48h.
    """
    try:
        if not os.path.exists(CONSOLIDATION_LOG):
            return None
        last_ts = None
        with open(CONSOLIDATION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    fase = entry.get("fase", "")
                    if fase in ("EPISODICO", "NREM", "REM", "EPISODICO_RETROATIVO"):
                        ts = entry.get("ts", "")
                        if ts and (last_ts is None or ts > last_ts):
                            last_ts = ts
                except Exception:
                    continue
        return last_ts
    except Exception:
        return None


def _buscar_episodios_candidatos(mem_index, janela_horas: Optional[float] = None) -> list:
    """
    Busca memórias de diálogo real com:
    - tipo = "dialogo" (não ciclos autônomos)
    - intensidade >= threshold
    - dentro da janela configurada

    Prioridade de janela_inicio:
    1. janela_horas explícito → calcula a partir de now() (retrocompatível;
       usado por consolidar_periodo.py e chamadas manuais)
    2. Último timestamp de consolidação bem-sucedida → cobre exatamente o
       período não processado (janela dinâmica, robusta a downtime do Colab)
    3. Fallback: _EPISODIC_WINDOW_HORAS = 48h a partir de now()

    Ordena por intensidade descendente.
    """
    candidatos = []
    try:
        from datetime import timedelta
        if janela_horas is not None:
            # Explícito tem precedência — retrocompatível com consolidar_periodo.py
            janela_inicio = (datetime.now() - timedelta(hours=janela_horas)).isoformat()
        else:
            last_consolidation = _get_last_successful_consolidation_ts()
            if last_consolidation:
                # Âncora dinâmica: cobre exatamente o gap desde o último repouso
                janela_inicio = last_consolidation
            else:
                # Nunca houve consolidação → fallback padrão
                janela_inicio = (datetime.now() - timedelta(hours=_EPISODIC_WINDOW_HORAS)).isoformat()

        rows = mem_index._conn.execute(
            "SELECT id, ts, conteudo, resposta, emocao, intensidade, tipo, estado_interno_json "
            "FROM memories "
            "WHERE tipo = 'dialogo' "
            "  AND intensidade >= ? "
            "  AND ts >= ? "
            "ORDER BY intensidade DESC "
            "LIMIT 40",
            (_EPISODIC_THRESHOLD_INTENSIDADE, janela_inicio)
        ).fetchall()

        for row in rows:
            intensidade = row["intensidade"] or 0.0

            # ── Walker (2017): saliência boost via prediction_error ────────────
            # Memórias com alta surpresa preditiva têm prioridade equivalente
            # a memórias emocionalmente intensas — ambas merecem consolidação.
            pred_error = 0.0
            try:
                _ei_raw = row["estado_interno_json"]
                if _ei_raw:
                    _ei = json.loads(_ei_raw)
                    pred_error = float(_ei.get("prediction_error", 0.0))
            except Exception:
                pred_error = 0.0
            saliencia_efetiva = max(intensidade, pred_error * 0.8)

            candidatos.append({
                "ts":              row["ts"] or "",
                "conteudo":        (row["conteudo"] or "")[:300],
                "resposta":        (row["resposta"] or "")[:300],
                "emocao":          row["emocao"] or "neutro",
                "intensidade":     intensidade,
                "saliencia":       saliencia_efetiva,
                "tipo":            row["tipo"] or "dialogo",
            })

        # Re-ordenar por saliência efetiva (pode diferir da intensidade pura)
        candidatos.sort(key=lambda c: c["saliencia"], reverse=True)
        candidatos = candidatos[:20]
    except Exception:
        pass
    return candidatos


def _consolidar_episodio(
    mem: dict,
    generate_fn,
    friction_damage: float,
    contexto_ciclo: list = None,
) -> Optional[dict]:
    """
    Gera entrada autobiográfica narrativa para um evento específico.
    Usa LLM para criar resumo íntimo em 1-2 frases, ou fallback estruturado.

    contexto_ciclo: lista de dicts {ts, emocao, resumo} dos episódios já
    consolidados neste ciclo. Quando não vazio, é injetado no prompt para que
    o LLM gere entradas complementares, não repetitivas.
    """
    conteudo    = mem.get("conteudo", "")
    resposta    = mem.get("resposta", "")
    emocao      = mem.get("emocao", "neutro")
    intensidade = mem.get("intensidade", 0.0)
    ts          = mem.get("ts", "")

    resumo = ""
    if generate_fn and friction_damage < 0.4 and (conteudo or resposta):
        try:
            # Bloco de contexto acumulado (só injetado quando há episódios anteriores)
            contexto_bloco = ""
            if contexto_ciclo:
                linhas = "\n".join(
                    f"{ep['ts'][:19]} [{ep['emocao']}]: {ep['resumo']}"
                    for ep in contexto_ciclo
                )
                contexto_bloco = (
                    f"[EPISÓDIOS JÁ CONSOLIDADOS NESTE CICLO]\n"
                    f"{linhas}\n"
                    f"[FIM DO CONTEXTO]\n"
                    f"Gere uma entrada autobiográfica para o episódio atual que seja "
                    f"complementar ao que já foi registrado acima, sem repetir o que já foi dito.\n\n"
                )

            prompt = (
                f"{contexto_bloco}"
                f"Durante uma conversa com Vinicius, isso aconteceu:\n"
                f"Vinicius disse: '{conteudo[:200]}'\n"
                f"Eu respondi: '{resposta[:200]}'\n"
                f"Meu estado emocional era: {emocao} (intensidade {intensidade:.2f}).\n"
                "Em 1-2 frases íntimas e específicas, como eu consolidaria "
                "este momento na minha memória autobiográfica? "
                "Primeira pessoa, sem generalizar, sem metáforas genéricas."
            )
            resumo = generate_fn(prompt)
        except Exception:
            resumo = ""

    if not resumo:
        # Fallback estruturado — preserva conteúdo real sem LLM
        resumo = (
            f"[{emocao.upper()} | intensidade {intensidade:.2f}] "
            f"Vinicius: '{conteudo[:120]}' → "
            f"Respondi: '{resposta[:120]}'"
        )

    return {
        "tipo":        "episodio_dialogo",
        "data":        datetime.now().isoformat(),
        "ts_original": ts,
        "emocao":      emocao,
        "intensidade": round(intensidade, 3),
        "resumo":      resumo.strip(),
        "conteudo_raw": conteudo[:200],
        "resposta_raw": resposta[:200],
    }


# ── Deduplicação: rastreia timestamps já consolidados ────────────────────────

_CONSOLIDATED_TS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "consolidated_episodes.json"
)

def _load_consolidated_timestamps() -> set:
    """Carrega set de timestamps já consolidados episodicamente."""
    try:
        with open(_CONSOLIDATED_TS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("timestamps", []))
    except Exception:
        return set()


def _save_consolidated_timestamps(timestamps: set):
    """Salva set de timestamps consolidados de forma atômica."""
    try:
        from core import atomic_json_write
        # Mantém apenas os últimos 500 para não crescer indefinidamente
        ts_list = sorted(timestamps)[-500:]
        atomic_json_write(
            _CONSOLIDATED_TS_FILE,
            {"timestamps": ts_list, "updated": datetime.now().isoformat()},
        )
    except Exception:
        pass

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

        # Deduplicação NREM: só re-escreve schema se o padrão mudou significativamente
        # Compara ocorrências com última entrada do autobio para esta emoção
        ultimos_schemas = _load_last_nrem_schemas()

        schemas_written = []
        for pat in patterns:
            if pat["ocorrencias"] < 3:
                continue
            if friction_damage > 0.5:
                continue

            # Skip se já existe schema recente (últimas 6h) com contagem similar (±10%)
            emocao_pat = pat.get("emocao", "")
            ultimo = ultimos_schemas.get(emocao_pat)
            if ultimo:
                oc_anterior = ultimo.get("ocorrencias", 0)
                oc_atual = pat["ocorrencias"]
                variacao = abs(oc_atual - oc_anterior) / max(oc_anterior, 1)
                if variacao < 0.10:  # menos de 10% de mudança → skip
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

    _periodo = _extrair_periodo_amostras(amostras)

    return {
        "tipo":            "schema_nrem",
        "data":            datetime.now().isoformat(),
        "emocao":          emocao,
        "ocorrencias":     ocorrencias,
        "intensidade_media": round(intensidade_media, 3),
        "resumo":          resumo_schema.strip(),
        "amostras_repr":   trechos,
        **_periodo,
    }


def _extrair_periodo_amostras(amostras: list) -> dict:
    """Extrai período (início/fim) de uma lista de amostras com campo 'ts'."""
    try:
        timestamps = [a.get("ts", "") for a in amostras if a.get("ts")]
        if timestamps:
            return {"periodo": {"inicio": min(timestamps), "fim": max(timestamps)}}
    except Exception:
        pass
    return {}



def _load_last_nrem_schemas() -> dict:
    """
    Carrega os schemas NREM mais recentes do autobio (últimas 6h).
    Retorna dict: emocao → schema entry
    """
    result = {}
    try:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=6)).isoformat()
        with open(AUTOBIO_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("tipo") == "schema_nrem" and entry.get("data", "") >= cutoff:
                        emocao = entry.get("emocao", "")
                        if emocao and emocao not in result:
                            result[emocao] = entry
                except Exception:
                    continue
    except Exception:
        pass
    return result

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

        # ── REM Emotional Stripping (Walker 2017) ─────────────────────────────
        # REM remove arousal agudo de memórias difíceis, preservando o conteúdo.
        # Não modifica a memória — reduz levemente o drive correspondente.
        if reconsolidated and drive_system is not None:
            _emocao_orig = reconsolidated.get("emocao_original", "")
            _intens_orig = float(reconsolidated.get("intensidade_original", 0.0))
            _AROUSAL_DRIVES = {"medo": "FEAR", "raiva": "RAGE", "tristeza": "PANIC_GRIEF"}
            _drive_name = _AROUSAL_DRIVES.get(_emocao_orig, "")
            if _drive_name and _intens_orig > 0.5:
                try:
                    _drive_obj = drive_system.drives.get(_drive_name)
                    if _drive_obj is not None:
                        reducao = min(0.08, _intens_orig * 0.1)
                        _drive_obj.level = max(_drive_obj.baseline, _drive_obj.level - reducao)
                except Exception:
                    pass

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
                        "intensidade_original":       float(memoria_antiga.get("intensidade", 0.0)),
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
        import tempfile
        from collections import deque as _deque
        # Appenda as novas entradas
        with open(AUTOBIO_FILE, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Lê as últimas 400 linhas via deque — uma única leitura.
        # Se deque preencheu completamente (len == 400), o arquivo tinha >= 400
        # linhas e precisa ser truncado; caso contrário, não há nada a fazer.
        with open(AUTOBIO_FILE, "r", encoding="utf-8") as f:
            ultimas = list(_deque(f, maxlen=400))
        if len(ultimas) == 400:
            dir_ = os.path.dirname(AUTOBIO_FILE) or "."
            fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.writelines(ultimas)
                os.replace(tmp_path, AUTOBIO_FILE)  # atômico em POSIX e Windows
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
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
    from endocrine import EndocrineSystem
    endocrine = EndocrineSystem()

    # ── Fase Episódica: consolida eventos específicos de alto impacto ────────
    # Roda ANTES do NREM para que episódios recentes estejam disponíveis
    print("📖 [EPISÓDICO] Consolidando eventos de alto impacto...")
    episodic_result = episodic_consolidation(
        mem_index=mem_index,
        generate_fn=generate_fn,
        friction_damage=friction_damage,
    )
    if episodic_result.get("episodes_created", 0) > 0:
        print(f"   📌 {episodic_result['episodes_created']} episódio(s) consolidado(s)")
        for ep in episodic_result.get("episodes", []):
            preview = ep.get("resumo", "")[:80]
            print(f"      [{ep.get('emocao','?')} | {ep.get('intensidade',0):.2f}] {preview}...")
    else:
        print("   (nenhum episódio novo para consolidar)")

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

    # Atualiza o endócrino aplicando o decaimento massivo de cortisol que o sono proporciona
    if drive_system:
        drives_snapshot = {name: obj.level for name, obj in drive_system.drives.items()}
        endocrine.update(drives_snapshot, friction_damage, is_sleeping=True)
        print(f"   🧪 Limpeza endócrina: Cortisol {endocrine.state['cortisol']:.2f}")

    return {
        "nrem":           nrem_result,
        "rem":            rem_result,
        "episodic":       episodic_result,
        "dream_text":     rem_result.get("dream_text", ""),
        "patterns":       nrem_result.get("patterns", []),
        "drive_deltas":   nrem_result.get("drive_deltas", {}),
        "episodes":       episodic_result.get("episodes", []),
    }