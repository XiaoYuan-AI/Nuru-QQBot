try:
    from .plugin import *  # noqa: F401,F403
except ModuleNotFoundError as exc:
    if exc.name is None or not exc.name.startswith("nonebot"):
        raise

    __plugin_meta__ = None
