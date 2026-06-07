from typing import Optional

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

from .api import ImageResult, VoicePayload


def build_reply_message(text: str, image: Optional[ImageResult] = None) -> Message:
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


async def send_private_voice(bot: Bot, user_id: int, voice: Optional[VoicePayload]) -> None:
    if voice is None:
        return
    file_value = voice_file_value(voice)
    if not file_value:
        return
    await bot.send_private_msg(
        user_id=int(user_id),
        message=MessageSegment.record(file=file_value),
    )


def image_file_value(image: ImageResult) -> str:
    if image.url:
        return image.url
    if image.base64_data:
        if image.base64_data.startswith("base64://"):
            return image.base64_data
        return f"base64://{image.base64_data}"
    return ""


def voice_file_value(voice: VoicePayload) -> str:
    if voice.file:
        return voice.file
    if voice.base64_data:
        if voice.base64_data.startswith("base64://"):
            return voice.base64_data
        return f"base64://{voice.base64_data}"
    return ""
