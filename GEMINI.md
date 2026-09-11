# GEMINI.md

This file provides guidance to Gemini Code Assist and AI pair programmers working in this repository.

## Code Style and Communication

**CRITICAL: Never use emojis. Anywhere. Ever.**
- No emojis in code comments
- No emojis in commit messages
- No emojis in pull request descriptions
- No emojis in code review comments
- No emojis in documentation
- Emojis are unprofessional and must not be used in any context

## Shell and Environment Variables

- In code and shell examples, define environment variables first (e.g. `PROJECT_ID="..."`) and then reference them as `$PROJECT_ID`.

## Git Worktree and Path Conventions

- This repository adheres to the `<project_name>__worktrees/` convention.
- Primary clone with `.git/` is located at `<project_name>__worktrees/main`.
- Linked worktrees exist as sibling folders (e.g., `<project_name>__worktrees/<branch_name>`).
- Always resolve internal paths relative to `BASE_DIR = Path(__file__).resolve().parent` to maintain portability across sibling worktrees.
- If removing a worktree containing git submodules under `external/`, deinitialize submodules first: `git submodule deinit --all -f` before removing the worktree.

## Project Structure

```text
.
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore configuration
├── GEMINI.md             # AI coding instructions and repo guidelines
├── justfile              # Task runner (setup, install, test, lint, format, clean)
├── manage.py             # Typer + Rich unified CLI
├── pyproject.toml        # PEP 621 dependencies & tool configurations
├── docs/                 # Technical documentation & architecture notes
├── external/             # Git submodules container (MCP servers, external packages)
├── scripts/              # Helper & deployment automation scripts
├── src/
│   └── google__skills/
│       ├── __init__.py
│       ├── py.typed      # PEP 561 marker
│       └── core.py       # Core package implementation
└── tests/
    ├── __init__.py
    ├── conftest.py       # Pytest fixtures and mock setup
    └── test_basic.py     # Basic test suite
```

## Common Commands

| Task | Command | Description |
| :--- | :--- | :--- |
| **Setup** | `just setup` | Create virtualenv, copy `.env.example` to `.env`, and install dependencies |
| **Install** | `just install` | Install editable package and dev dependencies |
| **Run Tests** | `just test` | Run pytest suite |
| **Coverage** | `just test-cov` | Run tests with terminal and HTML coverage report |
| **Lint** | `just lint` | Run ruff check and format inspection |
| **Format** | `just format` | Automatically fix and format code with ruff |
| **Typecheck** | `just typecheck` | Run mypy type analysis |
| **CLI Info** | `python manage.py info` | Print environment status via Typer CLI |
| **Clean** | `just clean` | Remove cache files, coverage reports, and build artifacts |
