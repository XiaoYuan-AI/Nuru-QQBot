from src.plugins.nuru_chat.tools import ToolStore, calculate, handle_tool_text


def test_calculator_tool_evaluates_simple_expression():
    result = calculate("2 + 3 * 4")

    assert result.name == "calculator.calculate"
    assert result.output == "2 + 3 * 4 = 14"


def test_calendar_and_reminder_tools_persist_by_scope(tmp_path):
    store = ToolStore(str(tmp_path / "state.sqlite3"))

    calendar = handle_tool_text(
        store,
        "group",
        "42",
        "calendar add stream planning at tomorrow 20:00",
    )
    reminder = handle_tool_text(
        store,
        "group",
        "42",
        "remind me hydrate at 21:00",
    )
    calendar_list = handle_tool_text(store, "group", "42", "calendar list")
    reminder_list = handle_tool_text(store, "group", "42", "reminders list")

    assert calendar is not None and calendar.name == "calendar.add"
    assert reminder is not None and reminder.name == "reminder.add"
    assert calendar_list is not None and "stream planning" in calendar_list.output
    assert reminder_list is not None and "hydrate" in reminder_list.output
    store.close()
