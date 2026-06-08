from src.plugins.nuru_chat.awareness import GroupAwarenessStore


def test_group_idle_settings_override_global_interval_and_quiet_mode(tmp_path):
    store = GroupAwarenessStore(str(tmp_path / "state.sqlite3"))
    store.record_group_message("42", "1001", "Alice", timestamp=10.0)

    assert store.idle_group_ids(100, [], now=50.0) == []

    store.set_idle_interval("42", 30, "1001")
    assert store.idle_group_ids(100, [], now=50.0) == ["42"]

    store.set_quiet_mode("42", True, "1001")
    assert store.idle_group_ids(100, [], now=200.0) == []
    store.close()
