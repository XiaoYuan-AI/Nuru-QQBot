from src.plugins.nuru_chat.memory import MemoryStore


def test_memory_store_persists_recent_messages_and_recalls(tmp_path):
    sqlite_path = tmp_path / "memory.sqlite3"
    chroma_path = tmp_path / "chroma"

    store = MemoryStore(
        sqlite_path=str(sqlite_path),
        chroma_path=str(chroma_path),
        collection_name="test_memory",
        enable_chroma=False,
    )
    store.add_message(
        scope_type="private",
        scope_id="1001",
        user_id="1001",
        user_name="Alice",
        role="user",
        content="I like strawberry cake",
        created_at=1.0,
    )
    store.add_message(
        scope_type="private",
        scope_id="1001",
        user_id="1001",
        user_name="Nuru",
        role="assistant",
        content="Strawberry cake sounds cute.",
        created_at=2.0,
    )
    store.close()

    reopened = MemoryStore(
        sqlite_path=str(sqlite_path),
        chroma_path=str(chroma_path),
        collection_name="test_memory",
        enable_chroma=False,
    )
    recent = reopened.recent_messages("private", "1001")
    recalled = reopened.recall("1001", "strawberry dessert", limit=2)

    assert [item.role for item in recent] == ["user", "assistant"]
    assert recalled
    assert {item.record.content for item in recalled} >= {
        "I like strawberry cake",
        "Strawberry cake sounds cute.",
    }
    reopened.close()
