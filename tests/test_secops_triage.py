"""Tests for Google SecOps alert triage skill and command."""

import re
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "plugins/cloud/google-secops/skills/triage/SKILL.md"
COMMAND_PATH = REPO_ROOT / "plugins/cloud/google-secops/commands/secops/triage.toml"


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-like frontmatter between --- markers without external dependencies."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    assert match is not None, (
        "SKILL.md must contain valid YAML frontmatter between --- markers"
    )
    frontmatter_raw = match.group(1)
    body = match.group(2)

    data: dict[str, Any] = {}
    current_key: str | None = None
    sub_dict: dict[str, Any] | None = None
    multiline_buf: list[str] = []

    for line in frontmatter_raw.splitlines():
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#"):
            continue

        if line.startswith("  ") and current_key and sub_dict is not None:
            sub_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line_strip)
            if sub_match:
                sub_dict[sub_match.group(1)] = sub_match.group(2).strip("\"'")
            continue

        if current_key and sub_dict is not None:
            data[current_key] = sub_dict
            sub_dict = None

        key_val_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line_strip)
        if key_val_match and not line.startswith(" "):
            if current_key and multiline_buf:
                data[current_key] = " ".join(multiline_buf).strip()
                multiline_buf = []
            key, val = key_val_match.group(1), key_val_match.group(2).strip("\"'")
            current_key = key
            if val in (">-", ">", "|-", "|"):
                continue
            elif not val:
                sub_dict = {}
            else:
                data[key] = val
        elif current_key and line.startswith("  "):
            multiline_buf.append(line_strip)

    if current_key and multiline_buf:
        data[current_key] = " ".join(multiline_buf).strip()
    if current_key and sub_dict is not None:
        data[current_key] = sub_dict

    return data, body


def test_triage_skill_file_exists() -> None:
    """Verify that triage/SKILL.md exists at the expected public path."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"


def test_triage_skill_frontmatter_standards() -> None:
    """Verify that triage/SKILL.md adheres to YAML frontmatter standards."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    frontmatter, _ = _parse_frontmatter(content)

    assert "name" in frontmatter, "Frontmatter must contain 'name'"
    assert frontmatter["name"] in ("triage", "secops-triage"), (
        f"Skill name '{frontmatter['name']}' must be 'triage' or 'secops-triage'"
    )

    assert "description" in frontmatter, "Frontmatter must contain 'description'"
    assert len(frontmatter["description"]) <= 1024, (
        "Description must not exceed 1024 characters"
    )
    assert len(frontmatter["description"]) >= 20, "Description must be substantive"


def test_triage_skill_documentation_sections() -> None:
    """Verify documentation of alert investigation, severity adjustment, entity risk, and closing."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    lower_body = body.lower()

    # 1. Step-by-step alert investigation
    assert "investigation" in lower_body or "investigate" in lower_body, (
        "SKILL.md must document alert investigation"
    )
    assert any(
        term in lower_body
        for term in ["gather context", "alert-specific", "siem search", "udm_search"]
    ), "SKILL.md must detail investigation steps"

    # 2. Severity adjustment
    assert "severity" in lower_body or "priority" in lower_body, (
        "SKILL.md must document severity or priority adjustment"
    )
    assert any(
        term in lower_body
        for term in [
            "severity adjustment",
            "update_case",
            "change_case_priority",
            "escalate",
        ]
    ), "SKILL.md must provide actionable severity adjustment guidance"

    # 3. Entity risk assessment
    assert "entity" in lower_body and "risk" in lower_body, (
        "SKILL.md must document entity risk assessment"
    )
    assert any(
        term in lower_body
        for term in [
            "enrich",
            "enrichment",
            "summarize_entity",
            "lookup_entity",
            "ioc",
        ]
    ), "SKILL.md must describe entity enrichment and IoC matching"

    # 4. Triage closing
    assert any(
        term in lower_body
        for term in ["closing", "close case", "execute_bulk_close_case"]
    ), "SKILL.md must document triage closing procedures"
    assert any(
        term in lower_body
        for term in ["false positive", "benign true positive", "fp", "btp"]
    ), "SKILL.md must specify closing criteria for false positives / benign detections"


def test_triage_command_slash_definition() -> None:
    """Verify that commands/secops/triage.toml defines valid slash command configuration."""
    assert COMMAND_PATH.is_file(), f"Expected command file at {COMMAND_PATH}"
    content = COMMAND_PATH.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)

    assert "prompt" in parsed, "Command TOML must contain 'prompt'"
    prompt_str = parsed["prompt"]
    assert "triage" in prompt_str, "Command prompt must reference triage skill"
    assert "{{args}}" in prompt_str, "Command prompt must accept '{{args}}' placeholder"


def test_public_entry_point_discovery() -> None:
    """Verify public entry point discovery of skills and commands without direct module imports."""
    plugin_dir = REPO_ROOT / "plugins/cloud/google-secops"
    assert plugin_dir.is_dir(), f"Expected plugin directory at {plugin_dir}"

    skills_dir = plugin_dir / "skills"
    assert (skills_dir / "triage" / "SKILL.md").is_file(), (
        "Triage skill entry point missing"
    )

    commands_dir = plugin_dir / "commands" / "secops"
    assert (commands_dir / "triage.toml").is_file(), (
        "Triage command entry point missing"
    )
