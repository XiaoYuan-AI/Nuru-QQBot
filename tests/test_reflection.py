from src.plugins.nuru_chat.memory import MemoryStore
from src.plugins.nuru_chat.mood import MoodStore
from src.plugins.nuru_chat.reflection import ReflectionStore, reflect_exchange
from src.plugins.nuru_chat.working_memory import WorkingMemoryStore


def test_reflection_adds_internal_memory(tmp_path):
    sqlite_path = tmp_path / "state.sqlite3"
    memory = MemoryStore(
        sqlite_path=str(sqlite_path),
        chroma_path=str(tmp_path / "chroma"),
        collection_name="test",
        enable_chroma=False,
    )
    mood_store = MoodStore(str(sqlite_path))
    reflection = ReflectionStore(str(sqlite_path))
    working = WorkingMemoryStore(max_items=3)
    mood = mood_store.update_from_message("group", "42", "waffle lore", now=1.0)
    working.add_exchange("group:42", "waffle lore", "waffle lore is canon")

    result = reflect_exchange(
        memory,
        reflection,
        "group",
        "42",
        "1001",
        "Alice",
        "waffle lore",
        "waffle lore is canon",
        mood,
        working.recent_topics("group:42"),
    )
    recent = memory.recent_messages("group", "42", limit=3)

    assert "waffle" in result.summary
    assert any(item.role == "reflection" for item in recent)
    memory.close()
    mood_store.close()
    reflection.close()
