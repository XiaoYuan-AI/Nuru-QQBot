import hashlib
import math
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from loguru import logger


@dataclass
class MemoryRecord:
    id: int
    scope_type: str
    scope_id: str
    user_id: str
    user_name: str
    role: str
    content: str
    content_type: str
    created_at: float
    mood_label: str
    personality: str


@dataclass
class MemorySearchResult:
    record: MemoryRecord
    score: float


class MemoryStore:
    def __init__(
        self,
        sqlite_path: str,
        chroma_path: str,
        collection_name: str,
        embedding_dimension: int = 384,
        enable_chroma: bool = True,
    ) -> None:
        self.sqlite_path = sqlite_path
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self._conn = _connect(sqlite_path)
        self._create_tables()
        self._collection = None
        if enable_chroma:
            self._collection = self._create_chroma_collection()

    @property
    def chroma_enabled(self) -> bool:
        return self._collection is not None

    def close(self) -> None:
        self._conn.close()

    def add_message(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
        user_name: str,
        role: str,
        content: str,
        content_type: str = "text",
        embedding: Optional[Sequence[float]] = None,
        mood_label: str = "balanced",
        personality: str = "neuro",
        created_at: Optional[float] = None,
    ) -> int:
        timestamp = created_at if created_at is not None else time.time()
        cursor = self._conn.execute(
            """
            INSERT INTO conversation_messages (
                scope_type, scope_id, user_id, user_name, role, content,
                content_type, created_at, mood_label, personality
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope_type,
                scope_id,
                user_id,
                user_name,
                role,
                content,
                content_type,
                timestamp,
                mood_label,
                personality,
            ),
        )
        message_id = int(cursor.lastrowid)
        self._upsert_profile(user_id, user_name, timestamp)
        self._conn.commit()
        self._add_to_chroma(
            message_id=message_id,
            scope_type=scope_type,
            scope_id=scope_id,
            user_id=user_id,
            role=role,
            content=content,
            embedding=embedding,
            created_at=timestamp,
        )
        return message_id

    def recent_messages(
        self,
        scope_type: str,
        scope_id: str,
        limit: int = 12,
    ) -> List[MemoryRecord]:
        rows = self._conn.execute(
            """
            SELECT * FROM conversation_messages
            WHERE scope_type = ? AND scope_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (scope_type, scope_id, limit),
        ).fetchall()
        return [_record_from_row(row) for row in reversed(rows)]

    def recall(
        self,
        user_id: str,
        query: str,
        embedding: Optional[Sequence[float]] = None,
        limit: int = 6,
    ) -> List[MemorySearchResult]:
        if self._collection is not None:
            chroma_results = self._recall_from_chroma(user_id, query, embedding, limit)
            if chroma_results:
                return chroma_results

        return self._recall_from_sqlite(user_id, query, limit)

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                created_at REAL NOT NULL,
                mood_label TEXT NOT NULL DEFAULT 'balanced',
                personality TEXT NOT NULL DEFAULT 'neuro'
            );

            CREATE INDEX IF NOT EXISTS idx_messages_scope_time
                ON conversation_messages (scope_type, scope_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_messages_user_time
                ON conversation_messages (user_id, created_at);

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                first_seen_at REAL NOT NULL,
                last_seen_at REAL NOT NULL,
                message_count INTEGER NOT NULL
            );
            """
        )
        self._conn.commit()

    def _upsert_profile(self, user_id: str, user_name: str, timestamp: float) -> None:
        self._conn.execute(
            """
            INSERT INTO user_profiles (
                user_id, display_name, first_seen_at, last_seen_at, message_count
            )
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = excluded.display_name,
                last_seen_at = excluded.last_seen_at,
                message_count = user_profiles.message_count + 1
            """,
            (user_id, user_name, timestamp, timestamp),
        )

    def _create_chroma_collection(self) -> Any:
        try:
            import chromadb
        except Exception as exc:
            logger.warning("ChromaDB is unavailable; semantic memory disabled: {}", exc)
            return None

        os.makedirs(self.chroma_path, exist_ok=True)
        client = chromadb.PersistentClient(path=self.chroma_path)
        return client.get_or_create_collection(name=self.collection_name)

    def _add_to_chroma(
        self,
        message_id: int,
        scope_type: str,
        scope_id: str,
        user_id: str,
        role: str,
        content: str,
        embedding: Optional[Sequence[float]],
        created_at: float,
    ) -> None:
        if self._collection is None or not content.strip():
            return

        vector = list(embedding) if embedding is not None else deterministic_embedding(
            content,
            self.embedding_dimension,
        )
        try:
            self._collection.add(
                ids=[f"message-{message_id}"],
                documents=[content],
                embeddings=[vector],
                metadatas=[
                    {
                        "message_id": message_id,
                        "scope_type": scope_type,
                        "scope_id": scope_id,
                        "user_id": user_id,
                        "role": role,
                        "created_at": created_at,
                    }
                ],
            )
        except Exception as exc:
            logger.warning("Failed to index memory in ChromaDB: {}", exc)

    def _recall_from_chroma(
        self,
        user_id: str,
        query: str,
        embedding: Optional[Sequence[float]],
        limit: int,
    ) -> List[MemorySearchResult]:
        if self._collection is None:
            return []

        vector = list(embedding) if embedding is not None else deterministic_embedding(
            query,
            self.embedding_dimension,
        )
        try:
            result = self._collection.query(
                query_embeddings=[vector],
                n_results=limit,
                where={"user_id": user_id},
            )
        except Exception as exc:
            logger.warning("Failed to recall memory from ChromaDB: {}", exc)
            return []

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        message_ids = [int(str(item).replace("message-", "")) for item in ids]
        records = self._records_by_ids(message_ids)
        by_id = {record.id: record for record in records}
        results: List[MemorySearchResult] = []
        for index, message_id in enumerate(message_ids):
            record = by_id.get(message_id)
            if record is None:
                continue
            distance = float(distances[index]) if index < len(distances) else 1.0
            results.append(MemorySearchResult(record=record, score=1.0 / (1.0 + distance)))
        return results

    def _recall_from_sqlite(
        self,
        user_id: str,
        query: str,
        limit: int,
    ) -> List[MemorySearchResult]:
        rows = self._conn.execute(
            """
            SELECT * FROM conversation_messages
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (user_id,),
        ).fetchall()
        query_terms = set(_tokens(query))
        scored: List[MemorySearchResult] = []
        for row in rows:
            record = _record_from_row(row)
            terms = set(_tokens(record.content))
            score = _overlap_score(query_terms, terms)
            if score > 0:
                scored.append(MemorySearchResult(record=record, score=score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def _records_by_ids(self, ids: Sequence[int]) -> List[MemoryRecord]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT * FROM conversation_messages WHERE id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
        return [_record_from_row(row) for row in rows]


def deterministic_embedding(text: str, dimensions: int = 384) -> List[float]:
    dimensions = max(8, dimensions)
    vector = [0.0 for _ in range(dimensions)]
    tokens = _tokens(text) or [text]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        offset = digest[0] % dimensions
        for index, byte in enumerate(digest):
            slot = (offset + index) % dimensions
            vector[slot] += (float(byte) - 127.5) / 127.5

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _record_from_row(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        id=int(row["id"]),
        scope_type=str(row["scope_type"]),
        scope_id=str(row["scope_id"]),
        user_id=str(row["user_id"]),
        user_name=str(row["user_name"]),
        role=str(row["role"]),
        content=str(row["content"]),
        content_type=str(row["content_type"]),
        created_at=float(row["created_at"]),
        mood_label=str(row["mood_label"]),
        personality=str(row["personality"]),
    )


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _overlap_score(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
