from typing import Any, Callable, Optional

def build_reply_message(text: str, image: Optional[Any] = None) -> Any:
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    message = Message()
    if text:
        message += MessageSegment.text(text)

    if image is not None:
        image_file = image_file_value(image)
        if image_file:
            if text:
                message += MessageSegment.text("\n")
            message += MessageSegment.image(file=image_file)
        elif image.text:
            if text:
                message += MessageSegment.text("\n")
            message += MessageSegment.text(image.text)

    return message


async def send_private_voice(
    bot: Any,
    user_id: int,
    voice: Optional[Any],
    record_factory: Optional[Callable[[str], Any]] = None,
) -> None:
    if voice is None:
        return
    file_value = voice_file_value(voice)
    if not file_value:
        return
    if record_factory is not None:
        message = record_factory(file_value)
    else:
        message = _record_segment(file_value)
    await bot.send_private_msg(
        user_id=int(user_id),
        message=message,
    )


def image_file_value(image: Any) -> str:
    if image.url:
        return image.url
    if image.base64_data:
        if image.base64_data.startswith("base64://"):
            return image.base64_data
        return f"base64://{image.base64_data}"
    return ""


def voice_file_value(voice: Any) -> str:
    if voice.file:
        return voice.file
    if voice.base64_data:
        if voice.base64_data.startswith("base64://"):
            return voice.base64_data
        return f"base64://{voice.base64_data}"
    return ""


def _record_segment(file_value: str) -> Any:
    from nonebot.adapters.onebot.v11 import MessageSegment

    return MessageSegment.record(file=file_value)
