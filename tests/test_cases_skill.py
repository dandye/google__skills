"""Tests for Google SecOps Case Management skill and command."""

import re
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_SKILL_PATH = (
    REPO_ROOT / "plugins" / "cloud" / "google-secops" / "skills" / "cases" / "SKILL.md"
)
CASES_COMMAND_PATH = (
    REPO_ROOT
    / "plugins"
    / "cloud"
    / "google-secops"
    / "commands"
    / "secops"
    / "cases.toml"
)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    assert match is not None, "File missing valid '---' YAML frontmatter delimiters"

    raw_yaml = match.group(1)
    body = match.group(2)

    data: dict[str, Any] = {}
    current_key: str | None = None
    sub_dict: dict[str, Any] | None = None
    multiline_key: str | None = None
    multiline_lines: list[str] = []

    for line in raw_yaml.splitlines():
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#"):
            continue

        if multiline_key is not None:
            if line.startswith("  "):
                multiline_lines.append(line_strip)
                continue
            else:
                data[multiline_key] = " ".join(multiline_lines)
                multiline_key = None
                multiline_lines = []

        if line.startswith("  ") and current_key and sub_dict is not None:
            sub_match = re.match(r"^(\w+):\s*(.*)$", line_strip)
            if sub_match:
                k, v = sub_match.group(1), sub_match.group(2).strip("\"'")
                sub_dict[k] = v
        else:
            if current_key and sub_dict is not None:
                data[current_key] = sub_dict
                sub_dict = None

            key_match = re.match(r"^([\w-]+):\s*(.*)$", line_strip)
            if key_match:
                k, v = key_match.group(1), key_match.group(2).strip("\"'")
                if v in (">-", ">", "|", "|-"):
                    multiline_key = k
                    multiline_lines = []
                    current_key = None
                elif not v:
                    current_key = k
                    sub_dict = {}
                else:
                    data[k] = v
                    current_key = None

    if multiline_key is not None:
        data[multiline_key] = " ".join(multiline_lines)

    if current_key and sub_dict is not None:
        data[current_key] = sub_dict

    return data, body


def test_cases_skill_file_exists() -> None:
    """Verify that cases/SKILL.md exists at the expected public path."""
    assert CASES_SKILL_PATH.is_file(), (
        f"Expected SKILL.md at {CASES_SKILL_PATH} does not exist"
    )


def test_cases_skill_frontmatter_valid() -> None:
    """Verify that cases/SKILL.md has valid YAML frontmatter conforming to spec."""
    content = CASES_SKILL_PATH.read_text(encoding="utf-8")
    data, _ = parse_frontmatter(content)

    assert "name" in data, "Missing 'name' in frontmatter"
    assert data["name"] in (
        "cases",
        "secops-cases",
    ), f"Invalid skill name: {data['name']}"
    assert len(data["name"]) <= 64, "Skill name exceeds 64 characters"

    assert "description" in data, "Missing 'description' in frontmatter"
    assert len(data["description"]) > 10, "Skill description is too short"
    assert len(data["description"]) <= 1024, "Skill description exceeds 1024 characters"

    if "metadata" in data:
        metadata = data["metadata"]
        assert isinstance(metadata, dict), "'metadata' should be a dictionary"
        if "version" in metadata:
            assert re.match(r"^\d+\.\d+\.\d+$", str(metadata["version"])), (
                f"Invalid version format: {metadata['version']}"
            )


