import asyncio
import base64
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import httpx
from loguru import logger

from .config import Config
from .memory import deterministic_embedding


@dataclass
class ImageResult:
    url: Optional[str] = None
    base64_data: Optional[str] = None
    text: str = ""


@dataclass
class VoicePayload:
    file: Optional[str] = None
    base64_data: Optional[str] = None


@dataclass
class ModelReply:
    text: str
    image: Optional[ImageResult] = None
    voice: Optional[VoicePayload] = None


class NuruModelClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    async def embed_text(self, text: str) -> List[float]:
        data = await self._post_json(
            self.config.nuru_embeddings_endpoint,
            {"input": text, "dimensions": self.config.nuru_embedding_dimension},
        )
        embedding = data.get("embedding")
        data_item = _first_data_item(data)
        if embedding is None and isinstance(data_item, dict):
            embedding = data_item.get("embedding")
        if _is_number_list(embedding):
            return [float(value) for value in embedding]
        return deterministic_embedding(text, self.config.nuru_embedding_dimension)

    async def create_chat_reply(self, payload: Dict[str, Any]) -> ModelReply:
        data = await self._post_json(self.config.nuru_chat_endpoint, payload)
        if data.get("_api_failed"):
            return ModelReply(text=self.config.nuru_busy_message)
        text = _extract_text(data)
        if not text:
            text = self._fallback_reply(payload)

        voice = None
        if self.config.nuru_voice_enabled and _chance(self.config.nuru_voice_probability):
            voice = await self.synthesize_voice(text)

        return ModelReply(text=text, voice=voice)

    async def create_idle_message(self, payload: Dict[str, Any]) -> str:
        data = await self._post_json(self.config.nuru_chat_endpoint, payload)
        if data.get("_api_failed"):
            return self.config.nuru_busy_message
        return _extract_text(data) or "It got quiet in here, so I came back to poke chat."

    async def recognize_images(self, text: str, images: Sequence[str]) -> str:
        if not images or not self.config.nuru_image_recognition_enabled:
            return ""
        data = await self._post_json(
            self.config.nuru_vision_endpoint,
            {"text": text, "images": list(images)},
        )
        return _extract_text(data)

    async def generate_image(self, prompt: str) -> ImageResult:
        if not self.config.nuru_image_generation_enabled:
            return ImageResult(text="Image generation is disabled.")
        data = await self._post_json(
            self.config.nuru_image_generation_endpoint,
            {"prompt": prompt},
        )
        if data.get("_api_failed"):
            return ImageResult(text=self.config.nuru_busy_message)
        image_data = data.get("image") or _first_data_item(data)
        if isinstance(image_data, dict):
            return ImageResult(
                url=image_data.get("url"),
                base64_data=image_data.get("b64_json") or image_data.get("base64"),
                text=_extract_text(data),
            )
        return ImageResult(text=_extract_text(data) or "I could not generate an image.")

    async def synthesize_voice(self, text: str) -> Optional[VoicePayload]:
        data = await self._post_json(
            self.config.nuru_tts_endpoint,
            {"text": text, "mode": self.config.nuru_voice_mode},
        )
        file_value = data.get("file") or data.get("url")
        base64_value = data.get("base64") or data.get("b64_json")
        if file_value:
            return VoicePayload(file=str(file_value))
        if base64_value:
            return VoicePayload(base64_data=str(base64_value))
        audio_bytes = data.get("audio")
        if isinstance(audio_bytes, bytes):
            return VoicePayload(base64_data=base64.b64encode(audio_bytes).decode("ascii"))
        return None

    async def _post_json(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.nuru_api_base_url:
            return {}

        url = self.config.nuru_api_base_url.rstrip("/") + "/" + endpoint.lstrip("/")
        headers = {}
        if self.config.nuru_api_key:
            headers["Authorization"] = f"Bearer {self.config.nuru_api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.config.nuru_api_timeout_seconds) as client:
                attempts = max(1, self.config.nuru_api_retries + 1)
                for attempt in range(attempts):
                    try:
                        response = await client.post(url, json=payload, headers=headers)
                        response.raise_for_status()
                        data = response.json()
                        return data if isinstance(data, dict) else {}
                    except Exception as exc:
                        if attempt >= attempts - 1:
                            raise exc
                        delay = self.config.nuru_api_backoff_seconds * (2**attempt)
                        logger.warning(
                            "Nuru model API request failed for {} on attempt {}: {}",
                            endpoint,
                            attempt + 1,
                            exc,
                        )
                        await asyncio.sleep(delay)
        except Exception as exc:
            logger.warning("Nuru model API request failed for {} after retries: {}", endpoint, exc)
            return {"_api_failed": True}

    def _fallback_reply(self, payload: Dict[str, Any]) -> str:
        text = str(payload.get("text") or "").strip()
        mood = payload.get("mood", {})
        label = mood.get("label", "balanced") if isinstance(mood, dict) else "balanced"
        if not text:
            return "I saw that, but I need a little more to work with."
        if label == "mischievous":
            return f"I heard you. Tiny streamer brain says: {text[:120]}"
        if label == "sleepy":
            return f"Mhm... {text[:120]}"
        return f"I heard you: {text[:160]}"


def _extract_text(data: Dict[str, Any]) -> str:
    for key in ("text", "reply", "content", "description", "caption"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    return ""


def _first_data_item(data: Dict[str, Any]) -> Any:
    items = data.get("data")
    if isinstance(items, list) and items:
        return items[0]
    return {}


def _is_number_list(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, (int, float)) for item in value)


def _chance(probability: float) -> bool:
    return random.random() < max(0.0, min(1.0, probability))
