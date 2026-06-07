import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional


POSITIVE_WORDS = {"love", "great", "nice", "good", "thanks", "cute", "happy"}
NEGATIVE_WORDS = {"bad", "hate", "angry", "sad", "wrong", "stupid", "annoying"}


@dataclass
class MoodState:
    scope_type: str
    scope_id: str
    energy: float
    affection: float
    sass: float
    curiosity: float
    updated_at: float

    @property
    def label(self) -> str:
        if self.affection < 0.35:
            return "irritated"
        if self.energy < 0.35:
            return "sleepy"
        if self.sass > 0.7:
            return "mischievous"
        if self.curiosity > 0.7:
            return "curious"
        if self.affection > 0.7:
            return "warm"
        return "balanced"


class MoodStore:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        self._conn = _connect(sqlite_path)
        self._create_tables()

    def close(self) -> None:
        self._conn.close()

    def get_state(self, scope_type: str, scope_id: str) -> MoodState:
        row = self._conn.execute(
            "SELECT * FROM mood_states WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
        if row is None:
            return MoodState(scope_type, scope_id, 0.55, 0.55, 0.45, 0.50, time.time())
        return MoodState(
            scope_type=str(row["scope_type"]),
            scope_id=str(row["scope_id"]),
            energy=float(row["energy"]),
            affection=float(row["affection"]),
            sass=float(row["sass"]),
            curiosity=float(row["curiosity"]),
            updated_at=float(row["updated_at"]),
        )

    def update_from_message(
        self,
        scope_type: str,
        scope_id: str,
        text: str,
        addressed: bool = False,
        has_image: bool = False,
        now: Optional[float] = None,
    ) -> MoodState:
        timestamp = now if now is not None else time.time()
        state = self.get_state(scope_type, scope_id)
        elapsed_minutes = max(0.0, (timestamp - state.updated_at) / 60.0)
        energy = _decay(state.energy, 0.55, elapsed_minutes, 0.015)
        affection = _decay(state.affection, 0.55, elapsed_minutes, 0.01)
        sass = _decay(state.sass, 0.45, elapsed_minutes, 0.012)
        curiosity = _decay(state.curiosity, 0.50, elapsed_minutes, 0.012)

        tokens = set(text.lower().split())
        positive = len(tokens & POSITIVE_WORDS)
        negative = len(tokens & NEGATIVE_WORDS)
        questions = text.count("?")

        energy += 0.04 if addressed else -0.01
        affection += 0.06 * positive - 0.08 * negative
        sass += 0.03 * negative + (0.02 if addressed else 0.0)
        curiosity += 0.04 * questions + (0.06 if has_image else 0.0)

        if len(text) > 240:
            energy -= 0.04
            curiosity += 0.03

        updated = MoodState(
            scope_type=scope_type,
            scope_id=scope_id,
            energy=_clamp(energy),
            affection=_clamp(affection),
            sass=_clamp(sass),
            curiosity=_clamp(curiosity),
            updated_at=timestamp,
        )
        self._save(updated)
        return updated

    def response_guidance(self, state: MoodState, base_limit: int) -> str:
        limit = suggested_reply_limit(state, base_limit)
        return (
            f"Mood is {state.label}. Energy={state.energy:.2f}, "
            f"affection={state.affection:.2f}, sass={state.sass:.2f}, "
            f"curiosity={state.curiosity:.2f}. Keep the reply under {limit} characters."
        )

    def _save(self, state: MoodState) -> None:
        self._conn.execute(
            """
            INSERT INTO mood_states (
                scope_type, scope_id, energy, affection, sass, curiosity, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, scope_id) DO UPDATE SET
                energy = excluded.energy,
                affection = excluded.affection,
                sass = excluded.sass,
                curiosity = excluded.curiosity,
                updated_at = excluded.updated_at
            """,
            (
                state.scope_type,
                state.scope_id,
                state.energy,
                state.affection,
                state.sass,
                state.curiosity,
                state.updated_at,
            ),
        )
        self._conn.commit()

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mood_states (
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                energy REAL NOT NULL,
                affection REAL NOT NULL,
                sass REAL NOT NULL,
                curiosity REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY(scope_type, scope_id)
            )
            """
        )
        self._conn.commit()


def suggested_reply_limit(state: MoodState, base_limit: int) -> int:
    limit = base_limit
    if state.energy < 0.35:
        limit -= 80
    if state.curiosity > 0.7:
        limit += 80
    if state.sass > 0.7:
        limit -= 40
    return max(80, min(600, limit))


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _decay(value: float, target: float, elapsed_minutes: float, rate: float) -> float:
    if elapsed_minutes <= 0:
        return value
    strength = min(1.0, elapsed_minutes * rate)
    return value + (target - value) * strength


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
