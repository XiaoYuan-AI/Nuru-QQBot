import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List


TOPIC_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,}")


@dataclass
class WorkingExchange:
    user: str
    assistant: str
    topic_terms: List[str]


class WorkingMemoryStore:
    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max(1, max_items)
        self._items: Dict[str, Deque[WorkingExchange]] = defaultdict(deque)

    def add_exchange(self, scope_key: str, user: str, assistant: str) -> None:
        terms = TOPIC_PATTERN.findall(f"{user} {assistant}".lower())
        items = self._items[scope_key]
        items.append(WorkingExchange(user=user, assistant=assistant, topic_terms=terms))
        while len(items) > self.max_items:
            items.popleft()

    def recent_topics(self, scope_key: str, limit: int = 8) -> List[str]:
        counter: Counter = Counter()
        for exchange in self._items.get(scope_key, []):
            counter.update(exchange.topic_terms)
        return [topic for topic, _count in counter.most_common(limit)]

    def format_context(self, scope_key: str, limit: int = 6) -> str:
        items = list(self._items.get(scope_key, []))[-limit:]
        if not items:
            return ""
        topics = ", ".join(self.recent_topics(scope_key))
        lines = [f"- User: {item.user} | Nuru: {item.assistant}" for item in items]
        header = f"Recent topics: {topics}" if topics else "Recent exchanges:"
        return header + "\n" + "\n".join(lines)
