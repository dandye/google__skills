# Cross-harness clean-room test

Verifies the plugin installs and is discovered by **Gemini CLI**, **Claude Code**
and **Codex**, in a container with an empty `HOME` and no credentials.

```bash
scripts/harness-test/run.sh          # podman (default)
ENGINE=docker scripts/harness-test/run.sh
```

## Why this exists

The plugin was developed and tested only under Antigravity. Three defects
reached the repository as a direct result, none of which any unit test or
Antigravity run could detect:

| Defect | Effect |
| :--- | :--- |
| `~/.gemini/jetski/mcp/` in the skill's stop message | Agent printed a nonexistent path to Claude, Codex and Gemini users |
| `google-secops` absent from both marketplace manifests | Plugin was uninstallable on Claude Code and Codex |
| `"mcpServers": "./mcp_config.json"` in `.claude-plugin/plugin.json` | Silently ignored by Claude; users got zero SecOps tools |

The last one is worth remembering: the string path *resolves to a real file*, so
a unit test asserting the file exists passed while the feature was broken. Only
asking Claude what it loaded revealed it.

## What it checks

No credentials are needed because every check is about packaging and discovery,
not agent behaviour.

- `HOME` is genuinely empty before any command runs.
- Gemini CLI installs the extension from a local path and lists it.
- Claude Code adds the repo marketplace, installs the plugin, and reports the
  expected inventory: 5 skills, 3 agents, 1 MCP server.
- Codex adds the repo marketplace and discovers the plugin.
- No harness-specific filesystem path appears in agent-facing skill text.

## Gotchas

- `gemini extension install --consent` does **not** cover the separate
  folder-trust prompt. On closed stdin that prompt defaults to no, and install
  becomes a silent no-op that still exits 0. Answer it explicitly.
- Assert on state after the command, never on the command's output. The install
  prompt echoes the plugin name, so grepping the output for it always passes.
- CLI versions are pinned in the `Dockerfile`. Bump them deliberately.
