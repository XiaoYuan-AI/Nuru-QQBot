import asyncio
from types import SimpleNamespace

from src.plugins.nuru_chat.media import send_private_voice


class FakeBot:
    def __init__(self):
        self.calls = []

    async def send_private_msg(self, user_id, message):
        self.calls.append({"user_id": user_id, "message": message})


def test_send_private_voice_uses_mocked_onebot_call():
    bot = FakeBot()

    asyncio.run(
        send_private_voice(
            bot,
            1001,
            SimpleNamespace(file=None, base64_data="abc"),
            record_factory=lambda file_value: {"record": file_value},
        )
    )

    assert bot.calls == [
        {"user_id": 1001, "message": {"record": "base64://abc"}},
    ]
