"""Tests for Google SecOps detection engineering skill and command."""

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from manage import app


REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "cloud" / "google-secops"
SKILL_PATH = PLUGIN_DIR / "skills" / "detection-engineering" / "SKILL.md"
COMMAND_PATH = PLUGIN_DIR / "commands" / "secops" / "detection-engineering.toml"
COVERAGE_EVAL_SKILL_PATH = (
    REPO_ROOT
    / "skills"
    / "cloud"
    / "detection-engineering-coverage-evaluation"
    / "SKILL.md"
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
            key, val = key_val_match.group(1), key_val_match.group(2).strip()
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


def test_detection_engineering_skill_file_exists() -> None:
    """Verify that detection-engineering/SKILL.md exists at the expected public path."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"


def test_detection_engineering_skill_frontmatter_standards() -> None:
    """Verify that detection-engineering/SKILL.md adheres to YAML frontmatter standards."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    frontmatter, _ = _parse_frontmatter(content)

    assert "name" in frontmatter, "Frontmatter must contain 'name'"
    assert frontmatter["name"] in (
        "detection-engineering",
        "secops-detection-engineering",
    ), (
        f"Skill name '{frontmatter['name']}' must be 'detection-engineering' "
        "or 'secops-detection-engineering'"
    )

    assert "description" in frontmatter, "Frontmatter must contain 'description'"
    assert len(frontmatter["description"]) <= 1024, (
        "Description must not exceed 1024 characters"
    )
    assert len(frontmatter["description"]) >= 20, "Description must be substantive"


def test_detection_engineering_guidelines_authoring_vs_coverage_evaluation() -> None:
    """Verify clear guidelines for when to author new rules vs evaluate detection coverage gaps."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    lower_body = body.lower()

    # Clear distinction and guidelines
    assert "when to" in lower_body, "Must include guidance on when to apply workflows"
    assert "author" in lower_body and "rule" in lower_body, (
        "Must detail when to author rules"
    )
    assert "coverage" in lower_body and (
        "gap" in lower_body or "evaluation" in lower_body
    ), "Must detail when to evaluate coverage gaps"

    # Specific scenarios
    assert (
        "incident" in lower_body
        or "hunt" in lower_body
        or "known logic" in lower_body
        or "tuning" in lower_body
    ), "Must mention direct rule authoring scenarios"
    assert (
        "threat intelligence" in lower_body
        or "cti" in lower_body
        or "blog" in lower_body
        or "posture" in lower_body
    ), "Must mention coverage evaluation scenarios"


def test_detection_engineering_harmonization_with_coverage_evaluation() -> None:
    """Verify coverage evaluation harmonizes with detection-engineering-coverage-evaluation."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)

    # Core tools from existing coverage evaluation skill
    assert "generate_threat_detection_opportunity" in body
    assert "generate_synthetic_events" in body
    assert (
        "evaluate_rule_coverage_long_running" in body
        or "evaluate_rule_coverage" in body
    )
    assert "get_operation" in body
    assert "generate_rules" in body
    assert "create_rule" in body

    # Workflow alignment with coverage evaluation
    lower_body = body.lower()
    assert "prompt injection" in lower_body, (
        "Must include prompt injection safety check"
    )
    assert "synthetic" in lower_body, "Must reference synthetic event generation"
    assert "udmjson" in lower_body or "udm_json" in lower_body or "udm" in lower_body, (
        "Must specify UDM JSON formatting"
    )
    assert "tdo" in body or "threat detection opportunit" in lower_body, (
        "Must reference TDOs"
    )
    assert "user approval" in lower_body or "approve" in lower_body, (
        "Must require user approval before creating rules"
    )


def test_detection_engineering_rule_authoring_testing_deployment() -> None:
    """Verify documentation covers YARA-L rule authoring, validation, testing, and deployment."""
    assert SKILL_PATH.is_file(), f"Expected skill file at {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    lower_body = body.lower()

    # YARA-L rule authoring standards
    assert "yara-l" in lower_body, "Must document YARA-L 2.0 rule syntax"
    assert "meta:" in body or "meta" in lower_body, "Must describe rule anatomy (meta)"
    assert "events:" in body or "events" in lower_body, (
        "Must describe rule anatomy (events)"
    )
    assert "condition:" in body or "condition" in lower_body, (
        "Must describe rule anatomy (condition)"
    )

    # Validation and testing tools
    assert "validate_rule" in body, "Must document validate_rule tool"
    assert (
        "list_rule_detections" in body or "test_rule" in body or "test" in lower_body
    ), "Must document rule testing/detection validation"
    assert "create_rule" in body, "Must document create_rule tool"


def test_detection_engineering_command_slash_definition() -> None:
    """Verify commands/secops/detection-engineering.toml defines valid slash command configuration."""
    assert COMMAND_PATH.is_file(), f"Expected command file at {COMMAND_PATH}"
    content = COMMAND_PATH.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)

    assert "prompt" in parsed, "Command TOML must contain 'prompt'"
    prompt_str = parsed["prompt"]
    assert (
        "detection-engineering" in prompt_str
        or "secops-detection-engineering" in prompt_str
    ), "Command prompt must reference detection engineering skill"
    assert "{{args}}" in prompt_str, "Command prompt must accept '{{args}}' placeholder"


def test_detection_engineering_public_entry_point() -> None:
    """Exercise public entry point via CLI runner and manifest discovery without direct imports."""
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0, f"CLI runner failed: {result.stdout}"
    assert "google__skills Environment Status" in result.stdout

    # Manifest discovery via public extension definition
    extension_manifest = PLUGIN_DIR / "gemini-extension.json"
    assert extension_manifest.is_file(), (
        f"Missing extension manifest at {extension_manifest}"
    )
    with open(extension_manifest, encoding="utf-8") as f:
        ext_data = json.load(f)

    assert "skills" in ext_data, "gemini-extension.json must declare skills"
    assert "skills/detection-engineering" in ext_data["skills"], (
        "gemini-extension.json must register 'skills/detection-engineering'"
    )

    # Entry point accessibility
    assert SKILL_PATH.is_file(), f"Skill entry point file not found at {SKILL_PATH}"
    assert COMMAND_PATH.is_file(), (
        f"Command entry point file not found at {COMMAND_PATH}"
    )
