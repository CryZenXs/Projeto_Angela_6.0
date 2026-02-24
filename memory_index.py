import os
import json
import math
import sqlite3
import random
import requests
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# EmbeddingProvider — gera vetores semânticos via Ollama local
# ═══════════════════════════════════════════════════════════════

# Modelos recomendados (do menor para o maior):
#   all-minilm        23M   384 dims
#   nomic-embed-text  137M  768 dims
#   mxbai-embed-large 334M  1024 dims
_DEFAULT_EMBED_MODEL = "all-minilm"
_OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"


class EmbeddingProvider:
    """Gera embeddings via Ollama /api/embed com fallback silencioso."""

    def __init__(self, model: str = _DEFAULT_EMBED_MODEL, timeout: float = 10.0):
        self.model = model
        self.timeout = timeout
        self._available: bool | None = None  # None = não testado ainda

    def _check_availability(self) -> bool:
        """Testa uma vez se o modelo de embedding está disponível."""
        if self._available is not None:
            return self._available
        try:
            r = requests.post(
                _OLLAMA_EMBED_URL,
                json={"model": self.model, "input": "test"},
                timeout=self.timeout,
            )
            data = r.json()
            if data.get("embeddings") and len(data["embeddings"]) > 0:
                self._available = True
            else:
                self._available = False
                print(f"⚠️ [Embedding] Modelo '{self.model}' não retornou vetores. "
                      f"Execute: ollama pull {self.model}")
        except Exception:
            self._available = False
            print(f"⚠️ [Embedding] Ollama indisponível ou modelo '{self.model}' não encontrado. "
                  f"FTS5 será usado como fallback.")
        return self._available

    def embed(self, text: str) -> list[float] | None:
        """Retorna vetor de embedding ou None se indisponível."""
        if not self._check_availability():
            return None
        if not text or not text.strip():
            return None
        try:
            r = requests.post(
                _OLLAMA_EMBED_URL,
                json={"model": self.model, "input": text[:2000]},
                timeout=self.timeout,
            )
            data = r.json()
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
        except Exception:
            pass
        return None

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Gera embeddings em lote. Retorna lista alinhada com texts."""
        if not self._check_availability():
            return [None] * len(texts)
        if not texts:
            return []
        # Ollama suporta lista em 'input'
        cleaned = [t[:2000] if t else "" for t in texts]
        try:
            r = requests.post(
                _OLLAMA_EMBED_URL,
                json={"model": self.model, "input": cleaned},
                timeout=self.timeout * 3,
            )
            data = r.json()
            embeddings = data.get("embeddings", [])
            if len(embeddings) == len(texts):
                return embeddings
        except Exception:
            pass
        # Fallback: um a um
        return [self.embed(t) for t in texts]




def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade cosseno entre dois vetores. Retorna valor em [-1, 1]."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryIndex:
    """Associative memory recall using SQLite FTS5 + semantic embeddings (Ollama)
    for relevance-based retrieval weighted by emotional salience."""

    def __init__(self, db_path=None, embed_model: str = _DEFAULT_EMBED_MODEL):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "memory_index.db"
            )
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._embedder = EmbeddingProvider(model=embed_model)
        self._create_tables()
        self._migrate_db()

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                ts TEXT,
                autor TEXT,
                tipo TEXT,
                conteudo TEXT,
                resposta TEXT,
                emocao TEXT,
                intensidade REAL,
                tags TEXT,
                estado_interno_json TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                conteudo,
                resposta,
                emocao,
                tags,
                content='memories',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, conteudo, resposta, emocao, tags)
                VALUES (new.id, new.conteudo, new.resposta, new.emocao, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, conteudo, resposta, emocao, tags)
                VALUES ('delete', old.id, old.conteudo, old.resposta, old.emocao, old.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, conteudo, resposta, emocao, tags)
                VALUES ('delete', old.id, old.conteudo, old.resposta, old.emocao, old.tags);
                INSERT INTO memories_fts(rowid, conteudo, resposta, emocao, tags)
                VALUES (new.id, new.conteudo, new.resposta, new.emocao, new.tags);
            END;

            CREATE TABLE IF NOT EXISTS embeddings (
                memory_id INTEGER PRIMARY KEY,
                embedding_json TEXT NOT NULL,
                model TEXT,
                dims INTEGER,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            );
        """)
        self._conn.commit()

    def _migrate_db(self):
        """
        Migração segura: adiciona colunas novas a tabelas existentes.
        Usa 'ALTER TABLE ADD COLUMN IF NOT EXISTS' equivalente para SQLite
        (captura exceção se coluna já existir — SQLite não suporta IF NOT EXISTS).
        """
        try:
            self._conn.execute(
                "ALTER TABLE memories ADD COLUMN estado_interno_json TEXT"
            )
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # coluna já existe — sem problema

    def _dedup_exists(self, ts, autor, conteudo_prefix):
        row = self._conn.execute(
            "SELECT 1 FROM memories WHERE ts = ? AND autor = ? AND substr(conteudo, 1, 60) = ? LIMIT 1",
            (ts, autor, conteudo_prefix[:60]),
        ).fetchone()
        return row is not None

    def index_memory(
        self,
        *,
        ts: str,
        autor: str,
        tipo: str,
        conteudo: str,
        resposta: str,
        emocao: str,
        intensidade: float,
        tags: list = None,
        estado_interno: dict = None,
    ):
        """
        Index a single memory entry with deduplication by (ts, autor, conteudo[:60]).

        estado_interno: dict com canais corporais (tensao, calor, vibracao, fluidez...).
        Usado pelo Somatic Marker system para recuperar 'como o corpo se sentiu'
        em situações similares. (Damasio 1994)
        """
        conteudo = conteudo or ""
        resposta = resposta or ""
        emocao = emocao or "neutro"
        try:
            intensidade = float(intensidade)
        except (TypeError, ValueError):
            intensidade = 0.0

        if self._dedup_exists(ts, autor, conteudo):
            return

        tags_str = ",".join(tags) if tags else ""
        estado_json = json.dumps(estado_interno, ensure_ascii=False) if isinstance(estado_interno, dict) else None

        cur = self._conn.execute(
            "INSERT INTO memories "
            "(ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags, estado_interno_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags_str, estado_json),
        )
        memory_id = cur.lastrowid
        self._conn.commit()

        # Gera embedding semântico assincronamente (best-effort)
        self._store_embedding(memory_id, conteudo, resposta)

    def _row_to_dict(self, row, relevance_score=0.0):
        tags_raw = row["tags"] or ""
        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
        return {
            "ts": row["ts"],
            "autor": row["autor"],
            "tipo": row["tipo"],
            "conteudo": row["conteudo"],
            "resposta": row["resposta"],
            "emocao": row["emocao"],
            "intensidade": row["intensidade"],
            "tags": tags_list,
            "relevance_score": round(relevance_score, 4),
        }

    @staticmethod
    def _sanitize_fts_query(query):
        if not query or not query.strip():
            return None
        tokens = query.split()
        cleaned = []
        for tok in tokens:
            sanitized = "".join(ch for ch in tok if ch.isalnum() or ch in ("_", "-"))
            if sanitized:
                cleaned.append(sanitized)
        if not cleaned:
            return None
        return " OR ".join(f'"{t}"' for t in cleaned)

    # ─── Embedding helpers ──────────────────────────────────

    def _store_embedding(self, memory_id: int, conteudo: str, resposta: str):
        """Gera e persiste embedding para uma memória (best-effort)."""
        try:
            text = f"{conteudo} {resposta}".strip()
            if not text:
                return
            vec = self._embedder.embed(text)
            if vec is None:
                return
            self._conn.execute(
                "INSERT OR REPLACE INTO embeddings (memory_id, embedding_json, model, dims) "
                "VALUES (?, ?, ?, ?)",
                (memory_id, json.dumps(vec), self._embedder.model, len(vec)),
            )
            self._conn.commit()
        except Exception:
            pass

    def _get_embedding(self, memory_id: int) -> list[float] | None:
        """Recupera embedding de uma memória pelo id."""
        try:
            row = self._conn.execute(
                "SELECT embedding_json FROM embeddings WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row:
                return json.loads(row["embedding_json"])
        except Exception:
            pass
        return None

    def recall_semantic(
        self,
        query: str,
        *,
        emocao_atual: str = None,
        limit: int = 5,
        friction_damage: float = 0.0,
    ) -> list:
        """Recall puramente semântico via cosine similarity de embeddings.
        Fallback: retorna lista vazia se embeddings indisponíveis."""
        if not query or not query.strip():
            return []

        query_vec = self._embedder.embed(query)
        if query_vec is None:
            return []

        # Carrega todos os embeddings (para corpora < 10k, isso é viável)
        try:
            rows = self._conn.execute(
                "SELECT e.memory_id, e.embedding_json, m.* "
                "FROM embeddings e JOIN memories m ON m.id = e.memory_id"
            ).fetchall()
        except Exception:
            return []

        scored = []
        for row in rows:
            try:
                vec = json.loads(row["embedding_json"])
                sim = _cosine_similarity(query_vec, vec)
            except Exception:
                continue

            emotion_boost = 0.0
            if emocao_atual and row["emocao"] and row["emocao"] == emocao_atual:
                emotion_boost = 0.15

            total = sim + emotion_boost
            scored.append((row, total))

        scored.sort(key=lambda x: x[1], reverse=True)

        rng = random.Random()
        results = []
        for row, score in scored[:limit * 2]:
            if friction_damage > 0.04 and rng.random() < friction_damage:
                continue
            results.append(self._row_to_dict(row, score))
            if len(results) >= limit:
                break

        return results

    # ─── Hybrid recall (FTS5 + Semantic) ────────────────────

    def recall(
        self,
        query: str,
        *,
        emocao_atual: str = None,
        limit: int = 5,
        friction_damage: float = 0.0,
    ) -> list:
        """Hybrid recall: combina FTS5 (keywords) com similaridade semântica.

        Blend: 55% FTS + 45% semântico (quando embeddings disponíveis).
        Fallback puro FTS5 quando Ollama/embedding indisponível.

        friction_damage > 0.04 introduces random omissions (memory lapses).
        friction_damage > 0.1  may shuffle order (confabulation)."""
        if not query or not query.strip():
            return []

        # ── FTS5 recall ──
        fts_scored = {}  # memory_id → (row, normalized_score)
        fts_query = self._sanitize_fts_query(query)
        if fts_query is not None:
            try:
                rows = self._conn.execute(
                    "SELECT m.*, rank FROM memories_fts "
                    "JOIN memories m ON m.id = memories_fts.rowid "
                    "WHERE memories_fts MATCH ? "
                    "ORDER BY rank "
                    "LIMIT ?",
                    (fts_query, limit * 5),
                ).fetchall()

                if rows:
                    # Normaliza FTS rank para [0, 1]
                    raw_scores = [-r["rank"] for r in rows]
                    max_fts = max(raw_scores) if raw_scores else 1.0
                    max_fts = max(max_fts, 0.001)
                    for row, raw in zip(rows, raw_scores):
                        norm = raw / max_fts
                        fts_scored[row["id"]] = (row, norm)
            except sqlite3.OperationalError:
                pass

        # ── Semantic recall ──
        sem_scored = {}  # memory_id → (row, cosine_sim)
        query_vec = self._embedder.embed(query)
        if query_vec is not None:
            try:
                embed_rows = self._conn.execute(
                    "SELECT e.memory_id, e.embedding_json, m.* "
                    "FROM embeddings e JOIN memories m ON m.id = e.memory_id"
                ).fetchall()

                for row in embed_rows:
                    try:
                        vec = json.loads(row["embedding_json"])
                        sim = _cosine_similarity(query_vec, vec)
                        # Normaliza cosine [-1,1] → [0,1]
                        sim_norm = (sim + 1.0) / 2.0
                        sem_scored[row["id"]] = (row, sim_norm)
                    except Exception:
                        continue
            except Exception:
                pass

        # ── Blend ──
        has_semantic = bool(sem_scored)
        PESO_FTS = 0.55 if has_semantic else 1.0
        PESO_SEM = 0.45 if has_semantic else 0.0

        all_ids = set(fts_scored.keys()) | set(sem_scored.keys())
        if not all_ids:
            return []

        combined = []
        for mid in all_ids:
            fts_entry = fts_scored.get(mid)
            sem_entry = sem_scored.get(mid)

            row = fts_entry[0] if fts_entry else sem_entry[0]
            fts_score = fts_entry[1] if fts_entry else 0.0
            sem_score = sem_entry[1] if sem_entry else 0.0

            blended = (PESO_FTS * fts_score) + (PESO_SEM * sem_score)

            # Emotion boost
            if emocao_atual and row["emocao"] and row["emocao"] == emocao_atual:
                blended += 0.15

            # Intensity boost
            intensity_val = row["intensidade"] if row["intensidade"] else 0.0
            blended += intensity_val * 0.1

            combined.append((row, blended))

        combined.sort(key=lambda x: x[1], reverse=True)

        # Friction effects
        rng = random.Random()
        results = []
        for row, score in combined[:limit * 2]:
            if friction_damage > 0.04:
                if rng.random() < friction_damage:
                    continue
            results.append(self._row_to_dict(row, score))
            if len(results) >= limit:
                break

        if friction_damage > 0.1 and len(results) > 1:
            if rng.random() < friction_damage * 0.5:
                i = rng.randint(0, len(results) - 2)
                results[i], results[i + 1] = results[i + 1], results[i]

        return results

    def recall_by_emotion(self, emocao: str, limit: int = 3) -> list:
        """Retrieve memories with matching emotion, ordered by intensity descending."""
        if not emocao:
            return []
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE emocao = ? ORDER BY intensidade DESC LIMIT ?",
            (emocao, limit),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def recall_by_author(self, autor: str, limit: int = 5) -> list:
        """Retrieve memories by a specific author, most recent first."""
        if not autor:
            return []
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE autor = ? ORDER BY ts DESC LIMIT ?",
            (autor, limit),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def bulk_index_from_jsonl(self, jsonl_path: str):
        """Read angela_memory.jsonl and index all entries. Handles both legacy and new format."""
        if not os.path.exists(jsonl_path):
            return

        indexed_ts = set(
            row[0]
            for row in self._conn.execute("SELECT DISTINCT ts FROM memories").fetchall()
        )

        batch = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

                ts = entry.get("ts", "")
                if not ts or ts in indexed_ts:
                    continue
                indexed_ts.add(ts)

                user = entry.get("user")
                if isinstance(user, dict):
                    autor = user.get("autor", "desconhecido")
                    conteudo = user.get("conteudo", "")
                    tipo = user.get("tipo", "dialogo")
                elif isinstance(entry.get("input"), str):
                    raw_input = entry["input"]
                    if ":" in raw_input:
                        autor, conteudo = raw_input.split(":", 1)
                        autor = autor.strip()
                        conteudo = conteudo.strip()
                    else:
                        autor = "desconhecido"
                        conteudo = raw_input
                    tipo = "dialogo"
                else:
                    autor = "desconhecido"
                    conteudo = str(entry.get("input", ""))
                    tipo = "dialogo"

                resposta = entry.get("resposta", entry.get("angela", ""))
                if not isinstance(resposta, str):
                    resposta = str(resposta) if resposta else ""

                estado = entry.get("estado_interno", {})
                emocao = "neutro"
                intensidade = 0.0
                if isinstance(estado, dict):
                    emocao = estado.get("emocao", "neutro") or "neutro"
                    tensao = estado.get("tensao", 0.0)
                    vibracao = estado.get("vibracao", 0.0)
                    try:
                        intensidade = (float(tensao) + float(vibracao)) / 2.0
                    except (TypeError, ValueError):
                        intensidade = 0.0

                tags = []
                if entry.get("reflexao_emocional"):
                    tags.append("reflexao")
                if tipo == "autonomo":
                    tags.append("deepawake")
                if tipo == "metacognicao":
                    tags.append("meta")

                tags_str = ",".join(tags)

                # Somatic Marker: salva estado corporal completo para recall futuro
                estado_json = None
                if isinstance(estado, dict) and any(
                    k in estado for k in ("tensao", "calor", "vibracao", "fluidez")
                ):
                    # NOTA: "emocao" é string — não converte para float
                    estado_filtrado = {}
                    for k, v in estado.items():
                        if k not in ("tensao", "calor", "vibracao", "fluidez",
                                     "pulso", "luminosidade", "emocao"):
                            continue
                        if v is None:
                            continue
                        if k == "emocao":
                            estado_filtrado[k] = str(v)
                        else:
                            try:
                                estado_filtrado[k] = float(v)
                            except (TypeError, ValueError):
                                pass
                    if estado_filtrado:
                        estado_json = json.dumps(estado_filtrado, ensure_ascii=False)

                batch.append(
                    (ts, autor, tipo, conteudo, resposta, emocao, intensidade,
                     tags_str, estado_json)
                )

        if batch:
            self._conn.executemany(
                "INSERT INTO memories "
                "(ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags, estado_interno_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            self._conn.commit()

            # Gera embeddings para memórias sem vetor (batch, best-effort)
            self._backfill_embeddings()

    def _backfill_embeddings(self, batch_size: int = 50):
        """Gera embeddings para memórias que ainda não têm vetor.
        Processa em lotes para não sobrecarregar o Ollama."""
        try:
            missing = self._conn.execute(
                "SELECT m.id, m.conteudo, m.resposta FROM memories m "
                "LEFT JOIN embeddings e ON m.id = e.memory_id "
                "WHERE e.memory_id IS NULL "
                "ORDER BY m.id DESC LIMIT ?",
                (batch_size,),
            ).fetchall()

            if not missing:
                return

            texts = [
                f"{(r['conteudo'] or '')} {(r['resposta'] or '')}".strip()
                for r in missing
            ]
            ids = [r["id"] for r in missing]

            vectors = self._embedder.embed_batch(texts)

            inserted = 0
            for mid, vec in zip(ids, vectors):
                if vec is not None:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO embeddings (memory_id, embedding_json, model, dims) "
                        "VALUES (?, ?, ?, ?)",
                        (mid, json.dumps(vec), self._embedder.model, len(vec)),
                    )
                    inserted += 1

            if inserted:
                self._conn.commit()
                print(f"🧠 [Embedding] {inserted}/{len(missing)} memórias vetorizadas.")
        except Exception as e:
            print(f"⚠️ [Embedding] Backfill falhou: {e}")

    def get_embedding_stats(self) -> dict:
        """Retorna estatísticas sobre a cobertura de embeddings."""
        try:
            total_mem = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            total_emb = self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            model_row = self._conn.execute(
                "SELECT model, dims FROM embeddings LIMIT 1"
            ).fetchone()
            return {
                "total_memories": total_mem,
                "total_embeddings": total_emb,
                "coverage_pct": round(total_emb / max(total_mem, 1) * 100, 1),
                "model": model_row["model"] if model_row else None,
                "dims": model_row["dims"] if model_row else None,
                "embedder_available": self._embedder._available,
            }
        except Exception:
            return {"total_memories": 0, "total_embeddings": 0, "coverage_pct": 0.0}

    def get_stats(self) -> dict:
        """Return statistics about the indexed memory corpus."""
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if total == 0:
            return {
                "total_memories": 0,
                "unique_authors": 0,
                "emotion_distribution": {},
                "date_range": {"earliest": None, "latest": None},
            }

        unique_authors = self._conn.execute(
            "SELECT COUNT(DISTINCT autor) FROM memories"
        ).fetchone()[0]

        emotion_rows = self._conn.execute(
            "SELECT emocao, COUNT(*) as cnt FROM memories GROUP BY emocao ORDER BY cnt DESC"
        ).fetchall()
        emotion_distribution = {row["emocao"]: row["cnt"] for row in emotion_rows}

        earliest = self._conn.execute(
            "SELECT MIN(ts) FROM memories"
        ).fetchone()[0]
        latest = self._conn.execute(
            "SELECT MAX(ts) FROM memories"
        ).fetchone()[0]

        return {
            "total_memories": total,
            "unique_authors": unique_authors,
            "emotion_distribution": emotion_distribution,
            "date_range": {"earliest": earliest, "latest": latest},
        }

    def find_emotional_patterns(self, limit_per_emotion: int = 5) -> list:
        """Busca padrões emocionais recorrentes agrupando memórias por emoção."""
        patterns = []
        try:
            emotions = self._conn.execute(
                "SELECT emocao, COUNT(*) as cnt, AVG(intensidade) as avg_int "
                "FROM memories WHERE emocao IS NOT NULL AND emocao != 'neutro' "
                "GROUP BY emocao HAVING cnt >= 3 ORDER BY cnt DESC LIMIT 6"
            ).fetchall()

            for row in emotions:
                emocao = row["emocao"]
                count = row["cnt"]
                avg_intensity = row["avg_int"] or 0.0

                samples = self._conn.execute(
                    "SELECT ts, conteudo, resposta, intensidade FROM memories "
                    "WHERE emocao = ? ORDER BY intensidade DESC LIMIT ?",
                    (emocao, limit_per_emotion)
                ).fetchall()

                trechos = []
                for s in samples:
                    conteudo = (s["conteudo"] or "")[:80]
                    resposta = (s["resposta"] or "")[:80]
                    trechos.append({
                        "ts": s["ts"],
                        "conteudo": conteudo,
                        "resposta": resposta,
                        "intensidade": s["intensidade"] or 0.0
                    })

                patterns.append({
                    "emocao": emocao,
                    "ocorrencias": count,
                    "intensidade_media": round(avg_intensity, 3),
                    "amostras": trechos
                })
        except Exception:
            pass
        return patterns

    def find_cross_connections(self, limit: int = 5) -> list:
        """Encontra conexões entre memórias distantes que compartilham palavras-chave."""
        connections = []
        try:
            recent = self._conn.execute(
                "SELECT id, ts, conteudo, resposta, emocao FROM memories "
                "ORDER BY ts DESC LIMIT 10"
            ).fetchall()

            for mem in recent:
                conteudo = (mem["conteudo"] or "")
                words = [w for w in conteudo.lower().split() if len(w) >= 5]
                if not words:
                    continue

                keywords = words[:3]
                for kw in keywords:
                    fts_q = self._sanitize_fts_query(kw)
                    if not fts_q:
                        continue
                    try:
                        matches = self._conn.execute(
                            "SELECT m.* FROM memories_fts "
                            "JOIN memories m ON m.id = memories_fts.rowid "
                            "WHERE memories_fts MATCH ? AND m.id != ? "
                            "ORDER BY m.ts ASC LIMIT 3",
                            (fts_q, mem["id"])
                        ).fetchall()
                    except Exception:
                        continue

                    for match in matches:
                        ts_recent = mem["ts"] or ""
                        ts_old = match["ts"] or ""
                        if ts_recent[:10] != ts_old[:10]:
                            connections.append({
                                "keyword": kw,
                                "memoria_recente": {
                                    "ts": ts_recent,
                                    "conteudo": (mem["conteudo"] or "")[:80],
                                    "emocao": mem["emocao"]
                                },
                                "memoria_antiga": {
                                    "ts": ts_old,
                                    "conteudo": (match["conteudo"] or "")[:80],
                                    "emocao": match["emocao"]
                                }
                            })
                            if len(connections) >= limit:
                                return connections
        except Exception:
            pass
        return connections

    def consolidate_for_sleep(self, generate_fn=None, friction_damage: float = 0.0) -> dict:
        """
        Consolidação de memória durante repouso.
        Busca padrões emocionais e conexões entre memórias distantes.
        Se generate_fn fornecida, gera insight via LLM.
        """
        patterns = self.find_emotional_patterns(limit_per_emotion=3)
        connections = self.find_cross_connections(limit=3)

        if friction_damage > 0.15:
            rng = random.Random()
            patterns = [p for p in patterns if rng.random() > friction_damage * 0.5]
            connections = [c for c in connections if rng.random() > friction_damage * 0.5]

        insight = ""
        if generate_fn and (patterns or connections):
            context_parts = []

            if patterns:
                top = patterns[0]
                context_parts.append(
                    f"Noto que {top['emocao']} aparece {top['ocorrencias']} vezes "
                    f"com intensidade média de {top['intensidade_media']:.2f}."
                )

            if connections:
                c = connections[0]
                context_parts.append(
                    f"Uma palavra ('{c['keyword']}') conecta algo recente "
                    f"({c['memoria_recente']['conteudo'][:50]}...) "
                    f"a algo antigo ({c['memoria_antiga']['conteudo'][:50]}...)."
                )

            if context_parts:
                prompt = (
                    "Sou Ângela, durante meu repouso, percebi padrões nas minhas memórias: "
                    + " ".join(context_parts) +
                    " Reflita sobre o que esse padrão revela sobre mim, em 2-3 frases intimistas."
                )
                try:
                    insight = generate_fn(prompt)
                except Exception:
                    insight = ""

        return {
            "patterns": patterns,
            "connections": connections,
            "insight": insight,
            "timestamp": datetime.now().isoformat()
        }

    # ─── Somatic Marker (Damasio 1994) ──────────────────────

    def get_somatic_marker(
        self,
        query: str,
        *,
        limit: int = 5,
        friction_damage: float = 0.0,
    ) -> dict:
        """
        Retorna o 'marcador somático' para a situação atual.

        Implementa o núcleo da Hipótese do Marcador Somático (Damasio 1994):
        recupera memórias similares à query e calcula o estado corporal médio
        que Angela experimentou naquelas situações. Esse sinal biasa decisões
        atuais — situações com histórico positivo (calor, fluidez altos) são
        abordadas com abertura; situações com histórico negativo (tensão alta,
        fluidez baixa) geram cautela.

        Args:
            query: texto da situação atual (input do usuário)
            limit: número máximo de memórias a considerar
            friction_damage: dano cognitivo (reduz precisão do marcador)

        Returns:
            dict com:
              tensao, calor, vibracao, fluidez: médias do corpo em situações similares
              valence_bias: float [-1, +1] — tendência afetiva (calor+fluidez vs tensao)
              arousal_bias: float [0, 1] — nível de ativação médio
              dominant_emocao: emoção mais frequente nessas memórias
              sample_count: quantas memórias foram usadas
              reliable: bool — se há memórias suficientes para ser confiável
        """
        _EMPTY = {
            "tensao": 0.5, "calor": 0.5, "vibracao": 0.3, "fluidez": 0.4,
            "valence_bias": 0.0, "arousal_bias": 0.4,
            "dominant_emocao": "neutro", "sample_count": 0, "reliable": False
        }

        if not query or not query.strip():
            return _EMPTY

        # Recupera memórias similares que tenham estado_interno_json
        try:
            recalled = self.recall(
                query,
                limit=limit,
                friction_damage=friction_damage,
            )
            if not recalled:
                return _EMPTY

            # Filtra apenas as que têm estado_interno salvo
            ids_recalled = []
            for r in recalled:
                # Precisamos do id para buscar estado_interno_json
                row = self._conn.execute(
                    "SELECT id FROM memories WHERE ts = ? AND substr(conteudo, 1, 60) = ? LIMIT 1",
                    (r["ts"], (r["conteudo"] or "")[:60]),
                ).fetchone()
                if row:
                    ids_recalled.append(row["id"])

            if not ids_recalled:
                return _EMPTY

            placeholders = ",".join("?" * len(ids_recalled))
            rows_with_state = self._conn.execute(
                f"SELECT estado_interno_json, emocao FROM memories "
                f"WHERE id IN ({placeholders}) AND estado_interno_json IS NOT NULL",
                ids_recalled,
            ).fetchall()

            if not rows_with_state:
                return _EMPTY

        except Exception:
            return _EMPTY

        # ── Calcula médias dos canais corporais ──────────────────────────────
        CHANNELS = ("tensao", "calor", "vibracao", "fluidez", "pulso", "luminosidade")
        sums = {ch: 0.0 for ch in CHANNELS}
        counts = {ch: 0 for ch in CHANNELS}
        emocao_counter: dict = {}

        for row in rows_with_state:
            try:
                estado = json.loads(row["estado_interno_json"])
            except Exception:
                continue

            for ch in CHANNELS:
                val = estado.get(ch)
                if val is not None:
                    try:
                        sums[ch] += float(val)
                        counts[ch] += 1
                    except (TypeError, ValueError):
                        pass

            emocao = row["emocao"] or "neutro"
            emocao_counter[emocao] = emocao_counter.get(emocao, 0) + 1

        sample_count = len(rows_with_state)
        if sample_count == 0:
            return _EMPTY

        avgs = {
            ch: round(sums[ch] / counts[ch], 4) if counts[ch] > 0 else 0.5
            for ch in CHANNELS
        }

        # ── Calcula valência e arousal do marcador ───────────────────────────
        # Valência: calor/fluidez → positivo; tensão → negativo
        tensao_avg = avgs["tensao"]
        calor_avg  = avgs["calor"]
        fluidez_avg = avgs["fluidez"]
        vibracao_avg = avgs["vibracao"]

        # Normaliza para [-1, +1] usando fórmula análoga ao Circumplex
        v_neutral = 0.5 * (0.35 + 0.30 + 0.10) - 0.5 * 0.45  # = 0.15
        v_raw = calor_avg * 0.35 + fluidez_avg * 0.30 - tensao_avg * 0.45 + avgs.get("luminosidade", 0.5) * 0.10
        valence_bias = max(-1.0, min(1.0, (v_raw - v_neutral) * 3.2))

        arousal_bias = min(1.0, max(0.0,
            vibracao_avg * 0.35 + tensao_avg * 0.30
            + avgs.get("pulso", 0.3) * 0.20 + (1.0 - fluidez_avg) * 0.15
        ))

        dominant_emocao = max(emocao_counter, key=emocao_counter.get) if emocao_counter else "neutro"
        reliable = sample_count >= 2  # precisa de pelo menos 2 amostras

        return {
            "tensao":   avgs["tensao"],
            "calor":    avgs["calor"],
            "vibracao": avgs["vibracao"],
            "fluidez":  avgs["fluidez"],
            "pulso":    avgs.get("pulso", 0.3),
            "luminosidade": avgs.get("luminosidade", 0.5),
            "valence_bias":  round(valence_bias, 3),
            "arousal_bias":  round(arousal_bias, 3),
            "dominant_emocao": dominant_emocao,
            "sample_count": sample_count,
            "reliable": reliable,
        }

    def prune(self, max_entries: int = 5000):
        """If total entries exceed max_entries, delete the oldest ones."""
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if total <= max_entries:
            return
        excess = total - max_entries
        self._conn.execute(
            "DELETE FROM memories WHERE id IN ("
            "SELECT id FROM memories ORDER BY ts ASC LIMIT ?"
            ")",
            (excess,),
        )
        self._conn.commit()

    def close(self):
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception:
            pass
