from fast_langdetect import detect
from nonebot import get_plugin_config, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata
from nonebot_plugin_userinfo import get_user_info

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="handle",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

handle_message = on_message()


@handle_message.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent):
    if event.is_tome():
        text = event.get_plaintext()
        if text == "":
            await handle_message.finish()
        if not detect(text)["lang"] == "en":
            await handle_message.finish("Someone tell XiaoYuan151 that there is a problem with my AI.")
        else:
            user_info = await get_user_info(bot, event, event.get_user_id())
            if event.reply:
                reply_info = await get_user_info(bot, event, str(event.reply.sender.user_id))
                input = f"{user_info.user_name}: {reply_info.user_name} said \"{event.reply.message}\"\n{text}"
            else:
                input = f"{user_info.user_name}: {text}"
            await handle_message.finish()


handle_private_message = on_message()


@handle_private_message.handle()
async def handle_function(bot: Bot, event: PrivateMessageEvent):
    text = event.get_plaintext()
    if text == "":
        await handle_private_message.finish()
    if not detect(text)["lang"] == "en":
        await handle_private_message.finish("Someone tell XiaoYuan151 that there is a problem with my AI.")
    else:
        user_info = await get_user_info(bot, event, event.get_user_id())
        input = f"{user_info.user_name}: {text}"
        await handle_private_message.finish()
