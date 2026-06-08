import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Iterable, Optional

from .mood import MoodState


@dataclass
class RefusalDecision:
    refused: bool
    reason: str = ""
    message: str = ""


class RefusalLogStore:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        self._conn = _connect(sqlite_path)
        self._create_tables()

    def close(self) -> None:
        self._conn.close()

    def add(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
        reason: str,
        text: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO refusal_logs (
                scope_type, scope_id, user_id, reason, text, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (scope_type, scope_id, user_id, reason, text, time.time()),
        )
        self._conn.commit()

    def latest_reason(self) -> Optional[str]:
        row = self._conn.execute(
            "SELECT reason FROM refusal_logs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return str(row["reason"])

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refusal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()


def decide_refusal(
    text: str,
    mood: MoodState,
    blocked_terms: Iterable[str],
    energy_threshold: float,
    low_energy_message: str,
    safety_message: str,
) -> RefusalDecision:
    lowered = text.lower()
    for term in blocked_terms:
        normalized = term.strip().lower()
        if normalized and normalized in lowered:
            return RefusalDecision(
                refused=True,
                reason=f"blocked_term:{normalized}",
                message=safety_message,
            )

    if mood.energy <= energy_threshold:
        return RefusalDecision(
            refused=True,
            reason=f"low_energy:{mood.energy:.2f}",
            message=low_energy_message,
        )

    return RefusalDecision(refused=False)


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
