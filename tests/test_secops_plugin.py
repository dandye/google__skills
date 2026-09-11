"""Automated validation tests for Google SecOps plugin manifests, skills, and harnesses.

Validates:
1. All SKILL.md files under plugins/cloud/google-secops/skills/ contain valid YAML
   frontmatter (name, description, metadata).
2. Version alignment across plugin.json, gemini-extension.json,
   .claude-plugin/plugin.json, and .codex-plugin/plugin.json.
3. All referenced commands and MCP servers exist and are properly configured.
4. Plugin discovery and validation through public CLI entry points.
"""

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from manage import app


REPO_ROOT = Path(__file__).resolve().parent.parent
SECOPS_DIR = REPO_ROOT / "plugins" / "cloud" / "google-secops"


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown content without external dependencies."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
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


def test_all_secops_skills_have_valid_frontmatter() -> None:
    """Validate that all SKILL.md files under plugins/cloud/google-secops/skills/ have valid YAML frontmatter."""
    skills_dir = SECOPS_DIR / "skills"
    assert skills_dir.is_dir(), f"Skills directory not found at {skills_dir}"

    skill_files = sorted(skills_dir.rglob("SKILL.md"))
    assert len(skill_files) >= 4, (
        f"Expected at least 4 SKILL.md files, found {len(skill_files)}"
    )

    expected_skill_dirs = {"cases", "hunt", "investigate", "triage"}
    found_dirs = {f.parent.name for f in skill_files}
    assert expected_skill_dirs.issubset(found_dirs), (
        f"Missing expected skill directories: {expected_skill_dirs - found_dirs}"
    )

    for skill_file in skill_files:
        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"{skill_file}: SKILL.md must start with YAML frontmatter '---'"
        )

        frontmatter, body = parse_frontmatter(content)

        # Validate name field
        assert "name" in frontmatter, f"{skill_file}: Missing 'name' in frontmatter"
        name = frontmatter["name"]
        assert isinstance(name, str) and name.strip(), (
            f"{skill_file}: 'name' must be a non-empty string"
        )
        assert name.startswith("secops-"), (
            f"{skill_file}: 'name' ({name}) must start with 'secops-'"
        )
        expected_suffix = skill_file.parent.name
        assert expected_suffix in name, (
            f"{skill_file}: 'name' ({name}) does not match directory ({expected_suffix})"
        )

        # Validate description field
        assert "description" in frontmatter, (
            f"{skill_file}: Missing 'description' in frontmatter"
        )
        description = frontmatter["description"]
        assert isinstance(description, str) and len(description.strip()) > 0, (
            f"{skill_file}: 'description' must be a non-empty string"
        )
        assert len(description.strip()) >= 20, (
            f"{skill_file}: 'description' is too short ({len(description.strip())} chars)"
        )

        # Validate metadata if present
        if "metadata" in frontmatter and isinstance(frontmatter["metadata"], dict):
            metadata = frontmatter["metadata"]
            if "version" in metadata:
                assert re.match(r"^\d+\.\d+\.\d+$", metadata["version"]), (
                    f"{skill_file}: Invalid semver version '{metadata['version']}' in metadata"
                )

        # Validate markdown body
        assert len(body.strip()) > 0, f"{skill_file}: Markdown body must not be empty"
        assert body.strip().startswith("#"), (
            f"{skill_file}: Markdown body should start with a top-level header"
        )


def test_manifest_version_alignment_across_harnesses() -> None:
    """Validate version alignment across plugin.json, gemini-extension.json, .claude-plugin/plugin.json, and .codex-plugin/plugin.json."""
    manifest_paths = {
        "plugin.json": SECOPS_DIR / "plugin.json",
        "gemini-extension.json": SECOPS_DIR / "gemini-extension.json",
        ".claude-plugin/plugin.json": SECOPS_DIR / ".claude-plugin" / "plugin.json",
        ".codex-plugin/plugin.json": SECOPS_DIR / ".codex-plugin" / "plugin.json",
    }

    versions: dict[str, str] = {}
    names: dict[str, str] = {}

    for manifest_name, path in manifest_paths.items():
        assert path.is_file(), f"Manifest file missing: {path}"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert "version" in data, f"{manifest_name} missing 'version' field"
        version = data["version"]
        assert isinstance(version, str) and version.strip(), (
            f"{manifest_name} has invalid 'version'"
        )
        assert re.match(r"^\d+\.\d+\.\d+$", version), (
            f"{manifest_name} version '{version}' is not valid semver"
        )
        versions[manifest_name] = version

        assert "name" in data, f"{manifest_name} missing 'name' field"
        names[manifest_name] = data["name"]

    # All versions must be identical
    unique_versions = set(versions.values())
    assert len(unique_versions) == 1, f"Version mismatch across manifests: {versions}"
    expected_version = next(iter(unique_versions))
    assert expected_version == "1.1.0"

    # All names must be identical
    unique_names = set(names.values())
    assert len(unique_names) == 1, f"Name mismatch across manifests: {names}"
    assert next(iter(unique_names)) == "google-secops"


