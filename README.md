# Nuru QQ Bot

Nuru QQ Bot is a small NoneBot2 project for OneBot V11. The current plugin listens
to private messages and group messages that mention the bot, ignores empty or
English messages, and replies with a warning when the message is not English.

## Project Tree

```text
.
├── bot.py
├── pyproject.toml
├── requirements.txt
└── src/
    └── plugins/
        └── nuru_chat/
            ├── __init__.py
            ├── config.py
            ├── language.py
            └── rules.py
```

## Setup

1. Create and activate a Python 3.9+ virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust values if needed.
4. Run the bot with `nb run --reload` or `python bot.py`.

## Configuration

`NURU_REQUIRED_LANGUAGE` controls the accepted language code. `NURU_LANGUAGE_WARNING`
controls the warning sent when a message is rejected.
