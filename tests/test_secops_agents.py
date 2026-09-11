"""Automated validation tests for SecOps specialized agents, manifests, and documentation.

Validates:
1. Agent definition files under plugins/cloud/google-secops/agents/ exist and contain valid YAML frontmatter.
2. Agent frontmatter fields: name, description, kind, tools.
3. Agent system prompt coverage: UDM, YARA-L 2.0, Chronicle MCP actions, case management.
4. Manifest declarations in gemini-extension.json for commands and agents.
5. Documentation of agents and namespaced slash commands in plugins/cloud/google-secops/README.md.
6. Zero emojis rule enforcement across all agent definitions.
"""

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SECOPS_DIR = REPO_ROOT / "plugins" / "cloud" / "google-secops"
AGENTS_DIR = SECOPS_DIR / "agents"


def parse_agent_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from agent markdown content without external dependencies."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    assert match is not None, (
        "Agent file missing valid '---' YAML frontmatter delimiters"
    )

    raw_yaml = match.group(1)
    body = match.group(2)

    data: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
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

        # Handle list items
        if line_strip.startswith("- ") and current_key and current_list is not None:
            current_list.append(line_strip[2:].strip("\"'"))
            continue

        if current_key and current_list is not None:
            data[current_key] = current_list
            current_list = None
            current_key = None

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
                    current_list = []
                else:
                    data[k] = v
                    current_key = None

    if multiline_key is not None:
        data[multiline_key] = " ".join(multiline_lines)

    if current_key and current_list is not None:
        data[current_key] = current_list

    if current_key and sub_dict is not None:
        data[current_key] = sub_dict

    return data, body


def test_secops_agents_exist() -> None:
    """Validate that plugins/cloud/google-secops/agents/ contains all 3 specialized agent files."""
    assert AGENTS_DIR.is_dir(), f"Agents directory missing at {AGENTS_DIR}"

    expected_agents = {
        "secops-triage-analyst.md",
        "secops-investigator.md",
        "secops-detection-engineer.md",
    }
    found_agents = {f.name for f in AGENTS_DIR.glob("*.md")}
    assert expected_agents.issubset(found_agents), (
        f"Missing expected agents: {expected_agents - found_agents}"
    )


def test_secops_agents_frontmatter_validity() -> None:
    """Validate YAML frontmatter fields for all SecOps agent definition files."""
    assert AGENTS_DIR.is_dir(), f"Agents directory missing at {AGENTS_DIR}"

    agent_files = sorted(AGENTS_DIR.glob("*.md"))
    assert len(agent_files) >= 3, (
        f"Expected at least 3 agent files, found {len(agent_files)}"
    )

    for agent_file in agent_files:
        content = agent_file.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"{agent_file.name}: Must start with YAML frontmatter"
        )

        # Check for emojis
        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]",
            re.UNICODE,
        )
        assert not emoji_pattern.search(content), (
            f"{agent_file.name}: Must not contain emojis"
        )

        frontmatter, body = parse_agent_frontmatter(content)

        # Validate name
        assert "name" in frontmatter, (
            f"{agent_file.name}: Missing 'name' in frontmatter"
        )
        assert frontmatter["name"] == agent_file.stem, (
            f"{agent_file.name}: 'name' ({frontmatter['name']}) must match stem ({agent_file.stem})"
        )

        # Validate description
        assert "description" in frontmatter, f"{agent_file.name}: Missing 'description'"
        desc = frontmatter["description"]
        assert isinstance(desc, str) and len(desc.strip()) >= 30, (
            f"{agent_file.name}: Description too short"
        )

        # Validate kind
        assert frontmatter.get("kind") == "local", (
            f"{agent_file.name}: 'kind' must be 'local'"
        )

        # Validate tools
        assert "tools" in frontmatter, f"{agent_file.name}: Missing 'tools'"
        assert (
            isinstance(frontmatter["tools"], list) and len(frontmatter["tools"]) > 0
        ), f"{agent_file.name}: 'tools' must be a non-empty list"

        # Validate body
        assert len(body.strip()) > 100, (
            f"{agent_file.name}: Agent system prompt body too short"
        )
        assert body.strip().startswith("#"), (
            f"{agent_file.name}: Body must start with header"
        )


def test_secops_agents_system_prompts_domain_coverage() -> None:
    """Validate specialized domain content for each agent's system prompt."""
    triage_file = AGENTS_DIR / "secops-triage-analyst.md"
    assert triage_file.is_file()
    triage_text = triage_file.read_text(encoding="utf-8")
    assert "triage" in triage_text.lower()
    assert "risk" in triage_text.lower()
    assert "severity" in triage_text.lower()
    assert "escalat" in triage_text.lower()

    investigator_file = AGENTS_DIR / "secops-investigator.md"
    assert investigator_file.is_file()
    inv_text = investigator_file.read_text(encoding="utf-8")
    assert "investigat" in inv_text.lower()
    assert "pivot" in inv_text.lower() or "graph" in inv_text.lower()
    assert "udm" in inv_text.lower()
    assert "timeline" in inv_text.lower()

    detection_file = AGENTS_DIR / "secops-detection-engineer.md"
    assert detection_file.is_file()
    det_text = detection_file.read_text(encoding="utf-8")
    assert "yara-l" in det_text.lower() or "yara_l" in det_text.lower()
    assert "rule" in det_text.lower()
    assert "test" in det_text.lower() or "retro" in det_text.lower()


def test_gemini_extension_declares_commands_and_agents() -> None:
    """Validate that gemini-extension.json explicitly declares commands and agents."""
    manifest_path = SECOPS_DIR / "gemini-extension.json"
    assert manifest_path.is_file()

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    # Validate commands declaration
    assert "commands" in data, "gemini-extension.json must declare 'commands' array"
    commands = data["commands"]
    assert isinstance(commands, list)
    expected_commands = [
        "commands/secops/cases.toml",
        "commands/secops/detection-engineering.toml",
        "commands/secops/hunt.toml",
        "commands/secops/investigate.toml",
        "commands/secops/triage.toml",
    ]
    for cmd in expected_commands:
        assert cmd in commands, f"Missing command '{cmd}' in gemini-extension.json"

    # Validate agents declaration
    assert "agents" in data, "gemini-extension.json must declare 'agents' array"
    agents = data["agents"]
    assert isinstance(agents, list)
    expected_agents = [
        "agents/secops-triage-analyst.md",
        "agents/secops-investigator.md",
        "agents/secops-detection-engineer.md",
    ]
    for agent in expected_agents:
        assert agent in agents, f"Missing agent '{agent}' in gemini-extension.json"


def test_secops_plugin_readme_documents_agents() -> None:
    """Validate that README.md documents the specialized agents and namespaced slash commands."""
    readme_path = SECOPS_DIR / "README.md"
    assert readme_path.is_file()

    content = readme_path.read_text(encoding="utf-8")

    # Document all three agents
    for agent_name in [
        "secops-triage-analyst",
        "secops-investigator",
        "secops-detection-engineer",
    ]:
        assert agent_name in content, (
            f"README.md missing documentation for agent '{agent_name}'"
        )

    # Document slash command colon namespacing
    assert "/secops:triage" in content
    assert "/secops:investigate" in content
    assert "/secops:hunt" in content
    assert "/secops:cases" in content
    assert "/secops:detection-engineering" in content
