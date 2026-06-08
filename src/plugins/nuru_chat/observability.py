import json
import os
import time
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class ObservabilityEvent:
    event: str
    scope_type: str
    scope_id: str
    metadata: Dict[str, Any]
    created_at: float


class ObservabilityStore:
    def __init__(self, log_path: str, enabled: bool = True) -> None:
        self.log_path = log_path
        self.enabled = enabled
        self._metrics: Counter = Counter()

    def record(
        self,
        event: str,
        scope_type: str,
        scope_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        self._metrics[event] += 1
        if not self.enabled:
            return
        directory = os.path.dirname(self.log_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = ObservabilityEvent(event, scope_type, scope_id, metadata, time.time())
        with open(self.log_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(payload), ensure_ascii=False) + "\n")

    def metrics(self) -> Dict[str, int]:
        return dict(self._metrics)
