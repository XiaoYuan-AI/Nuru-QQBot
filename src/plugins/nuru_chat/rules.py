from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, PrivateMessageEvent


async def is_addressed_group_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and event.is_tome()


async def is_private_message(event: MessageEvent) -> bool:
    return isinstance(event, PrivateMessageEvent)
