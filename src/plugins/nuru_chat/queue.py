import asyncio
import time
from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, Dict, TypeVar


T = TypeVar("T")


class ScopeMessageQueue:
    def __init__(self, max_queue_depth: int, busy_message: str) -> None:
        self.max_queue_depth = max(1, max_queue_depth)
        self.busy_message = busy_message
        self._locks: DefaultDict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._pending: DefaultDict[str, int] = defaultdict(int)
        self._last_completed_at: Dict[str, float] = {}

    async def run(
        self,
        scope_key: str,
        min_gap_seconds: float,
        factory: Callable[[], Awaitable[T]],
        busy_factory: Callable[[str], T],
    ) -> T:
        if self._pending[scope_key] >= self.max_queue_depth:
            return busy_factory(self.busy_message)

        self._pending[scope_key] += 1
        try:
            async with self._locks[scope_key]:
                delay = self._delay_for(scope_key, min_gap_seconds)
                if delay > 0:
                    await asyncio.sleep(delay)
                result = await factory()
                self._last_completed_at[scope_key] = time.monotonic()
                return result
        finally:
            self._pending[scope_key] = max(0, self._pending[scope_key] - 1)

    def _delay_for(self, scope_key: str, min_gap_seconds: float) -> float:
        if min_gap_seconds <= 0:
            return 0.0
        last_completed = self._last_completed_at.get(scope_key)
        if last_completed is None:
            return 0.0
        return max(0.0, min_gap_seconds - (time.monotonic() - last_completed))
