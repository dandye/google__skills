"""Tests for Google SecOps plugin manifests and environment rules."""

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from manage import app


REPO_ROOT = Path(__file__).resolve().parent.parent
SECOPS_DIR = REPO_ROOT / "plugins" / "cloud" / "google-secops"


def test_secops_plugin_json_schema() -> None:
    """Validate plugin.json against Agent Plugins 1.0.0 specification."""
    plugin_path = SECOPS_DIR / "plugin.json"
    assert plugin_path.exists(), f"Missing {plugin_path}"

    with open(plugin_path, encoding="utf-8") as f:
        data = json.load(f)

    assert (
        data.get("$schema")
        == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    )
    assert data.get("name") == "google-secops"
    assert data.get("version") == "1.1.0"
    assert isinstance(data.get("description"), str) and len(data["description"]) > 0
    assert data.get("license") == "Apache-2.0"

    author = data.get("author")
    assert isinstance(author, dict)
    assert author.get("name") == "Google LLC"

    assert "homepage" in data
    assert "repository" in data
    keywords = data.get("keywords")
    assert isinstance(keywords, list)
    assert "google-secops" in keywords

    # Validate against allowed top-level keys in Agent Plugins 1.0.0
    allowed_keys = {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "extensions",
    }
    assert set(data.keys()).issubset(allowed_keys)


def test_secops_mcp_json_schema() -> None:
    """Validate mcp.json defines remote MCP server with streamable-http."""
    mcp_path = SECOPS_DIR / "mcp.json"
    assert mcp_path.exists(), f"Missing {mcp_path}"

    with open(mcp_path, encoding="utf-8") as f:
        data = json.load(f)

    assert (
        data.get("$schema") == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    )
    servers = data.get("mcpServers")
    assert isinstance(servers, dict)
    assert "google-security-operations" in servers

    secops_server = servers["google-security-operations"]
    assert secops_server.get("type") == "streamable-http"
    assert secops_server.get("url") == "https://chronicle.us.rep.googleapis.com/mcp"

    allowed_keys = {"$schema", "mcpServers"}
    assert set(data.keys()).issubset(allowed_keys)


def test_secops_harness_descriptors() -> None:
    """Validate Gemini, Claude, and Codex plugin descriptors and MCP configs."""
    # 1. Gemini extension
    gemini_path = SECOPS_DIR / "gemini-extension.json"
    assert gemini_path.exists(), f"Missing {gemini_path}"
    with open(gemini_path, encoding="utf-8") as f:
        gemini_data = json.load(f)
    assert gemini_data.get("name") == "google-secops"
    assert gemini_data.get("version") == "1.1.0"
    setting_names = {s["name"] for s in gemini_data.get("settings", [])}
    assert {"PROJECT_ID", "CUSTOMER_ID", "REGION", "SERVER_URL"}.issubset(setting_names)
    assert "google-security-operations" in gemini_data.get("mcpServers", {})

    # 2. Claude plugin & mcp_config.json
    claude_path = SECOPS_DIR / ".claude-plugin" / "plugin.json"
    assert claude_path.exists(), f"Missing {claude_path}"
    with open(claude_path, encoding="utf-8") as f:
        claude_data = json.load(f)
    assert claude_data.get("name") == "google-secops"
    assert claude_data.get("version") == "1.1.0"
    assert claude_data.get("mcpServers") == "./mcp_config.json"

    mcp_config_path = SECOPS_DIR / "mcp_config.json"
    assert mcp_config_path.exists(), f"Missing {mcp_config_path}"
    with open(mcp_config_path, encoding="utf-8") as f:
        mcp_config_data = json.load(f)
    assert "google-security-operations" in mcp_config_data.get("mcpServers", {})

    # 3. Codex plugin
    codex_path = SECOPS_DIR / ".codex-plugin" / "plugin.json"
    assert codex_path.exists(), f"Missing {codex_path}"
    with open(codex_path, encoding="utf-8") as f:
        codex_data = json.load(f)
    assert codex_data.get("name") == "google-secops"
    assert codex_data.get("version") == "1.1.0"
    assert codex_data.get("skills") == "./skills/"


def test_secops_environment_rules() -> None:
    """Validate secops-environment.md documents authentication and required variables."""
    rules_path = SECOPS_DIR / "rules" / "secops-environment.md"
    assert rules_path.exists(), f"Missing {rules_path}"

    content = rules_path.read_text(encoding="utf-8")
    # Validate YAML frontmatter
    assert content.startswith("---")
    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    assert frontmatter_match is not None, "Missing YAML frontmatter"
    frontmatter = frontmatter_match.group(1)
    assert "name: secops-environment" in frontmatter
    assert "description:" in frontmatter

    # Validate authentication documentation
    assert "gcloud auth application-default login" in content
    assert (
        "mcp enable chronicle" in content or "chronicle.googleapis.com/mcp" in content
    )

    # Validate required environment variables
    assert "PROJECT_ID" in content
    assert "CUSTOMER_ID" in content
    assert "REGION" in content
    assert "SERVER_URL" in content


def test_secops_public_entry_point() -> None:
    """Exercise plugin public entry point via CLI execution and discovery."""
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "google__skills Environment Status" in result.stdout

    # Verify that the public entry point plugin manifest is readable from the repository root
    manifest_file = REPO_ROOT / "plugins" / "cloud" / "google-secops" / "plugin.json"
    assert manifest_file.exists()
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["name"] == "google-secops"
    assert manifest["version"] == "1.1.0"
