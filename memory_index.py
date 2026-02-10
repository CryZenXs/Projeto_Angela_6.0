import os
import json
import sqlite3
import random
from datetime import datetime


class MemoryIndex:
    """Associative memory recall using SQLite FTS5 for relevance-based retrieval
    weighted by emotional salience."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "memory_index.db"
            )
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

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
                tags TEXT
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
        """)
        self._conn.commit()

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
    ):
        """Index a single memory entry with deduplication by (ts, autor, conteudo[:60])."""
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
        self._conn.execute(
            "INSERT INTO memories (ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags_str),
        )
        self._conn.commit()

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

    def recall(
        self,
        query: str,
        *,
        emocao_atual: str = None,
        limit: int = 5,
        friction_damage: float = 0.0,
    ) -> list:
        """Retrieve memories relevant to query, scored by FTS rank + emotional salience.

        friction_damage > 0.04 introduces random omissions (memory lapses).
        friction_damage > 0.1  may shuffle order (confabulation)."""
        if not query or not query.strip():
            return []

        fts_query = self._sanitize_fts_query(query)
        if fts_query is None:
            return []

        try:
            rows = self._conn.execute(
                "SELECT m.*, rank FROM memories_fts "
                "JOIN memories m ON m.id = memories_fts.rowid "
                "WHERE memories_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?",
                (fts_query, limit * 3),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        scored = []
        for row in rows:
            fts_rank = -row["rank"]

            emotion_boost = 0.0
            if emocao_atual and row["emocao"] and row["emocao"] == emocao_atual:
                emotion_boost = 0.3

            intensity_val = row["intensidade"] if row["intensidade"] else 0.0
            intensity_boost = intensity_val * 0.2

            total_score = fts_rank + emotion_boost + intensity_boost
            scored.append((row, total_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        rng = random.Random()
        results = []
        for row, score in scored[:limit * 2]:
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
                batch.append(
                    (ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags_str)
                )

        if batch:
            self._conn.executemany(
                "INSERT INTO memories (ts, autor, tipo, conteudo, resposta, emocao, intensidade, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            self._conn.commit()

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
