"""Tests for Google SecOps investigation skill and command."""

import re
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = (
    REPO_ROOT
    / "plugins"
    / "cloud"
    / "google-secops"
    / "skills"
    / "investigate"
    / "SKILL.md"
)
COMMAND_PATH = (
    REPO_ROOT
    / "plugins"
    / "cloud"
    / "google-secops"
    / "commands"
    / "secops"
    / "investigate.toml"
)


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
        if not line.strip() or line.strip().startswith("#"):
            continue
        key_val_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if key_val_match and not line.startswith(" "):
            if current_key and multiline_buf:
                data[current_key] = " ".join(multiline_buf).strip()
                multiline_buf = []
            if current_key and sub_dict is not None:
                data[current_key] = sub_dict
                sub_dict = None

            key, val = key_val_match.group(1), key_val_match.group(2).strip()
            current_key = key
            if val in (">-", ">", "|-", "|"):
                continue
            elif not val:
                sub_dict = {}
            else:
                data[key] = val.strip("\"'")
        elif current_key and sub_dict is not None and line.startswith("  "):
            sub_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line.strip())
            if sub_match:
                k, v = sub_match.group(1), sub_match.group(2).strip("\"'")
                sub_dict[k] = v
        elif current_key and line.startswith("  "):
            multiline_buf.append(line.strip())

    if current_key and multiline_buf:
        data[current_key] = " ".join(multiline_buf).strip()
    if current_key and sub_dict is not None:
        data[current_key] = sub_dict

    return data, body


def test_investigate_skill_file_exists() -> None:
    """Verify that investigate/SKILL.md exists at the expected public path."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"


def test_investigate_skill_frontmatter_standards() -> None:
    """Verify that investigate/SKILL.md adheres to YAML frontmatter standards."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    frontmatter, _ = _parse_frontmatter(content)

    assert "name" in frontmatter, "Frontmatter must contain 'name'"
    assert frontmatter["name"] in ("investigate", "secops-investigate"), (
        f"Skill name '{frontmatter['name']}' must be 'investigate' or 'secops-investigate'"
    )

    assert "description" in frontmatter, "Frontmatter must contain 'description'"
    assert len(frontmatter["description"]) <= 1024, (
        "Description must not exceed 1024 characters"
    )
    assert len(frontmatter["description"]) >= 20, "Description must be substantive"

    if "metadata" in frontmatter:
        meta = frontmatter["metadata"]
        assert isinstance(meta, dict), "Metadata must be a dictionary"
        if "version" in meta:
            assert re.match(r"^\d+\.\d+\.\d+$", str(meta["version"])), (
                f"Invalid version: {meta['version']}"
            )


def test_investigate_skill_udm_queries_and_event_extraction() -> None:
    """Verify documentation covers UDM search queries and event extraction."""
    assert SKILL_PATH.is_file()
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    lower_body = body.lower()

    # UDM Search Queries
    assert "udm" in lower_body, "Must document UDM usage"
    assert "udm_search" in body or "search_udm" in body, (
        "Must document UDM search tools"
    )
    assert "metadata.event_type" in body, (
        "Must provide concrete UDM queries referencing metadata.event_type"
    )

    # Event Extraction
    assert any(
        evt in body
        for evt in (
            "PROCESS_LAUNCH",
            "NETWORK_CONNECTION",
            "USER_LOGIN",
            "FILE_CREATION",
        )
    ), "Must detail event extraction for key UDM event types"


def test_investigate_skill_timeline_and_lateral_movement() -> None:
    """Verify documentation covers timeline analysis and lateral movement detection."""
    assert SKILL_PATH.is_file()
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    lower_body = body.lower()

    # Asset / User Timeline Analysis
    assert "timeline" in lower_body, "Must document timeline analysis"
    assert "asset" in lower_body or "host" in lower_body, "Must reference asset/host"
    assert "user" in lower_body or "principal" in lower_body, (
        "Must reference user/principal analysis"
    )

    # Lateral Movement Detection
    assert "lateral movement" in lower_body, "Must document lateral movement detection"
    assert any(term in lower_body for term in ("psexec", "wmi", "smb", "remote")), (
        "Must document lateral movement techniques such as PsExec, WMI, SMB, or remote execution"
    )


def test_investigate_command_slash_definition() -> None:
    """Verify that commands/secops/investigate.toml defines valid slash command configuration."""
    assert COMMAND_PATH.is_file(), f"Expected command file at {COMMAND_PATH}"
    content = COMMAND_PATH.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)

    assert "prompt" in parsed, "Command TOML must contain 'prompt'"
    prompt_str = parsed["prompt"]
    assert "investigate" in prompt_str, (
        "Command prompt must reference investigate skill"
    )
    assert "{{args}}" in prompt_str, "Command prompt must accept '{{args}}' placeholder"
