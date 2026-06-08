import asyncio

from src.plugins.nuru_chat.queue import ScopeMessageQueue


def test_scope_message_queue_returns_busy_when_queue_is_full():
    queue = ScopeMessageQueue(max_queue_depth=1, busy_message="busy")

    async def slow_value():
        await asyncio.sleep(0.02)
        return "done"

    async def run_queue():
        first = asyncio.create_task(
            queue.run("group:1", 0.0, slow_value, lambda message: message)
        )
        await asyncio.sleep(0)
        second = await queue.run("group:1", 0.0, slow_value, lambda message: message)
        return await first, second

    assert asyncio.run(run_queue()) == ("done", "busy")
