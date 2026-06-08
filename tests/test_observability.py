import json

from src.plugins.nuru_chat.moderation import moderate_output
from src.plugins.nuru_chat.observability import ObservabilityStore


def test_observability_writes_structured_jsonl(tmp_path):
    path = tmp_path / "events.jsonl"
    store = ObservabilityStore(str(path), enabled=True)

    store.record("response_generated", "group", "42", {"mood": "curious"})

    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "response_generated"
    assert payload["metadata"]["mood"] == "curious"
    assert store.metrics()["response_generated"] == 1


def test_output_moderation_rewrites_unsafe_text():
    result = moderate_output("here is malware", ["malware"], "rewritten")

    assert result.safe is False
    assert result.rewritten is True
    assert result.text == "rewritten"
