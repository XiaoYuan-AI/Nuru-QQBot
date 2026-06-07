import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class Participant:
    group_id: str
    user_id: str
    display_name: str
    last_seen_at: float
    message_count: int


class GroupAwarenessStore:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        self._conn = _connect(sqlite_path)
        self._create_tables()

    def close(self) -> None:
        self._conn.close()

    def record_group_message(
        self,
        group_id: str,
        user_id: str,
        display_name: str,
        timestamp: Optional[float] = None,
    ) -> None:
        now = timestamp if timestamp is not None else time.time()
        self._conn.execute(
            """
            INSERT INTO group_activity (group_id, last_activity_at, last_bot_message_at)
            VALUES (?, ?, 0)
            ON CONFLICT(group_id) DO UPDATE SET
                last_activity_at = excluded.last_activity_at
            """,
            (group_id, now),
        )
        self._conn.execute(
            """
            INSERT INTO group_participants (
                group_id, user_id, display_name, last_seen_at, message_count
            )
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                display_name = excluded.display_name,
                last_seen_at = excluded.last_seen_at,
                message_count = group_participants.message_count + 1
            """,
            (group_id, user_id, display_name, now),
        )
        self._conn.commit()

    def mark_bot_activity(self, group_id: str, timestamp: Optional[float] = None) -> None:
        now = timestamp if timestamp is not None else time.time()
        self._conn.execute(
            """
            INSERT INTO group_activity (group_id, last_activity_at, last_bot_message_at)
            VALUES (?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                last_bot_message_at = excluded.last_bot_message_at
            """,
            (group_id, now, now),
        )
        self._conn.commit()

    def recent_participants(self, group_id: str, limit: int = 8) -> List[Participant]:
        rows = self._conn.execute(
            """
            SELECT * FROM group_participants
            WHERE group_id = ?
            ORDER BY last_seen_at DESC
            LIMIT ?
            """,
            (group_id, limit),
        ).fetchall()
        return [
            Participant(
                group_id=str(row["group_id"]),
                user_id=str(row["user_id"]),
                display_name=str(row["display_name"]),
                last_seen_at=float(row["last_seen_at"]),
                message_count=int(row["message_count"]),
            )
            for row in rows
        ]

    def idle_group_ids(
        self,
        min_idle_seconds: int,
        configured_group_ids: Iterable[str],
        now: Optional[float] = None,
    ) -> List[str]:
        timestamp = now if now is not None else time.time()
        configured = {str(group_id) for group_id in configured_group_ids if str(group_id)}
        rows = self._conn.execute("SELECT * FROM group_activity").fetchall()
        idle: List[str] = []
        for row in rows:
            group_id = str(row["group_id"])
            if configured and group_id not in configured:
                continue
            last_activity = float(row["last_activity_at"])
            last_bot = float(row["last_bot_message_at"])
            if timestamp - max(last_activity, last_bot) >= min_idle_seconds:
                idle.append(group_id)
        return idle

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS group_activity (
                group_id TEXT PRIMARY KEY,
                last_activity_at REAL NOT NULL,
                last_bot_message_at REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS group_participants (
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                last_seen_at REAL NOT NULL,
                message_count INTEGER NOT NULL,
                PRIMARY KEY(group_id, user_id)
            );
            """
        )
        self._conn.commit()


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
