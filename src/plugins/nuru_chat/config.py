from pydantic import BaseModel


class Config(BaseModel):
    """Runtime settings for the Nuru chat plugin."""

    nuru_required_language: str = "en"
    nuru_language_warning: str = (
        "Someone tell XiaoYuan151 that there is a problem with my AI."
    )
