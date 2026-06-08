import asyncio
from typing import Any, Dict, List, Optional

from nonebot import get_bots, get_driver, get_plugin_config, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .api import ModelReply, NuruModelClient
from .awareness import GroupAwarenessStore
from .config import Config
from .language import is_expected_language, should_validate_language
from .media import build_reply_message, send_private_voice
from .memory import MemorySearchResult, MemoryStore
from .mood import MoodState, MoodStore, format_mood_reply
from .personality import (
    allowed_personalities,
    build_system_prompt,
    get_profile,
)
from .personality import PersonalityStore
from .queue import ScopeMessageQueue
from .refusal import RefusalLogStore, decide_refusal
from .rules import (
    event_is_tome,
    event_plain_text,
    extract_image_sources,
    is_addressed_group_message,
    is_group_admin,
    is_group_message,
    is_idle_command,
    is_image_generation_request,
    is_personality_command,
    is_private_message,
    parse_idle_command,
    parse_image_generation_prompt,
    parse_personality_command,
)

__plugin_meta__ = PluginMetadata(
    name="Nuru Chat",
    description="AI VTuber backend with memory, mood, media, and QQ group awareness.",
    usage=(
        "Mention Nuru in a group or send a private message. "
        "Group admins can use 'nuru personality <name>'."
    ),
    config=Config,
)

config = get_plugin_config(Config)
driver = get_driver()

memory_store = MemoryStore(
    sqlite_path=config.nuru_memory_sqlite_path,
    chroma_path=config.nuru_chroma_path,
    collection_name=config.nuru_chroma_collection,
    embedding_dimension=config.nuru_embedding_dimension,
)
mood_store = MoodStore(config.nuru_memory_sqlite_path)
personality_store = PersonalityStore(
    sqlite_path=config.nuru_memory_sqlite_path,
    default_personality=config.nuru_default_personality,
)
awareness_store = GroupAwarenessStore(config.nuru_memory_sqlite_path)
model_client = NuruModelClient(config)
refusal_store = RefusalLogStore(config.nuru_memory_sqlite_path)
message_queue = ScopeMessageQueue(
    max_queue_depth=config.nuru_max_queue_depth,
    busy_message=config.nuru_busy_message,
)


async def is_personality_admin_command(event: GroupMessageEvent) -> bool:
    return is_admin_command_event(
        event,
        is_personality_command(event, config.nuru_personality_command_prefix),
    )


async def is_idle_admin_command(event: GroupMessageEvent) -> bool:
    return is_admin_command_event(
        event,
        is_idle_command(event, config.nuru_idle_command_prefix),
    )


group_personality_admin = on_message(
    rule=Rule(is_personality_admin_command),
    priority=3,
    block=True,
)
group_idle_admin = on_message(
    rule=Rule(is_idle_admin_command),
    priority=4,
    block=True,
)
group_observer = on_message(rule=Rule(is_group_message), priority=90, block=False)
group_chat = on_message(
    rule=Rule(is_addressed_group_message),
    priority=10,
    block=True,
)
private_chat = on_message(
    rule=Rule(is_private_message),
    priority=10,
    block=True,
)

_idle_task: Optional[asyncio.Task] = None


@group_personality_admin.handle()
async def handle_personality_admin(event: GroupMessageEvent) -> None:
    requested = parse_personality_command(
        event_plain_text(event),
        config.nuru_personality_command_prefix,
    )
    available = allowed_personalities(config.personality_names())
    current = personality_store.get_personality("group", str(event.group_id))

    if requested in {None, "list"}:
        await group_personality_admin.finish(
            f"Current personality: {current}. Available: {', '.join(available)}"
        )

    requested = requested.strip().lower()
    if requested not in available:
        await group_personality_admin.finish(
            f"Unknown personality '{requested}'. Available: {', '.join(available)}"
        )

    personality_store.set_personality(
        "group",
        str(event.group_id),
        requested,
        str(event.user_id),
    )
    await group_personality_admin.finish(f"Personality switched to {requested}.")