def test_cases_skill_content_coverage() -> None:
    """Verify SKILL.md covers case listing, creation, updates, comments, and alert linking."""
    content = CASES_SKILL_PATH.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)
    body_lower = body.lower()

    # Case Listing
    assert "list_cases" in body or "list cases" in body_lower, (
        "SKILL.md must cover case listing"
    )

    # Case Creation
    assert "create_case" in body or "create case" in body_lower, (
        "SKILL.md must cover case creation"
    )

    # Status / Priority Updates
    assert any(
        kw in body for kw in ["update_case", "change_case_priority", "close_case"]
    ) or any(
        kw in body_lower for kw in ["priority update", "status update", "case priority"]
    ), "SKILL.md must cover status and priority updates"

    # Comment Addition
    assert (
        "create_case_comment" in body
        or "post_case_comment" in body
        or "case comment" in body_lower
    ), "SKILL.md must cover adding case comments"

    # Alert Linking
    assert (
        "list_case_alerts" in body
        or "list_alerts_by_case" in body
        or "alert" in body_lower
    ), "SKILL.md must cover alert linking or associating alerts with cases"


def test_cases_command_defined() -> None:
    """Verify commands/secops/cases.toml exists and defines a valid slash command."""
    assert CASES_COMMAND_PATH.is_file(), (
        f"Expected command file at {CASES_COMMAND_PATH} does not exist"
    )

    content = CASES_COMMAND_PATH.read_text(encoding="utf-8")
    data = tomllib.loads(content)

    assert "prompt" in data, "cases.toml must define 'prompt'"
    assert "secops-cases" in data["prompt"] or "cases" in data["prompt"], (
        "Command prompt must reference the cases skill"
    )


def test_cases_skill_declares_tool_availability_preconditions() -> None:
    """Verify SKILL.md instructs the agent to stop when no case tool is registered."""
    content = CASES_SKILL_PATH.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)

    assert "Tool Availability Preconditions" in body, (
        "SKILL.md must declare a 'Tool Availability Preconditions' section"
    )
    assert "STOP" in body, (
        "SKILL.md must instruct the agent to STOP when no case tool is registered"
    )
    assert "configuration failure to report" in body, (
        "SKILL.md must frame a missing tool as a configuration failure, not an obstacle"
    )


def test_cases_skill_forbids_credential_and_iam_workarounds() -> None:
    """Verify SKILL.md prohibits the improvised workarounds seen in incident triage.

    With no registered tool, an agent previously harvested service account keys,
    minted access tokens, probed unrelated tenants, and attempted to grant itself
    an IAM role. Each of those routes must be explicitly closed.
    """
    content = CASES_SKILL_PATH.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)

    assert "MUST NOT" in body, "SKILL.md must contain an explicit prohibition list"

    prohibitions = {
        "raw HTTP or JSON-RPC": "constructing raw Chronicle API calls",
        "print-access-token": "minting credentials via gcloud",
        "~/.ssh": "enumerating credential material",
        "IAM modification": "self-granting IAM roles",
        "Substitute a different project": "switching to another tenant",
    }
    for needle, description in prohibitions.items():
        assert needle in body, f"SKILL.md must prohibit {description}"


def test_cases_skill_has_no_permissive_fallback_clause() -> None:
    """Verify the unreachable-server fallback clause has not been reintroduced."""
    content = CASES_SKILL_PATH.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)

    assert "Fall back to local Python MCP server tools" not in body, (
        "The permissive fallback clause licenses workarounds and must not return"
    )
    assert "not registered or reachable" not in body, (
        "Unreachability must be a stop condition, not a trigger for an alternate path"
    )


def test_cases_skill_does_not_advertise_remote_create_case() -> None:
    """Verify the capability matrix does not claim a remote create_case tool.

    The remote Chronicle MCP server exposes 71 tools and create_case is not one
    of them. Advertising it invites the agent to improvise a substitute.
    """
    content = CASES_SKILL_PATH.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)

    matrix_rows = [
        line for line in body.splitlines() if line.startswith("| **Create Case**")
    ]
    assert len(matrix_rows) == 1, "Expected exactly one 'Create Case' capability row"

    remote_cell = matrix_rows[0].split("|")[2].strip()
    assert remote_cell == "Not available", (
        f"Remote create_case does not exist; matrix claims {remote_cell!r}"
    )
