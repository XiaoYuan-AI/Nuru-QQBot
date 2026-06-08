# Nuru QQ Bot

Nuru QQ Bot is a NoneBot2 backend for a Neuro-sama-like AI VTuber on QQ using
the OneBot V11 adapter. The `nuru_chat` plugin handles private messages, group
mentions, long-term memory, mood/personality state, image tasks, optional voice
messages, queued generation, local tool use, dialogue reflection, refusal logging,
and scheduled idle group messages.

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
|           |-- moderation.py
|           |-- mood.py
|           |-- observability.py
|           |-- personality.py
|           |-- plugin.py
|           |-- queue.py
|           |-- reflection.py
|           |-- refusal.py
|           |-- rules.py
|           |-- tools.py
|           `-- working_memory.py
`-- tests/
    |-- test_awareness.py
    |-- test_media.py
    |-- test_memory.py
    |-- test_mood.py
    |-- test_observability.py
    |-- test_queue.py
    |-- test_reflection.py
    |-- test_rules.py
    `-- test_tools.py
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
- `docker build -t nuru-qqbot .` builds the container image.

## Configuration

The plugin uses SQLite for conversation, mood, group, and personality state, and
ChromaDB for semantic memory under `data/nuru_chat/` by default. Configure model
API, image, voice, idle-message, and personality settings in `.env`.

## Chat Behavior

- Private chats respond normally.
- Group chats respond only when the bot is @mentioned, except scheduled idle
  messages.
- Group memory is scoped by group, so recalled topics and inside jokes stay tied
  to the group where they happened.
- Mood changes reply length, formality, and optional emoticon suffixes.
- Tool phrases are handled locally before model generation: `calculate 2+2`,
  `calendar add stream at tomorrow 20:00`, `calendar list`,
  `remind me hydrate at 21:00`, and `reminders list`.
- Dialogue reflection writes private summaries back into long-term memory.
- Structured observability events are appended to
  `NURU_OBSERVABILITY_LOG_PATH` when enabled.

## Admin Commands

When `NURU_ADMIN_REQUIRES_MENTION=true`, group admin commands must mention the
bot. Examples:

- `@Nuru nuru personality list`
- `@Nuru nuru personality evil`
- `@Nuru nuru idle status`
- `@Nuru nuru idle 600`
- `@Nuru nuru idle off`
- `@Nuru nuru idle quiet on`
- `@Nuru nuru idle quiet off`
