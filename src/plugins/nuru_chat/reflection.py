import os
import sqlite3
import time
from dataclasses import dataclass
from typing import List

from .memory import MemoryStore
from .mood import MoodState


@dataclass
class ReflectionResult:
    monologue: str
    summary: str


class ReflectionStore:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        self._conn = _connect(sqlite_path)
        self._create_tables()

    def close(self) -> None:
        self._conn.close()

    def add(self, scope_type: str, scope_id: str, result: ReflectionResult) -> None:
        self._conn.execute(
            """
            INSERT INTO reflections (scope_type, scope_id, monologue, summary, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scope_type, scope_id, result.monologue, result.summary, time.time()),
        )
        self._conn.commit()

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                monologue TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()


def reflect_exchange(
    memory_store: MemoryStore,
    reflection_store: ReflectionStore,
    scope_type: str,
    scope_id: str,
    user_id: str,
    user_name: str,
    user_text: str,
    assistant_text: str,
    mood: MoodState,
    topics: List[str],
) -> ReflectionResult:
    topic_text = ", ".join(topics[:4]) or "no stable topic yet"
    monologue = (
        f"I felt {mood.label} after {user_name}'s message and should remember "
        f"{topic_text} for this {scope_type}."
    )
    summary = f"{user_name} discussed {topic_text}. Nuru replied: {assistant_text[:160]}"
    result = ReflectionResult(monologue=monologue, summary=summary)
    reflection_store.add(scope_type, scope_id, result)
    memory_store.add_message(
        scope_type=scope_type,
        scope_id=scope_id,
        user_id=user_id,
        user_name="Nuru internal reflection",
        role="reflection",
        content=summary,
        content_type="reflection",
        mood_label=mood.label,
        personality="internal",
    )
    return result


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
