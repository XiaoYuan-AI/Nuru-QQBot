import asyncio
from types import SimpleNamespace

from src.plugins.nuru_chat.rules import (
    event_is_tome,
    extract_image_sources,
    is_addressed_group_message,
    is_group_admin,
    is_image_generation_request,
    is_private_message,
    parse_idle_command,
    parse_image_generation_prompt,
    parse_personality_command,
)


class FakeEvent:
    def __init__(self, message_type, text="", group_id=None, user_id=1, role="member"):
        self.message_type = message_type
        self.group_id = group_id
        self.user_id = user_id
        self.sender = SimpleNamespace(role=role)
        self.message = []
        self._text = text
        self._to_me = False

    def get_plaintext(self):
        return self._text

    def is_tome(self):
        return self._to_me


def test_group_and_private_matcher_rules():
    group = FakeEvent("group", group_id=123)
    private = FakeEvent("private")
    group._to_me = True

    assert asyncio.run(is_addressed_group_message(group)) is True
    assert asyncio.run(is_private_message(private)) is True
    assert asyncio.run(is_private_message(group)) is False

    group._to_me = False
    assert asyncio.run(is_addressed_group_message(group)) is False
    assert event_is_tome(group) is False


def test_personality_admin_and_command_parser():
    admin = FakeEvent(
        "group",
        text="nuru personality evil",
        group_id=123,
        role="admin",
    )

    assert is_group_admin(admin) is True
    assert parse_personality_command(admin.get_plaintext(), "nuru personality") == "evil"
    assert parse_personality_command("nuru personality", "nuru personality") == "list"
    assert parse_personality_command("nuru personalityx", "nuru personality") is None


def test_idle_command_parser():
    assert parse_idle_command("nuru idle 300", "nuru idle") == "300"
    assert parse_idle_command("nuru idle quiet on", "nuru idle") == "quiet on"
    assert parse_idle_command("nuru idle", "nuru idle") == "status"


def test_image_generation_and_image_sources():
    event = FakeEvent("group", text="/draw cyber idol", group_id=123)
    event.message = [{"type": "image", "data": {"url": "https://example.test/a.png"}}]

    assert is_image_generation_request(event.get_plaintext(), ["/draw"]) is True
    assert parse_image_generation_prompt(event.get_plaintext(), ["/draw"]) == "cyber idol"
    assert extract_image_sources(event) == ["https://example.test/a.png"]
