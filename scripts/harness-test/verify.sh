#!/usr/bin/env bash
#
# Cross-harness verification, run inside the clean-room container.
#
# Expects the repository mounted read-only at /repo. Requires no credentials:
# every check is about discovery and packaging, not agent behaviour.
#
# Every harness command runs under `timeout` with stdin closed. These CLIs
# prompt interactively when they want consent or configuration, and a prompt in
# a non-interactive container is an infinite hang, not an error.

set -uo pipefail

REPO=/repo
PLUGIN="$REPO/plugins/cloud/google-secops"
CMD_TIMEOUT=90
PASS=0
FAIL=0

ok()    { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS + 1)); }
bad()   { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL + 1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

run() { timeout "$CMD_TIMEOUT" "$@" </dev/null 2>&1; }

check() { # check <description> <expected-substring> <output>
  if grep -qiF -- "$2" <<< "$3"; then
    ok "$1"
  else
    bad "$1 (expected '$2')"
    sed 's/^/          | /' <<< "$(head -8 <<< "$3")"
  fi
}

# Pollution check must precede every CLI call: merely running `--version`
# creates the config directory.
head_ "Clean room"
polluted=0
for stale in "$HOME/.gemini" "$HOME/.claude" "$HOME/.codex" "$HOME/.claude.json"; do
  if [ -e "$stale" ]; then bad "pre-existing state: $stale"; polluted=1; fi
done
[ "$polluted" -eq 0 ] && ok "HOME contains no agent state before any command runs"
echo "  HOME=$HOME  user=$(id -un)"

head_ "Harness versions"
echo "  gemini $(run gemini --version | head -1)"
echo "  claude $(run claude --version | head -1)"
echo "  codex  $(run codex --version  | head -1)"

# ---------------------------------------------------------------- Gemini CLI
head_ "Gemini CLI: install extension from a local path"
# --consent covers the extension-install warning but NOT the folder-trust
# prompt, which defaults to "no" on closed stdin and makes install a silent
# no-op that still exits 0. Answer it explicitly.
printf 'y\n' | timeout "$CMD_TIMEOUT" gemini extension install \
  "$PLUGIN" --consent --skip-settings >/dev/null 2>&1
out=$(run gemini extension list)
check "extension is installed and listed" "google-secops" "$out"
[ -d "$HOME/.gemini/extensions/google-secops/skills" ] \
  && ok "skills/ present in the installed extension" \
  || bad "skills/ missing from the installed extension"

# ---------------------------------------------------------------- Claude Code
head_ "Claude Code: install from the repo marketplace"
out=$(run claude plugin marketplace add "$REPO")
check "marketplace registers" "google-plugins" "$out"
out=$(run claude plugin install google-secops@google-plugins -y)
check "plugin installs" "google-secops" "$out"
out=$(run claude plugin details google-secops)
check "Claude sees skills"      "Skills (5)"     "$out"
check "Claude sees agents"      "Agents (3)"     "$out"
check "Claude loads MCP server" "MCP servers (1)" "$out"
printf '        --- claude plugin details ---\n'
sed 's/^/        | /' <<< "$out" | head -30

# ---------------------------------------------------------------- Codex
head_ "Codex: install from the repo marketplace"
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
printf '  %d passed, %d failed\n\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
