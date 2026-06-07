from typing import Any, Mapping

from fast_langdetect import detect
from loguru import logger


def is_expected_language(text: str, expected_language: str) -> bool:
    try:
        detected = detect(text)
    except Exception as exc:
        logger.debug("Language detection failed: {}", exc)
        return False

    return _language_code(detected) == expected_language


def _language_code(detected: Mapping[str, Any]) -> str:
    language = detected.get("lang", "")
    if isinstance(language, str):
        return language
    return ""
