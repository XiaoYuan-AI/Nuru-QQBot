from src.plugins.nuru_chat.mood import MoodStore, suggested_reply_limit
from src.plugins.nuru_chat.personality import build_system_prompt, get_profile


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
