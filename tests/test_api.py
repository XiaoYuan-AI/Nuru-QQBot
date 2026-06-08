import asyncio

from src.plugins.nuru_chat import api
from src.plugins.nuru_chat.api import NuruModelClient
from src.plugins.nuru_chat.config import Config


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class RetryThenSuccessClient:
    attempts = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json, headers):
        self.__class__.attempts.append({"url": url, "json": json, "headers": headers})
        if len(self.__class__.attempts) == 1:
            raise RuntimeError("temporary outage")
        return FakeResponse({"text": "retry worked"})


class AlwaysFailClient:
    attempts = 0

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json, headers):
        self.__class__.attempts += 1
        raise RuntimeError("backend unavailable")


def test_nuru_api_retries_failed_requests(monkeypatch):
    RetryThenSuccessClient.attempts = []
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(api.httpx, "AsyncClient", RetryThenSuccessClient)
    monkeypatch.setattr(api.asyncio, "sleep", fake_sleep)

    client = NuruModelClient(
        Config(
            nuru_api_base_url="https://api.example.test",
            nuru_api_key="token",
            nuru_api_retries=1,
            nuru_api_backoff_seconds=0.25,
        )
    )
    reply = asyncio.run(client.create_chat_reply({"text": "hello"}))

    assert reply.text == "retry worked"
    assert len(RetryThenSuccessClient.attempts) == 2
    assert RetryThenSuccessClient.attempts[0]["headers"] == {
        "Authorization": "Bearer token"
    }
    assert sleeps == [0.25]


def test_nuru_api_falls_back_to_busy_message(monkeypatch):
    AlwaysFailClient.attempts = 0

    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(api.httpx, "AsyncClient", AlwaysFailClient)
    monkeypatch.setattr(api.asyncio, "sleep", fake_sleep)

    client = NuruModelClient(
        Config(
            nuru_api_base_url="https://api.example.test",
            nuru_api_retries=1,
            nuru_busy_message="busy, try again",
        )
    )
    reply = asyncio.run(client.create_chat_reply({"text": "hello"}))

    assert reply.text == "busy, try again"
    assert AlwaysFailClient.attempts == 2