@group_idle_admin.handle()
async def handle_idle_admin(event: GroupMessageEvent) -> None:
    command = parse_idle_command(
        event_plain_text(event),
        config.nuru_idle_command_prefix,
    )
    group_id = str(event.group_id)
    settings = awareness_store.idle_settings(group_id)

    if command in {None, "status"}:
        interval = settings.get("idle_interval_seconds", config.nuru_idle_min_seconds)
        quiet = settings.get("quiet_mode", config.nuru_quiet_mode_default)
        await group_idle_admin.finish(
            f"Idle interval: {interval}s. Quiet mode: {'on' if quiet else 'off'}."
        )

    normalized = command.strip().lower()
    if normalized == "off":
        awareness_store.set_idle_interval(group_id, 0, str(event.user_id))
        await group_idle_admin.finish("Idle messages disabled for this group.")

    if normalized.startswith("quiet "):
        value = normalized.split(" ", 1)[1].strip()
        if value not in {"on", "off"}:
            await group_idle_admin.finish("Use: nuru idle quiet on|off")
        awareness_store.set_quiet_mode(group_id, value == "on", str(event.user_id))
        await group_idle_admin.finish(f"Quiet mode {'enabled' if value == 'on' else 'disabled'}.")

    try:
        interval_seconds = int(normalized)
    except ValueError:
        await group_idle_admin.finish("Use: nuru idle <seconds>|off|quiet on|quiet off")

    awareness_store.set_idle_interval(group_id, interval_seconds, str(event.user_id))
    await group_idle_admin.finish(f"Idle interval set to {interval_seconds}s.")


@group_observer.handle()
async def observe_group_message(event: GroupMessageEvent) -> None:
    record_group_activity(event)


@group_chat.handle()
async def handle_group_chat(bot: Bot, event: GroupMessageEvent) -> None:
    record_group_activity(event)
    group_id = str(event.group_id)
    reply = await message_queue.run(
        scope_key=f"group:{group_id}",
        min_gap_seconds=config.nuru_group_min_reply_gap_seconds,
        factory=lambda: build_chat_reply(
            scope_type="group",
            scope_id=group_id,
            user_id=str(event.user_id),
            user_name=display_name(event),
            event=event,
            addressed=True,
        ),
        busy_factory=lambda message: ModelReply(text=message),
    )
    if reply.image is not None and not reply.text:
        reply.text = reply.image.text
    message = build_reply_message(reply.text, reply.image)
    awareness_store.mark_bot_activity(str(event.group_id))
    await group_chat.finish(message)


@private_chat.handle()
async def handle_private_chat(bot: Bot, event: PrivateMessageEvent) -> None:
    user_id = str(event.user_id)
    reply = await message_queue.run(
        scope_key=f"private:{user_id}",
        min_gap_seconds=config.nuru_private_min_reply_gap_seconds,
        factory=lambda: build_chat_reply(
            scope_type="private",
            scope_id=user_id,
            user_id=user_id,
            user_name=display_name(event),
            event=event,
            addressed=True,
        ),
        busy_factory=lambda message: ModelReply(text=message),
    )
    message = build_reply_message(reply.text, reply.image)
    await private_chat.send(message)
    await send_private_voice(bot, int(event.user_id), reply.voice)
    await private_chat.finish()


