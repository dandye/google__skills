"""Tests for registration of Google SecOps plugin and skills in index.json and README.md."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from manage import app


REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_JSON_PATH = REPO_ROOT / "index.json"
README_PATH = REPO_ROOT / "README.md"
PLUGIN_DIR = REPO_ROOT / "plugins" / "cloud" / "google-secops"

EXPECTED_SECOPS_SKILLS = [
    "cases",
    "detection-engineering",
    "hunt",
    "investigate",
    "triage",
]


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    assert match is not None, "File missing valid '---' YAML frontmatter delimiters"

    raw_yaml = match.group(1)
    body = match.group(2)

    data: dict[str, Any] = {}
    current_key: str | None = None
    sub_dict: dict[str, Any] | None = None
    multiline_buf: list[str] = []

    for line in raw_yaml.splitlines():
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
                data[key] = val.strip("\"'")
        elif current_key and line.startswith("  "):
            multiline_buf.append(line_strip)

    if current_key and multiline_buf:
        data[current_key] = " ".join(multiline_buf).strip()
    if current_key and sub_dict is not None:
        data[current_key] = sub_dict

    return data, body


def test_index_json_syntax_and_structure() -> None:
    """Verify index.json is valid JSON with expected top-level schema and sorted skills."""
    assert INDEX_JSON_PATH.is_file(), f"Missing index.json at {INDEX_JSON_PATH}"

    content = INDEX_JSON_PATH.read_text(encoding="utf-8")
    data = json.loads(content)

    assert "skills" in data, "index.json missing 'skills' key"
    assert isinstance(data["skills"], list), "'skills' must be a list"

    required_keys = {"name", "description", "entrypoint"}
    skill_names: list[str] = []

    for item in data["skills"]:
        assert isinstance(item, dict), f"Skill entry must be a dict: {item}"
        assert required_keys.issubset(item.keys()), (
            f"Skill entry {item.get('name')} missing keys: {required_keys - set(item.keys())}"
        )
        assert item["name"].strip(), "Skill 'name' cannot be empty"
        assert item["description"].strip(), (
            f"Skill '{item['name']}' has empty description"
        )
        assert item["entrypoint"].startswith(
            "https://raw.githubusercontent.com/google/skills/main/"
        ), f"Skill '{item['name']}' has invalid entrypoint URL: {item['entrypoint']}"
        skill_names.append(item["name"])

    # Verify skills are sorted alphabetically by name
    assert skill_names == sorted(skill_names), (
        "Skills in index.json must be sorted alphabetically by name"
    )


def test_secops_skills_registered_in_index_json() -> None:
    """Verify that all 5 SecOps skills (cases, hunt, investigate, triage, detection-engineering) are in index.json."""
    assert INDEX_JSON_PATH.is_file()
    content = INDEX_JSON_PATH.read_text(encoding="utf-8")
    data = json.loads(content)

    indexed_by_name = {s["name"]: s for s in data["skills"]}

    for skill_dir in EXPECTED_SECOPS_SKILLS:
        skill_file = PLUGIN_DIR / "skills" / skill_dir / "SKILL.md"
        assert skill_file.is_file(), f"SecOps skill file missing at {skill_file}"

        frontmatter, _ = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        canonical_name = frontmatter.get("name", f"secops-{skill_dir}")

        assert canonical_name in indexed_by_name, (
            f"Skill '{canonical_name}' (from {skill_dir}) is not registered in index.json"
        )

        entry = indexed_by_name[canonical_name]
        expected_entrypoint = (
            f"https://raw.githubusercontent.com/google/skills/main/plugins/cloud/"
            f"google-secops/skills/{skill_dir}/SKILL.md"
        )
        assert entry["entrypoint"] == expected_entrypoint, (
            f"Skill '{canonical_name}' has wrong entrypoint. Expected {expected_entrypoint}, "
            f"got {entry['entrypoint']}"
        )
        assert entry["description"] == frontmatter["description"], (
            f"Skill '{canonical_name}' description in index.json does not match SKILL.md frontmatter"
        )


def test_readme_plugins_table_lists_google_secops() -> None:
    """Verify README.md lists the google-secops plugin under the Plugins section and catalog."""
    assert README_PATH.is_file(), f"Missing README.md at {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    # Check for Plugins section and google-secops in plugins table
    assert "## Plugins" in readme_content, "README.md missing '## Plugins' section"

    plugins_section = re.split(r"\n## [^#]", readme_content.split("## Plugins")[1])[0]
    assert "google-secops" in plugins_section, (
        "README.md Plugins section must mention 'google-secops'"
    )
    assert "plugins/cloud/google-secops" in plugins_section, (
        "README.md Plugins table must link to 'plugins/cloud/google-secops'"
    )

    # Verify SecOps skills are also in the Available Skills catalog
    for skill_dir in EXPECTED_SECOPS_SKILLS:
        assert f"plugins/cloud/google-secops/skills/{skill_dir}" in readme_content, (
            f"README.md Available Skills must list SecOps skill '{skill_dir}'"
        )


def test_public_entry_point_and_jq_validation() -> None:
    """Exercise public entry point via CLI runner and validate index.json syntax with jq."""
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0, f"CLI runner failed: {result.stdout}"
    assert "google__skills Environment Status" in result.stdout

    # Validate index.json structure using jq if available
    jq_bin = shutil.which("jq")
    if jq_bin:
        proc = subprocess.run(  # noqa: S603
            [jq_bin, ".", str(INDEX_JSON_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (
            f"jq validation failed for index.json: {proc.stderr}"
        )
