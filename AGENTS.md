# Repository Guidelines

## Project Structure & Module Organization

This is a small NoneBot2 QQ bot using the OneBot V11 adapter.

- `bot.py` is the runtime entry point. It initializes NoneBot, registers the adapter, loads plugins from `src/plugins`, and starts the bot.
- `src/plugins/nuru_chat/` contains the current plugin.
- `src/plugins/nuru_chat/__init__.py` wires matchers and handler flow.
- `src/plugins/nuru_chat/config.py` defines environment-backed plugin settings.
- `src/plugins/nuru_chat/language.py` contains language detection helpers.
- `src/plugins/nuru_chat/rules.py` contains matcher rules.
- Tests live under `tests/`, mirroring plugin module names where practical.

## Build, Test, and Development Commands

- `pip install -r requirements.txt` installs runtime dependencies.
- `python bot.py` starts the bot directly.
- `nb run --reload` starts the bot through NoneBot CLI with reload support.
- `python -m compileall -q bot.py src tests` checks Python syntax without running the bot.
- `pytest` runs unit tests.
- `git diff --check` checks for whitespace errors before commit.

Use Python 3.9 or newer, matching `pyproject.toml`.

## Coding Style & Naming Conventions

Use 4-space indentation and type hints for new functions. Keep modules focused by responsibility, following the existing split between config, rules, language helpers, and matcher wiring.

Use snake_case for files, modules, functions, and variables. Use PascalCase for Pydantic config classes. Prefer clear matcher names such as `group_chat` or `private_chat` over generic names like `handler`.

Avoid broad refactors unless they directly support the change being made.

## Testing Guidelines

Use `pytest`. Place tests in `tests/`, use filenames like `test_language.py`, and keep plugin behavior tests close to the module they validate. Cover memory, mood, matcher rules, and language/media behavior before changing bot flow.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commits. Follow the same format:

- `feat: add chat response backend`
- `fix: handle language detection failures`
- `refactor: restructure chat plugin`
- `chore: update dependencies`

Pull requests should include a short summary, test results, linked issues when relevant, and configuration changes such as new `.env.example` keys. Include screenshots or logs only when behavior is difficult to verify from code.

## Security & Configuration Tips

Do not commit real `.env` files, tokens, QQ credentials, or adapter secrets. Document new configuration in `.env.example` and keep safe defaults in `Config`.