def test_referenced_commands_exist() -> None:
    """Verify all referenced command definitions exist, are valid TOML, and map to existing skills."""
    commands_dir = SECOPS_DIR / "commands" / "secops"
    assert commands_dir.is_dir(), f"Commands directory missing at {commands_dir}"

    command_files = sorted(commands_dir.glob("*.toml"))
    assert len(command_files) >= 4, (
        f"Expected at least 4 command files in {commands_dir}, found {len(command_files)}"
    )

    expected_commands = {"cases.toml", "hunt.toml", "investigate.toml", "triage.toml"}
    found_commands = {f.name for f in command_files}
    assert expected_commands.issubset(found_commands), (
        f"Missing commands: {expected_commands - found_commands}"
    )

    skills_dir = SECOPS_DIR / "skills"

    for cmd_file in command_files:
        content = cmd_file.read_text(encoding="utf-8")
        parsed = tomllib.loads(content)

        assert "prompt" in parsed, f"{cmd_file.name} missing 'prompt' key"
        prompt = parsed["prompt"]
        assert isinstance(prompt, str) and prompt.strip(), (
            f"{cmd_file.name} prompt must be non-empty"
        )

        skill_stem = cmd_file.stem
        target_skill_dir = skills_dir / skill_stem
        assert target_skill_dir.is_dir(), (
            f"Referenced skill directory {target_skill_dir} does not exist for command {cmd_file.name}"
        )
        assert (target_skill_dir / "SKILL.md").is_file(), (
            f"SKILL.md missing in referenced skill directory {target_skill_dir}"
        )

        expected_skill_name = f"secops-{skill_stem}"
        assert expected_skill_name in prompt or skill_stem in prompt, (
            f"{cmd_file.name} prompt must reference {expected_skill_name}"
        )


def test_referenced_mcp_servers_exist() -> None:
    """Verify all referenced MCP servers and configurations exist across manifests."""
    # 1. Standard mcp.json
    mcp_path = SECOPS_DIR / "mcp.json"
    assert mcp_path.is_file(), f"Missing {mcp_path}"
    with open(mcp_path, encoding="utf-8") as f:
        mcp_data = json.load(f)
    assert "mcpServers" in mcp_data
    assert "google-security-operations" in mcp_data["mcpServers"]
    secops_mcp = mcp_data["mcpServers"]["google-security-operations"]
    assert secops_mcp.get("type") == "streamable-http"
    assert "chronicle" in secops_mcp.get("url", "")

    # 2. Claude plugin MCP reference
    claude_path = SECOPS_DIR / ".claude-plugin" / "plugin.json"
    assert claude_path.is_file(), f"Missing {claude_path}"
    with open(claude_path, encoding="utf-8") as f:
        claude_data = json.load(f)
    assert "mcpServers" in claude_data
    claude_mcp_ref = claude_data["mcpServers"].lstrip("./")
    mcp_config_path = (SECOPS_DIR / claude_mcp_ref).resolve()
    assert mcp_config_path.is_file(), (
        f"Referenced MCP config {mcp_config_path} does not exist"
    )
    with open(mcp_config_path, encoding="utf-8") as f:
        mcp_config_data = json.load(f)
    assert "mcpServers" in mcp_config_data
    assert "google-security-operations" in mcp_config_data["mcpServers"]

    # 3. Gemini extension MCP configuration
    gemini_path = SECOPS_DIR / "gemini-extension.json"
    assert gemini_path.is_file(), f"Missing {gemini_path}"
    with open(gemini_path, encoding="utf-8") as f:
        gemini_data = json.load(f)
    assert "mcpServers" in gemini_data
    assert "google-security-operations" in gemini_data["mcpServers"]

    # 4. Codex plugin skills directory reference
    codex_path = SECOPS_DIR / ".codex-plugin" / "plugin.json"
    assert codex_path.is_file(), f"Missing {codex_path}"
    with open(codex_path, encoding="utf-8") as f:
        codex_data = json.load(f)
    assert "skills" in codex_data
    codex_skills_ref = codex_data["skills"].lstrip("./")
    codex_skills_path = (SECOPS_DIR / codex_skills_ref).resolve()
    assert codex_skills_path.is_dir(), (
        f"Referenced skills directory {codex_skills_path} does not exist"
    )


def test_public_entry_point_secops_validation() -> None:
    """Exercise secops plugin validation via public CLI entry point and root discovery."""
    # 1. Exercise public CLI entry point
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "google__skills Environment Status" in result.stdout

    # 2. Public entry point discovery of plugin manifest without importing internal modules
    public_plugin_path = (
        REPO_ROOT / "plugins" / "cloud" / "google-secops" / "plugin.json"
    )
    assert public_plugin_path.is_file(), (
        f"Plugin manifest missing at {public_plugin_path}"
    )
    with open(public_plugin_path, encoding="utf-8") as f:
        plugin_manifest = json.load(f)
    assert plugin_manifest["name"] == "google-secops"
    assert plugin_manifest["version"] == "1.1.0"

    # Verify that each public skill can be located and has valid markdown documentation
    skills_root = public_plugin_path.parent / "skills"
    for skill_name in ["cases", "hunt", "investigate", "triage"]:
        skill_doc = skills_root / skill_name / "SKILL.md"
        assert skill_doc.is_file(), f"Public skill documentation missing: {skill_doc}"
        text = skill_doc.read_text(encoding="utf-8")
        assert text.startswith("---")
        assert f"secops-{skill_name}" in text


def test_secops_plugin_readme() -> None:
    """Validate that plugins/cloud/google-secops/README.md exists and covers install and testing."""
    readme_path = SECOPS_DIR / "README.md"
    assert readme_path.is_file(), f"Missing README.md at {readme_path}"

    content = readme_path.read_text(encoding="utf-8")
    assert len(content) > 200

    # Verify installation testing instructions
    assert "agy plugin install" in content
    assert "gemini extension install" in content

    # Verify authentication and prerequisites
    assert "gcloud auth application-default login" in content
    assert "chronicle.googleapis.com/mcp" in content
    assert "PROJECT_ID" in content
    assert "CUSTOMER_ID" in content

    # Verify slash commands coverage
    for cmd in [
        "/secops:triage",
        "/secops:investigate",
        "/secops:hunt",
        "/secops:cases",
        "/secops:detection-engineering",
    ]:
        assert cmd in content
