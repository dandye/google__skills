# Clean-room harness for verifying the plugin outside a developer's own machine.
#
# The plugin ships to Antigravity, Claude Code and Codex. Testing it only under
# a contaminated Antigravity install let three defects reach the repo: a
# Jetski-specific path in agent-facing text, absence from both marketplace
# manifests, and an MCP declaration Claude silently ignores. See README.md.
#
# Claude Code and Codex are installed from public npm. Antigravity is a Google
# internal binary and cannot be baked in; run.sh mounts it when present, and
# the Antigravity checks skip cleanly when it is not.
FROM docker.io/library/node:22-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl jq python3 \
 && rm -rf /var/lib/apt/lists/*

# Pinned so an upstream regression shows up as a deliberate version bump rather
# than a mysterious failure.
ARG CLAUDE_CODE_VERSION=2.1.269
ARG CODEX_VERSION=0.154.0

RUN npm install -g \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
      "@openai/codex@${CODEX_VERSION}" \
 && npm cache clean --force

# Runs as root: rootless podman maps the invoking user to container root, which
# is required to read the mounted Antigravity binary. HOME is set per-run by
# verify.sh to a fresh empty directory, so nothing is inherited regardless.
WORKDIR /work
COPY verify.sh /usr/local/bin/verify.sh
ENTRYPOINT ["/bin/bash", "/usr/local/bin/verify.sh"]
