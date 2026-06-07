# Nuru QQ Bot

Nuru QQ Bot is a NoneBot2 backend for a Neuro-sama-like AI VTuber on QQ using
the OneBot V11 adapter. The `nuru_chat` plugin handles private messages, group
mentions, long-term memory, mood/personality state, image tasks, optional voice
messages, and scheduled idle group messages.

## Project Tree

```text
.
|-- bot.py
|-- pyproject.toml
|-- requirements.txt
|-- src/
|   `-- plugins/
|       `-- nuru_chat/
|           |-- __init__.py
|           |-- api.py
|           |-- awareness.py
|           |-- config.py
|           |-- language.py
|           |-- media.py
|           |-- memory.py
|           |-- mood.py
|           |-- personality.py
|           |-- plugin.py
|           `-- rules.py
`-- tests/
    |-- test_memory.py
    |-- test_mood.py
    `-- test_rules.py
```

## Setup

1. Create and activate a Python 3.9+ virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and configure the Nuru model API values.
4. Run the bot with `nb run --reload` or `python bot.py`.

## Useful Commands

- `python bot.py` starts the bot directly.
- `nb run --reload` starts the bot through NoneBot CLI with reload support.
- `python -m compileall -q bot.py src tests` checks syntax.
- `pytest` runs unit tests.

## Configuration

The plugin uses SQLite for conversation, mood, group, and personality state, and
ChromaDB for semantic memory under `data/nuru_chat/` by default. Configure model
API, image, voice, idle-message, and personality settings in `.env`.
