"""SQLite episodic memory + semantic store using our tiny encoder embeddings."""

from __future__ import annotations

import json
import math
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from rosa_brain.config import settings


EmbedFn = Callable[[str], list[float]]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class MemoryStore:
    def __init__(self, db_path: Path | None = None, embed_fn: EmbedFn | None = None) -> None:
        self.db_path = Path(db_path or settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embed_fn = embed_fn
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS semantics (
                    id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    embedding_json TEXT NOT NULL,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS outcomes (
                    id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    action TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    detail TEXT NOT NULL,
                    lesson TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_episodes_ts ON episodes(ts);
                CREATE INDEX IF NOT EXISTS idx_semantics_ts ON semantics(ts);
                """
            )

    def set_embedder(self, embed_fn: EmbedFn) -> None:
        self.embed_fn = embed_fn

    def add_episode(
        self,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> str:
        eid = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO episodes(id, ts, role, content, meta_json) VALUES (?,?,?,?,?)",
                (eid, time.time(), role, content, json.dumps(meta or {}, ensure_ascii=False)),
            )
        return eid

    def recent_episodes(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, role, content, meta_json FROM episodes ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "ts": r["ts"],
                    "role": r["role"],
                    "content": r["content"],
                    "meta": json.loads(r["meta_json"] or "{}"),
                }
            )
        return list(reversed(out))

    def add_semantic(
        self,
        text: str,
        source: str = "manual",
        embedding: list[float] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> str:
        if embedding is None:
            if self.embed_fn is None:
                # deterministic fallback hash-embedding so memory still works pre-model
                embedding = self._hash_embed(text)
            else:
                embedding = self.embed_fn(text)
        sid = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO semantics(id, ts, text, source, embedding_json, meta_json) "
                "VALUES (?,?,?,?,?,?)",
                (
                    sid,
                    time.time(),
                    text,
                    source,
                    json.dumps(embedding),
                    json.dumps(meta or {}, ensure_ascii=False),
                ),
            )
        return sid

    def search_semantic(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self.embed_fn is None:
            q = self._hash_embed(query)
        else:
            q = self.embed_fn(query)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, text, source, embedding_json, meta_json FROM semantics"
            ).fetchall()
        scored: list[tuple[float, dict[str, Any]]] = []
        for r in rows:
            emb = json.loads(r["embedding_json"])
            score = _cosine(q, emb)
            scored.append(
                (
                    score,
                    {
                        "id": r["id"],
                        "ts": r["ts"],
                        "text": r["text"],
                        "source": r["source"],
                        "score": score,
                        "meta": json.loads(r["meta_json"] or "{}"),
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:top_k]]

    def add_outcome(
        self, action: str, success: bool, detail: str, lesson: str = ""
    ) -> str:
        oid = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO outcomes(id, ts, action, success, detail, lesson) "
                "VALUES (?,?,?,?,?,?)",
                (oid, time.time(), action, 1 if success else 0, detail, lesson),
            )
        if lesson.strip():
            self.add_semantic(lesson, source="lesson", meta={"action": action, "success": success})
        return oid

    def recent_outcomes(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, action, success, detail, lesson FROM outcomes "
                "ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "ts": r["ts"],
                "action": r["action"],
                "success": bool(r["success"]),
                "detail": r["detail"],
                "lesson": r["lesson"],
            }
            for r in rows
        ]

    @staticmethod
    def _hash_embed(text: str, dim: int = 128) -> list[float]:
        vec = [0.0] * dim
        data = text.encode("utf-8", errors="replace") or b" "
        for i, b in enumerate(data):
            vec[i % dim] += ((b / 255.0) * 2 - 1) / (1 + i * 0.01)
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
