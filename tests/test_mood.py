from src.plugins.nuru_chat.mood import MoodStore, format_mood_reply, suggested_reply_limit
from src.plugins.nuru_chat.personality import build_system_prompt, get_profile
from src.plugins.nuru_chat.refusal import RefusalLogStore, decide_refusal


def test_mood_updates_from_message_and_influences_prompt(tmp_path):
    store = MoodStore(str(tmp_path / "state.sqlite3"))

    mood = store.update_from_message(
        scope_type="group",
        scope_id="42",
        text="thanks this is cute good?",
        addressed=True,
        has_image=True,
        now=10.0,
    )
    prompt = build_system_prompt(get_profile("neuro"), mood)

    assert mood.affection > 0.55
    assert mood.curiosity > 0.50
    assert "Current mood:" in prompt
    assert "characters" in prompt
    store.close()


def test_sleepy_mood_shortens_reply_limit():
    store = MoodStore(":memory:")
    mood = store.update_from_message(
        scope_type="private",
        scope_id="7",
        text="hello",
        addressed=False,
        now=1.0,
    )
    mood.energy = 0.20

    assert suggested_reply_limit(mood, 260) < 260
    store.close()


def test_mood_formatter_appends_emoticon_and_trims():
    store = MoodStore(":memory:")
    mood = store.update_from_message(
        scope_type="group",
        scope_id="7",
        text="thanks good cute",
        addressed=True,
        now=1.0,
    )
    mood.affection = 0.90

    reply = format_mood_reply("hello " * 50, mood, 90, {"warm": "<3"})

    assert len(reply) <= 90
    assert reply.endswith("<3") or reply.endswith("...")
    store.close()


def test_refusal_logs_low_energy_reason(tmp_path):
    store = MoodStore(str(tmp_path / "state.sqlite3"))
    refusal_log = RefusalLogStore(str(tmp_path / "state.sqlite3"))
    mood = store.update_from_message("private", "1", "hello", now=1.0)
    mood.energy = 0.10

    decision = decide_refusal(
        text="hello",
        mood=mood,
        blocked_terms=[],
        energy_threshold=0.20,
        low_energy_message="too tired",
        safety_message="no",
    )
    refusal_log.add("private", "1", "1", decision.reason, "hello")

    assert decision.refused is True
    assert refusal_log.latest_reason() == "low_energy:0.10"
    store.close()
    refusal_log.close()
