# Cross-harness clean-room test

Verifies the plugin installs and is discovered by **Antigravity**, **Claude Code**
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
| `~/.gemini/jetski/mcp/` in the skill's stop message | Agent printed a nonexistent path to Claude and Codex users |
| `google-secops` absent from both marketplace manifests | Plugin was uninstallable on Claude Code and Codex |
| `"mcpServers": "./mcp_config.json"` in `.claude-plugin/plugin.json` | Silently ignored by Claude; users got zero SecOps tools |

The last one is worth remembering: the string path *resolves to a real file*, so
a unit test asserting the file exists passed while the feature was broken. Only
asking Claude what it loaded revealed it.

## What it checks

No credentials are needed because every check is about packaging and discovery,
not agent behaviour.

- `HOME` is genuinely empty before any command runs.
- Antigravity validates the plugin, installs it from a local path, lists it, and
  lands `skills/`, `agents/`, `commands/` and `mcp_config.json` on disk.
- Claude Code adds the repo marketplace, installs the plugin, and reports the
  expected inventory: 5 skills, 3 agents, 1 MCP server.
- Codex adds the repo marketplace and discovers the plugin.
- No harness-specific filesystem path appears in agent-facing skill text.

## Antigravity in a container

Antigravity is internal and cannot be baked into the image, so `run.sh` mounts
the copy already on the host. Three requirements follow from that, and each one
fails confusingly if missed:

- `/google/bin/releases/jetski-devs/tools/cli` is a launcher, not the binary.
  `run.sh` extracts the real one with `SAR_EXTRACT_ONLY=1` and mounts the
  resulting `/tmp/sar.cli_internal.*` directory at `/opt/jetski`.
- The extracted binary is dynamically linked against GRTE, so `/usr/grte` is
  mounted too.
- The extract directory is mode `dr-xr-x---` owned by the invoking user, and
  rootless podman maps that user to container root. The container therefore runs
  `--user root`; as any other user the mount is unreadable.

When Antigravity is absent the checks **skip** rather than fail, so the harness
still runs on a machine without corp access, and in CI.

## Gotchas

- `timeout` execs a binary and cannot see a shell function. Wrapping the CLI in
  an `agy()` function and calling it through the `run` helper fails with
  `timeout: failed to run command 'agy'`.
- Assert on state after the command, never on the command's output. The install
  prompt echoes the plugin name, so grepping the output for it always passes.
- Keep `HOME` off `/tmp`: Codex refuses to create helper binaries when its home
  is on a temporary filesystem.
- CLI versions are pinned in the `Dockerfile`. Bump them deliberately.
