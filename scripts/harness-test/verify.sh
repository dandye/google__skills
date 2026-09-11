#!/usr/bin/env bash
#
# Cross-harness verification, run inside the clean-room container.
#
# Expects the repository mounted read-only at /repo. Antigravity is optional and
# mounted at /opt/jetski by run.sh when available.
#
# Requires no credentials: every check concerns packaging and discovery, not
# agent behaviour.
#
# Two rules learned the hard way, do not regress them:
#   1. Assert on resulting state, never on a command's output. Install prompts
#      echo the plugin name, so grepping output for it always "passes".
#   2. Every harness command runs under `timeout` with stdin closed. These CLIs
#      prompt for consent, and a prompt in a container is a hang, not an error.

set -uo pipefail

REPO=/repo
PLUGIN="$REPO/plugins/cloud/google-secops"
JETSKI=/opt/jetski/cli_internal_impl.runfiles/google3/third_party/jetski/cmd/cli/cli
CMD_TIMEOUT=120
PASS=0; FAIL=0; SKIP=0

ok()    { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS + 1)); }
bad()   { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL + 1)); }
skip()  { printf '  \033[33mSKIP\033[0m  %s\n' "$1"; SKIP=$((SKIP + 1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

run() { timeout "$CMD_TIMEOUT" "$@" </dev/null 2>&1; }

check() { # check <description> <expected-substring> <output>
  if grep -qiF -- "$2" <<< "$3"; then ok "$1"; else
    bad "$1 (expected '$2')"
    sed 's/^/          | /' <<< "$(head -8 <<< "$3")"
  fi
}

# Not under /tmp: Codex refuses to create helper binaries when codex_home is on a
# temporary filesystem, and warns on every invocation.
export HOME=/clean-home
rm -rf "$HOME"; mkdir -p "$HOME"

head_ "Clean room"
polluted=0
for stale in "$HOME/.gemini" "$HOME/.claude" "$HOME/.codex" "$HOME/.claude.json"; do
  [ -e "$stale" ] && { bad "pre-existing state: $stale"; polluted=1; }
done
[ "$polluted" -eq 0 ] && ok "HOME has no agent state before any command runs"
echo "  HOME=$HOME  user=$(id -un)"

# ------------------------------------------------------------- Antigravity
head_ "Antigravity CLI"
if [ ! -x "$JETSKI" ]; then
  skip "Antigravity not mounted (internal binary; run.sh mounts it when present)"
else
  # Not a bash function: `run` is `timeout ...`, and timeout execs a binary, so
  # it can never see a shell function.
  run_agy() { run "$JETSKI" --app_data_dir=jetski "$@"; }

  echo "  $(run_agy --version | head -1)"

  out=$(run_agy plugin validate "$PLUGIN")
  check "plugin validates" "google-secops" "$out"

  run_agy plugin install "$PLUGIN" >/dev/null
  out=$(run_agy plugin list)
  check "plugin is installed and listed" "google-secops" "$out"

  inst="$HOME/.gemini/config/plugins/google-secops"
  [ -d "$inst/skills" ]   && ok "skills/ installed"   || bad "skills/ missing from $inst"
  [ -d "$inst/agents" ]   && ok "agents/ installed"   || bad "agents/ missing"
  [ -d "$inst/commands" ] && ok "commands/ installed" || bad "commands/ missing"
  [ -f "$inst/mcp_config.json" ] \
    && ok "mcp_config.json installed (Antigravity's MCP source)" \
    || bad "mcp_config.json missing"
  printf '        --- agy plugin install ---\n'
  sed 's/^/        | /' <<< "$(run_agy plugin install "$PLUGIN")" | head -10
fi

# ------------------------------------------------------------- Claude Code
head_ "Claude Code"
out=$(run claude --version); echo "  claude $out"
out=$(run claude plugin marketplace add "$REPO")
check "marketplace registers" "google-plugins" "$out"
run claude plugin install google-secops@google-plugins -y >/dev/null
out=$(run claude plugin details google-secops)
check "Claude sees skills"      "Skills (5)"      "$out"
check "Claude sees agents"      "Agents (3)"      "$out"
check "Claude loads MCP server" "MCP servers (1)" "$out"
printf '        --- claude plugin details ---\n'
sed 's/^/        | /' <<< "$out" | head -12

# ------------------------------------------------------------------- Codex
head_ "Codex"
out=$(run codex --version); echo "  codex $out"
out=$(run codex plugin marketplace add "$REPO")
check "marketplace registers" "google" "$out"
out=$(run codex plugin list)
check "plugin is discoverable" "google-secops" "$out"

# ------------------------------------------------------- Harness neutrality
head_ "Harness neutrality of agent-facing text"
leaked=$(grep -rn -e '~/\.gemini' -e 'jetski' -e '~/\.claude' -e '\.codex' \
           "$PLUGIN/skills/" 2>/dev/null || true)
if [ -z "$leaked" ]; then
  ok "no harness-specific paths in skills/"
else
  bad "harness-specific paths leaked into agent-facing skill text"
  sed 's/^/          | /' <<< "$leaked"
fi

head_ "Result"
printf '  %d passed, %d failed, %d skipped\n\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ]
