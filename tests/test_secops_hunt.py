"""Tests for Google SecOps threat hunting skill and command."""

import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "plugins/cloud/google-secops/skills/hunt/SKILL.md"
COMMAND_PATH = REPO_ROOT / "plugins/cloud/google-secops/commands/secops/hunt.toml"


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML-like frontmatter between --- markers without external dependencies."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    assert match is not None, (
        "SKILL.md must contain valid YAML frontmatter between --- markers"
    )
    frontmatter_raw = match.group(1)
    body = match.group(2)

    data: dict[str, str] = {}
    current_key: str | None = None
    multiline_buf: list[str] = []

    for line in frontmatter_raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key_val_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if key_val_match and not line.startswith(" "):
            if current_key and multiline_buf:
                data[current_key] = " ".join(multiline_buf).strip()
                multiline_buf = []
            key, val = key_val_match.group(1), key_val_match.group(2).strip()
            current_key = key
            if val in (">-", ">", "|-", "|"):
                continue
            data[key] = val
        elif current_key and line.startswith("  "):
            multiline_buf.append(line.strip())

    if current_key and multiline_buf:
        data[current_key] = " ".join(multiline_buf).strip()

    return data, body


def test_hunt_skill_file_exists() -> None:
    """Verify that hunt/SKILL.md exists at the expected public path."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"


def test_hunt_skill_frontmatter_standards() -> None:
    """Verify that hunt/SKILL.md adheres to YAML frontmatter standards."""
    assert SKILL_PATH.is_file()
    content = SKILL_PATH.read_text(encoding="utf-8")
    frontmatter, _ = _parse_frontmatter(content)

    assert "name" in frontmatter, "Frontmatter must contain 'name'"
    assert frontmatter["name"] in ("hunt", "secops-hunt"), (
        f"Skill name '{frontmatter['name']}' must be 'hunt' or 'secops-hunt'"
    )

    assert "description" in frontmatter, "Frontmatter must contain 'description'"
    assert len(frontmatter["description"]) <= 1024, (
        "Description must not exceed 1024 characters"
    )
    assert len(frontmatter["description"]) >= 20, "Description must be substantive"


def test_hunt_skill_documentation_sections() -> None:
    """Verify documentation of workflows, IoC analysis, prevalence, and outliers."""
    assert SKILL_PATH.is_file()
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    lower_body = body.lower()

    # 1. Proactive threat hunting workflows
    assert "proactive" in lower_body
    assert "threat hunt" in lower_body or "threat hunting" in lower_body
    assert "workflow" in lower_body or "procedure" in lower_body

    # 2. IoC retroactive analysis
    assert "ioc" in lower_body or "indicator" in lower_body
    assert "retroactive" in lower_body
    assert "udm" in lower_body

    # 3. Prevalence searching
    assert "prevalence" in lower_body

    # 4. Outlier detection
    assert "outlier" in lower_body


def test_hunt_command_slash_definition() -> None:
    """Verify that commands/secops/hunt.toml defines valid slash command configuration."""
    assert COMMAND_PATH.is_file(), f"Expected command file at {COMMAND_PATH}"
    content = COMMAND_PATH.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)

    assert "prompt" in parsed, "Command TOML must contain 'prompt'"
    prompt_str = parsed["prompt"]
    assert "hunt" in prompt_str, "Command prompt must reference hunt skill"
    assert "{{args}}" in prompt_str, "Command prompt must accept '{{args}}' placeholder"
