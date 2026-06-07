from pydantic import BaseModel
from typing import List


class Config(BaseModel):
    """Runtime settings for the Nuru chat plugin."""

    nuru_required_language: str = "en"
    nuru_language_warning: str = (
        "Someone tell XiaoYuan151 that there is a problem with my AI."
    )
    nuru_data_dir: str = "data/nuru_chat"
    nuru_memory_sqlite_path: str = "data/nuru_chat/memory.sqlite3"
    nuru_chroma_path: str = "data/nuru_chat/chroma"
    nuru_chroma_collection: str = "nuru_memory"
    nuru_memory_recent_limit: int = 12
    nuru_memory_recall_limit: int = 6
    nuru_embedding_dimension: int = 384

    nuru_api_base_url: str = ""
    nuru_api_key: str = ""
    nuru_chat_endpoint: str = "/chat"
    nuru_embeddings_endpoint: str = "/embeddings"
    nuru_vision_endpoint: str = "/vision"
    nuru_image_generation_endpoint: str = "/images/generations"
    nuru_tts_endpoint: str = "/audio/speech"
    nuru_api_timeout_seconds: float = 30.0

    nuru_default_personality: str = "neuro"
    nuru_available_personalities: str = "neuro,evil,soft,focused"
    nuru_personality_command_prefix: str = "nuru personality"

    nuru_idle_enabled: bool = False
    nuru_idle_check_seconds: int = 60
    nuru_idle_min_seconds: int = 900
    nuru_idle_group_ids: str = ""
    nuru_idle_prompt: str = "Send a short playful idle message to restart chat."

    nuru_image_recognition_enabled: bool = True
    nuru_image_generation_enabled: bool = True
    nuru_image_generation_commands: str = "/draw,/imagine"

    nuru_voice_enabled: bool = False
    nuru_voice_probability: float = 1.0
    nuru_voice_mode: str = "file"

    def personality_names(self) -> List[str]:
        return _csv_values(self.nuru_available_personalities)

    def idle_group_ids(self) -> List[str]:
        return _csv_values(self.nuru_idle_group_ids)

    def image_generation_commands(self) -> List[str]:
        return _csv_values(self.nuru_image_generation_commands)


def _csv_values(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
