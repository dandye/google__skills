#!/usr/bin/env bash
#
# Build and run the cross-harness clean-room verification.
#
#   scripts/harness-test/run.sh          # or: just harness-test
#   ENGINE=docker scripts/harness-test/run.sh
#
# Claude Code and Codex come from public npm and are baked into the image.
#
# Antigravity is a Google internal binary that cannot be baked in. It is a
# self-extracting archive linked against Google's GRTE runtime, so when it is
# available this script extracts it and mounts both the extracted tree and
# /usr/grte. When it is absent -- on a non-corp machine or in CI -- the
# Antigravity checks skip and the rest still runs.
#
# Requires no credentials and touches nothing in your home directory.

set -euo pipefail

ENGINE="${ENGINE:-podman}"
IMAGE="${IMAGE:-secops-harness:latest}"
JETSKI_SAR="${JETSKI_SAR:-/google/bin/releases/jetski-devs/tools/internal/cli_internal}"
GRTE="${GRTE:-/usr/grte}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

command -v "$ENGINE" >/dev/null || {
  echo "ERROR: $ENGINE not found. Install podman, or set ENGINE=docker." >&2
  exit 1
}

mounts=(-v "$REPO_ROOT:/repo:ro")

if [ -x "$JETSKI_SAR" ] && [ -d "$GRTE" ]; then
  echo "Extracting Antigravity CLI (first run downloads; subsequent runs are cached) ..."
  log="$(mktemp -t jetski_sar.XXXXXX)"
  trap 'rm -f "$log"' EXIT
  SAR_EXTRACT_ONLY=1 "$JETSKI_SAR" >"$log" 2>&1 || true
  extract_dir="$(grep -o '[^ ]*/sar\.[^ ]*' "$log" | head -n1 || true)"

  if [ -n "$extract_dir" ] && [ -d "$extract_dir" ]; then
    echo "  mounted from $extract_dir"
    mounts+=(-v "$extract_dir:/opt/jetski:ro" -v "$GRTE:/usr/grte:ro")
  else
    echo "  WARNING: extraction produced no directory; Antigravity checks will skip." >&2
    sed 's/^/    /' "$log" | tail -5 >&2
  fi
else
  echo "Antigravity CLI not found at $JETSKI_SAR; those checks will skip."
fi

echo "Building $IMAGE ..."
"$ENGINE" build -q -t "$IMAGE" "$HERE" >/dev/null

# Runs as root because rootless podman maps the invoking user to container root,
# which is needed to read the mounted Antigravity tree (mode 0500, owner-only).
echo "Running clean-room verification against $REPO_ROOT"
exec "$ENGINE" run --rm --network=host --user root "${mounts[@]}" "$IMAGE"
