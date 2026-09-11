# Setup & Installation - google__skills

## Prerequisites
- Python >= 3.11
- `just` (command runner: `cargo install just` or system package manager)
- `uv` (recommended: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Local Development
1. Run `just setup` to initialize `.env` and install editable dependencies into `.venv`.
2. Run `just test` to verify test suite.
3. Run `just lint` to verify formatting and lint rules.
