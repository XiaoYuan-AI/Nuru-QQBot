from typing import Any, Dict, Iterable, List, Optional


async def is_addressed_group_message(event: Any) -> bool:
    return is_group_message_event(event) and event_is_tome(event)


async def is_private_message(event: Any) -> bool:
    return is_private_message_event(event)


async def is_group_message(event: Any) -> bool:
    return is_group_message_event(event)


def is_group_message_event(event: Any) -> bool:
    if getattr(event, "message_type", None) == "group":
        return True
    return hasattr(event, "group_id") and not is_private_message_event(event)


def is_private_message_event(event: Any) -> bool:
    if getattr(event, "message_type", None) == "private":
        return True
    return hasattr(event, "user_id") and not hasattr(event, "group_id")


def event_is_tome(event: Any) -> bool:
    is_tome = getattr(event, "is_tome", None)
    if callable(is_tome):
        return bool(is_tome())
    return False


def is_group_admin(event: Any) -> bool:
    sender = getattr(event, "sender", None)
    role = getattr(sender, "role", "")
    return role in {"admin", "owner"}


def parse_personality_command(text: str, prefix: str) -> Optional[str]:
    normalized = " ".join(text.strip().split())
    command = " ".join(prefix.strip().split())
    if not normalized.lower().startswith(command.lower()):
        return None

    remainder = normalized[len(command) :].strip()
    return remainder or "list"


def is_personality_command(event: Any, prefix: str) -> bool:
    text = event_plain_text(event)
    return parse_personality_command(text, prefix) is not None


def is_image_generation_request(text: str, commands: Iterable[str]) -> bool:
    return parse_image_generation_prompt(text, commands) is not None


def parse_image_generation_prompt(
    text: str,
    commands: Iterable[str],
) -> Optional[str]:
    normalized = text.strip()
    for command in commands:
        command = command.strip()
        if not command:
            continue
        if normalized.lower().startswith(command.lower()):
            prompt = normalized[len(command) :].strip()
            return prompt or None
    return None


def event_plain_text(event: Any) -> str:
    get_plaintext = getattr(event, "get_plaintext", None)
    if callable(get_plaintext):
        return str(get_plaintext())
    return str(getattr(event, "message", ""))


def message_has_image(event: Any) -> bool:
    return bool(extract_image_sources(event))


def extract_image_sources(event: Any) -> List[str]:
    sources: List[str] = []
    for segment in _iter_message_segments(event):
        segment_type = _segment_type(segment)
        if segment_type != "image":
            continue
        data = _segment_data(segment)
        source = data.get("url") or data.get("file") or data.get("base64")
        if source:
            sources.append(str(source))
    return sources


def _iter_message_segments(event: Any) -> Iterable[Any]:
    message = getattr(event, "message", [])
    if isinstance(message, str):
        return []
    try:
        return list(message)
    except TypeError:
        return []


def _segment_type(segment: Any) -> str:
    if isinstance(segment, dict):
        return str(segment.get("type", ""))
    return str(getattr(segment, "type", ""))


def _segment_data(segment: Any) -> Dict[str, Any]:
    if isinstance(segment, dict):
        data = segment.get("data", {})
    else:
        data = getattr(segment, "data", {})

    if isinstance(data, dict):
        return data
    return {}