async def build_chat_reply(
    scope_type: str,
    scope_id: str,
    user_id: str,
    user_name: str,
    event: MessageEvent,
    addressed: bool,
) -> ModelReply:
    text = event_plain_text(event).strip()
    images = extract_image_sources(event)
    image_prompt = parse_image_generation_prompt(
        text,
        config.image_generation_commands(),
    )
    is_image_request = is_image_generation_request(
        text,
        config.image_generation_commands(),
    )

    if should_validate_language(text, bool(images), is_image_request):
        if not is_expected_language(text, config.nuru_required_language):
            return ModelReply(text=config.nuru_language_warning)

    mood = mood_store.update_from_message(
        scope_type,
        scope_id,
        text,
        addressed=addressed,
        has_image=bool(images),
    )
    personality_name = personality_store.get_personality(scope_type, scope_id)
    profile = get_profile(personality_name)
    refusal = decide_refusal(
        text=text,
        mood=mood,
        blocked_terms=config.refusal_terms(),
        energy_threshold=config.nuru_refusal_energy_threshold,
        low_energy_message=config.nuru_low_energy_refusal,
        safety_message=config.nuru_safety_refusal,
    )
    if refusal.refused:
        refusal_store.add(scope_type, scope_id, user_id, refusal.reason, text)
        return ModelReply(
            text=format_mood_reply(
                refusal.message,
                mood,
                profile.base_reply_limit,
                config.mood_emoticons(),
            )
        )

    if image_prompt is not None:
        image = await model_client.generate_image(image_prompt)
        image.text = format_mood_reply(
            image.text,
            mood,
            profile.base_reply_limit,
            config.mood_emoticons(),
        )
        content = f"[image generation] {image_prompt}"
        save_memory(
            scope_type,
            scope_id,
            user_id,
            user_name,
            "user",
            content,
            "image_request",
            mood,
            profile.name,
        )
        save_memory(
            scope_type,
            scope_id,
            user_id,
            "Nuru",
            "assistant",
            image.text or image.url or "[generated image]",
            "image",
            mood,
            profile.name,
        )
        return ModelReply(text=image.text, image=image)

    visual_context = await model_client.recognize_images(text, images)
    memory_text = "\n".join(part for part in [text, visual_context] if part).strip()
    if not memory_text and images:
        memory_text = "[image message]"

    embedding = await model_client.embed_text(memory_text or text or "[empty]")
    save_memory(
        scope_type,
        scope_id,
        user_id,
        user_name,
        "user",
        memory_text or text,
        "image" if images else "text",
        mood,
        profile.name,
        embedding=embedding,
    )

    payload = build_model_payload(
        scope_type=scope_type,
        scope_id=scope_id,
        user_id=user_id,
        user_name=user_name,
        text=text,
        images=images,
        visual_context=visual_context,
        mood=mood,
        personality_name=profile.name,
        system_prompt=build_system_prompt(profile, mood),
        memories=memory_store.recall(
            user_id=user_id,
            query=memory_text or text,
            embedding=embedding,
            limit=config.nuru_memory_recall_limit,
        ),
        group_memories=memory_store.recall_scope(
            "group",
            scope_id,
            memory_text or text,
            limit=config.nuru_memory_recall_limit,
        )
        if scope_type == "group"
        else [],
    )
    reply = await model_client.create_chat_reply(payload)
    reply.text = format_mood_reply(
        reply.text,
        mood,
        profile.base_reply_limit,
        config.mood_emoticons(),
    )
    save_memory(
        scope_type,
        scope_id,
        user_id,
        "Nuru",
        "assistant",
        reply.text,
        "text",
        mood,
        profile.name,
    )
    return reply


