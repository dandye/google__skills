# Clean-room harness for verifying the plugin outside any one agent runtime.
#
# The plugin ships to Claude Code, Gemini CLI, Codex and Antigravity. Testing it
# only under Antigravity let a Jetski-specific path reach agent-facing text (see
# commit 32e0137). This image has no ~/.gemini, no installed plugins, no direnv
# and no credentials, so anything that passes here passes for a new user.
FROM docker.io/library/node:22-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl jq python3 \
 && rm -rf /var/lib/apt/lists/*

# Pinned so a broken upstream release is visible as a version bump, not a
# mysterious test failure. Bump deliberately.
ARG GEMINI_CLI_VERSION=0.59.0
ARG CLAUDE_CODE_VERSION=2.1.269
ARG CODEX_VERSION=0.154.0

RUN npm install -g \
      "@google/gemini-cli@${GEMINI_CLI_VERSION}" \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
      "@openai/codex@${CODEX_VERSION}" \
 && npm cache clean --force

# Unprivileged, with its own empty HOME. Nothing is inherited from the host.
RUN useradd --create-home --shell /bin/bash tester
USER tester
WORKDIR /home/tester

COPY --chown=tester:tester verify.sh /usr/local/bin/verify.sh
ENTRYPOINT ["/bin/bash", "/usr/local/bin/verify.sh"]
