import ast
import operator
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ToolResult:
    name: str
    output: str
    metadata: Dict[str, Any]


class ToolStore:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        self._conn = _connect(sqlite_path)
        self._create_tables()

    def close(self) -> None:
        self._conn.close()

    def add_calendar_event(
        self,
        scope_type: str,
        scope_id: str,
        title: str,
        starts_at: str,
    ) -> ToolResult:
        self._conn.execute(
            """
            INSERT INTO calendar_events (scope_type, scope_id, title, starts_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scope_type, scope_id, title, starts_at, time.time()),
        )
        self._conn.commit()
        return ToolResult(
            name="calendar.add",
            output=f"Calendar event saved: {title} at {starts_at}.",
            metadata={"title": title, "starts_at": starts_at},
        )

    def list_calendar_events(self, scope_type: str, scope_id: str, limit: int = 5) -> ToolResult:
        rows = self._conn.execute(
            """
            SELECT title, starts_at FROM calendar_events
            WHERE scope_type = ? AND scope_id = ?
            ORDER BY starts_at ASC, id ASC
            LIMIT ?
            """,
            (scope_type, scope_id, limit),
        ).fetchall()
        if not rows:
            output = "No calendar events saved."
        else:
            output = "Upcoming events: " + "; ".join(
                f"{row['title']} at {row['starts_at']}" for row in rows
            )
        return ToolResult(name="calendar.list", output=output, metadata={"count": len(rows)})

    def add_reminder(
        self,
        scope_type: str,
        scope_id: str,
        text: str,
        remind_at: str,
    ) -> ToolResult:
        self._conn.execute(
            """
            INSERT INTO reminders (scope_type, scope_id, text, remind_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scope_type, scope_id, text, remind_at, time.time()),
        )
        self._conn.commit()
        return ToolResult(
            name="reminder.add",
            output=f"Reminder saved: {text} at {remind_at}.",
            metadata={"text": text, "remind_at": remind_at},
        )

    def list_reminders(self, scope_type: str, scope_id: str, limit: int = 5) -> ToolResult:
        rows = self._conn.execute(
            """
            SELECT text, remind_at FROM reminders
            WHERE scope_type = ? AND scope_id = ?
            ORDER BY remind_at ASC, id ASC
            LIMIT ?
            """,
            (scope_type, scope_id, limit),
        ).fetchall()
        if not rows:
            output = "No reminders saved."
        else:
            output = "Reminders: " + "; ".join(
                f"{row['text']} at {row['remind_at']}" for row in rows
            )
        return ToolResult(name="reminder.list", output=output, metadata={"count": len(rows)})

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                title TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        self._conn.commit()


def handle_tool_text(
    store: ToolStore,
    scope_type: str,
    scope_id: str,
    text: str,
) -> Optional[ToolResult]:
    normalized = " ".join(text.strip().split())
    lowered = normalized.lower()

    if lowered.startswith("calculate "):
        expression = normalized[len("calculate ") :].strip()
        return calculate(expression)
    if lowered.startswith("calc "):
        expression = normalized[len("calc ") :].strip()
        return calculate(expression)
    if lowered == "calendar list":
        return store.list_calendar_events(scope_type, scope_id)
    if lowered.startswith("calendar add "):
        return _calendar_add(store, scope_type, scope_id, normalized[len("calendar add ") :])
    if lowered == "reminders list":
        return store.list_reminders(scope_type, scope_id)
    if lowered.startswith("remind me "):
        return _reminder_add(store, scope_type, scope_id, normalized[len("remind me ") :])

    return None


def calculate(expression: str) -> ToolResult:
    try:
        value = _safe_eval(expression)
    except (SyntaxError, ZeroDivisionError) as exc:
        raise ValueError("Calculator expression is invalid.") from exc
    return ToolResult(
        name="calculator.calculate",
        output=f"{expression} = {value:g}",
        metadata={"expression": expression, "value": value},
    )


def _calendar_add(
    store: ToolStore,
    scope_type: str,
    scope_id: str,
    payload: str,
) -> ToolResult:
    title, starts_at = _split_on_at(payload)
    return store.add_calendar_event(scope_type, scope_id, title, starts_at)


def _reminder_add(
    store: ToolStore,
    scope_type: str,
    scope_id: str,
    payload: str,
) -> ToolResult:
    text, remind_at = _split_on_at(payload)
    return store.add_reminder(scope_type, scope_id, text, remind_at)


def _split_on_at(payload: str) -> Tuple[str, str]:
    if " at " not in payload:
        raise ValueError("Use '<text> at <time>'.")
    left, right = payload.rsplit(" at ", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        raise ValueError("Both text and time are required.")
    return left, right


def _safe_eval(expression: str) -> float:
    operators: Dict[type, Callable[[float, float], float]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
    }

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            left = evaluate(node.left)
            right = evaluate(node.right)
            return operators[type(node.op)](left, right)
        raise ValueError("Only simple arithmetic is supported.")

    parsed = ast.parse(expression, mode="eval")
    return evaluate(parsed)


def _connect(path: str) -> sqlite3.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
