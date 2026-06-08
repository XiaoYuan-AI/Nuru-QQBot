from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class ModerationResult:
    text: str
    safe: bool
    categories: List[str]
    rewritten: bool = False


def moderate_output(
    text: str,
    blocked_terms: Iterable[str],
    rewrite_message: str,
) -> ModerationResult:
    lowered = text.lower()
    categories = [
        term.strip().lower()
        for term in blocked_terms
        if term.strip() and term.strip().lower() in lowered
    ]
    if not categories:
        return ModerationResult(text=text, safe=True, categories=[])
    return ModerationResult(
        text=rewrite_message,
        safe=False,
        categories=categories,
        rewritten=True,
    )