def build_model_payload(
    scope_type: str,
    scope_id: str,
    user_id: str,
    user_name: str,
    text: str,
    images: List[str],
    visual_context: str,
    mood: MoodState,
    personality_name: str,
    system_prompt: str,
    memories: List[MemorySearchResult],
    group_memories: List[MemorySearchResult],
) -> Dict[str, Any]:
    return {
        "event_type": "message",
        "scope": {"type": scope_type, "id": scope_id},
        "user": {"id": user_id, "name": user_name},
        "text": text,
        "images": images,
        "visual_context": visual_context,
        "personality": personality_name,
        "system_prompt": system_prompt,
        "mood": {
            "label": mood.label,
            "energy": mood.energy,
            "affection": mood.affection,
            "sass": mood.sass,
            "curiosity": mood.curiosity,
        },
        "recent_messages": [
            {
                "role": record.role,
                "user": record.user_name,
                "content": record.content,
                "mood": record.mood_label,
                "personality": record.personality,
            }
            for record in memory_store.recent_messages(
                scope_type,
                scope_id,
                config.nuru_memory_recent_limit,
            )
        ],
        "recalled_memories": [
            {
                "score": item.score,
                "role": item.record.role,
                "user": item.record.user_name,
                "content": item.record.content,
            }
            for item in memories
        ],
        "group_memories": [
            {
                "score": item.score,
                "role": item.record.role,
                "user": item.record.user_name,
                "content": item.record.content,
            }
            for item in group_memories
        ],
        "group_topics": [
            {
                "topic": topic.term,
                "count": topic.count,
                "sample": topic.sample,
            }
            for topic in memory_store.group_topics(scope_id)
        ]
        if scope_type == "group"
        else [],
        "participants": [
            {
                "id": participant.user_id,
                "name": participant.display_name,
                "message_count": participant.message_count,
            }
            for participant in awareness_store.recent_participants(scope_id)
        ]
        if scope_type == "group"
        else [],
    }


def save_memory(
    scope_type: str,
    scope_id: str,
    user_id: str,
    user_name: str,
    role: str,
    content: str,
    content_type: str,
    mood: MoodState,
    personality: str,
    embedding: Optional[List[float]] = None,
) -> None:
    if not content:
        return
    memory_store.add_message(
        scope_type=scope_type,
        scope_id=scope_id,
        user_id=user_id,
        user_name=user_name,
        role=role,
        content=content,
        content_type=content_type,
        embedding=embedding,
        mood_label=mood.label,
        personality=personality,
    )


def record_group_activity(event: GroupMessageEvent) -> None:
    awareness_store.record_group_message(
        group_id=str(event.group_id),
        user_id=str(event.user_id),
        display_name=display_name(event),
    )


def display_name(event: MessageEvent) -> str:
    sender = getattr(event, "sender", None)
    for attribute in ("card", "nickname"):
        value = getattr(sender, attribute, "")
        if value:
            return str(value)
    return str(getattr(event, "user_id", "unknown"))


def is_admin_command_event(event: GroupMessageEvent, command_matches: bool) -> bool:
    if not command_matches or not is_group_admin(event):
        return False
    if config.nuru_admin_requires_mention and not event_is_tome(event):
        return False
    return True


@driver.on_startup
async def start_idle_scheduler() -> None:
    global _idle_task
    if config.nuru_idle_enabled and _idle_task is None:
        _idle_task = asyncio.create_task(idle_loop())


@driver.on_shutdown
async def stop_idle_scheduler() -> None:
    if _idle_task is not None:
        _idle_task.cancel()


async def idle_loop() -> None:
    while True:
        await asyncio.sleep(max(10, config.nuru_idle_check_seconds))
        await send_idle_messages()


async def send_idle_messages() -> None:
    bots = get_bots()
    if not bots:
        return
    bot = next(iter(bots.values()))
    for group_id in awareness_store.idle_group_ids(
        min_idle_seconds=config.nuru_idle_min_seconds,
        configured_group_ids=config.idle_group_ids(),
        quiet_mode_default=config.nuru_quiet_mode_default,
    ):
        text = await model_client.create_idle_message(
            {
                "event_type": "idle",
                "scope": {"type": "group", "id": group_id},
                "prompt": config.nuru_idle_prompt,
                "participants": [
                    {
                        "id": participant.user_id,
                        "name": participant.display_name,
                    }
                    for participant in awareness_store.recent_participants(group_id)
                ],
            }
        )
        await bot.send_group_msg(group_id=int(group_id), message=text)
        awareness_store.mark_bot_activity(group_id)
