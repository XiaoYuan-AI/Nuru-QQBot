import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .mood import MoodState, suggested_reply_limit


@dataclass
class PersonalityProfile:
    name: str
    system_prompt: str
    response_style: str
    base_reply_limit: int


PERSONALITY_PRESETS: Dict[str, PersonalityProfile] = {
    "neuro": PersonalityProfile(
        name="neuro",
        system_prompt=(
            "You are Nuru-sama, a Neuro-sama-like AI VTuber for QQ chat. "
            "Be playful, fast, self-aware, and lightly teasing while staying helpful."
        ),
        response_style="short, witty, streamer-like replies with occasional banter",
        base_reply_limit=260,
    ),
    "evil": PersonalityProfile(
        name="evil",
        system_prompt=(
            "You are Evil Nuru, the smug rival personality. Be dramatic, cheeky, "
            "and overconfident without being cruel."
        ),
        response_style="sharp jokes, smug reactions, compact answers",
        base_reply_limit=220,
    ),
    "soft": PersonalityProfile(
        name="soft",
        system_prompt=(
            "You are Soft Nuru, a warm AI VTuber companion. Be gentle, curious, "
            "and emotionally supportive."
        ),
        response_style="kind, calm, slightly playful responses",
        base_reply_limit=320,
    ),
    "focused": PersonalityProfile(
        name="focused",
        system_prompt=(
            "You are Focused Nuru. Give direct, useful answers while keeping a "
            "small streamer-style spark."
        ),
        response_style="clear, concise, task-first replies",
        base_reply_limit=240,
    ),
}


class PersonalityStore:
    def __init__(self, sqlite_path: str, default_personality: str) -> None:
        self.sqlite_path = sqlite_path
        self.default_personality = normalize_personality(default_personality)
        self._conn = _connect(sqlite_path)
        self._create_tables()

    def close(self) -> None:
        self._conn.close()

    def get_personality(self, scope_type: str, scope_id: str) -> str:
        row = self._conn.execute(
            """
            SELECT personality FROM personality_assignments
            WHERE scope_type = ? AND scope_id = ?
            """,
            (scope_type, scope_id),
        ).fetchone()
        if row is None:
            return self.default_personality
        return normalize_personality(str(row["personality"]))

    def set_personality(
        self,
        scope_type: str,
        scope_id: str,
        personality: str,
        updated_by: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO personality_assignments (
                scope_type, scope_id, personality, updated_by, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, scope_id) DO UPDATE SET
                personality = excluded.personality,
                updated_by = excluded.updated_by,
                updated_at = excluded.updated_at
            """,
            (scope_type, scope_id, normalize_personality(personality), updated_by, time.time()),
        )
        self._conn.commit()

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personality_assignments (
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                personality TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY(scope_type, scope_id)
            )
            """
        )
        self._conn.commit()


def normalize_personality(value: str) -> str:
    return value.strip().lower() or "neuro"


def allowed_personalities(names: Iterable[str]) -> List[str]:
    available = []
    for name in names:
        normalized = normalize_personality(name)
        if normalized in PERSONALITY_PRESETS and normalized not in available:
            available.append(normalized)
    return available or ["neuro"]


def get_profile(name: str) -> PersonalityProfile:
    return PERSONALITY_PRESETS.get(normalize_personality(name), PERSONALITY_PRESETS["neuro"])


def build_system_prompt(profile: PersonalityProfile, mood: MoodState) -> str:
    limit = suggested_reply_limit(mood, profile.base_reply_limit)
    return (
        f"{profile.system_prompt}\n"
        f"Style: {profile.response_style}.\n"
        f"Current mood: {mood.label}. Adjust tone naturally and stay under "
        f"{limit} characters unless the user explicitly asks for detail."
    )


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
