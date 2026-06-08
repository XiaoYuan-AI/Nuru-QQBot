# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python 3.9+ NoneBot2 QQ bot using the OneBot V11 adapter.

- `bot.py` initializes NoneBot, registers OneBot V11, loads `src/plugins`, and starts the bot.
- `src/plugins/nuru_chat/plugin.py` wires message matchers, admin commands, queues, memory, mood, tools, and idle scheduling.
- `src/plugins/nuru_chat/config.py` defines environment-backed settings. Add new runtime options here and mirror them in `.env.example`.
- `src/plugins/nuru_chat/` keeps behavior split by responsibility: `api.py`, `memory.py`, `mood.py`, `awareness.py`, `rules.py`, `media.py`, `queue.py`, `refusal.py`, `reflection.py`, `tools.py`, `working_memory.py`, `observability.py`, and `moderation.py`.
- `tests/` contains pytest coverage for plugin modules, including mocked OneBot calls in `test_media.py`.

## Build, Test, and Development Commands

- `pip install -r requirements.txt` installs runtime dependencies.
- `python bot.py` starts the bot directly.
- `nb run --reload` starts the bot through NoneBot CLI with reload support.
- `python -m compileall -q bot.py src tests` checks syntax.
- `pytest` runs unit tests.
- `git diff --check` checks whitespace before committing.
- `docker build -t nuru-qqbot .` builds the container image.

## Coding Style & Naming Conventions

Use 4-space indentation, type hints for new public helpers, and focused modules that match the current layout. Use snake_case for files, modules, functions, and variables. Use PascalCase for classes such as `Config`, `MemoryStore`, and `NuruModelClient`. Keep matcher names descriptive, for example `group_chat`, `private_chat`, or `group_idle_admin`.

## Testing Guidelines

Use `pytest` and name files `tests/test_<module>.py`. Prefer small unit tests for memory, mood, group rules, queue behavior, moderation, and API fallback paths. Mock OneBot API calls instead of requiring a live adapter connection.

## Commit & Pull Request Guidelines

History uses Conventional Commits. Use messages such as `feat: add group memory topics`, `fix: retry Nuru API failures`, `test: cover group mention rules`, or `docs: update admin commands`.

Pull requests should include a short summary, test results, linked issues when relevant, and any `.env.example` changes. Include screenshots or logs only when behavior cannot be verified from tests.

## Security & Configuration Tips

Do not commit real `.env` files, QQ credentials, API keys, generated memory databases, Chroma indexes, or observability logs. Keep safe defaults in `Config` and document every new environment variable in `.env.example`.
