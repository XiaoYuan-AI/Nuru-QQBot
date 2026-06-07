from typing import Optional

from nonebot import get_plugin_config, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .config import Config
from .language import is_expected_language
from .rules import is_addressed_group_message, is_private_message

__plugin_meta__ = PluginMetadata(
    name="Nuru Chat",
    description="Validates chat messages before Nuru handles them.",
    usage="Mention Nuru in a group or send a private message. Non-English text is rejected.",
    config=Config,
)

config = get_plugin_config(Config)

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


def get_rejection_message(event: MessageEvent) -> Optional[str]:
    text = event.get_plaintext().strip()
    if not text:
        return None

    if not is_expected_language(text, config.nuru_required_language):
        return config.nuru_language_warning

    return None


@group_chat.handle()
async def handle_group_chat(event: GroupMessageEvent) -> None:
    rejection_message = get_rejection_message(event)
    if rejection_message is not None:
        await group_chat.finish(rejection_message)
    await group_chat.finish()


@private_chat.handle()
async def handle_private_chat(event: PrivateMessageEvent) -> None:
    rejection_message = get_rejection_message(event)
    if rejection_message is not None:
        await private_chat.finish(rejection_message)
    await private_chat.finish()
