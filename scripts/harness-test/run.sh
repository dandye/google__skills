#!/usr/bin/env bash
#
# Build and run the cross-harness clean-room verification.
#
#   scripts/harness-test/run.sh
#
# Uses rootless podman by default; set ENGINE=docker to override. Requires no
# credentials and touches nothing in your home directory.

set -euo pipefail

ENGINE="${ENGINE:-podman}"
IMAGE="${IMAGE:-secops-harness:latest}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

command -v "$ENGINE" >/dev/null || {
  echo "ERROR: $ENGINE not found. Install podman, or set ENGINE=docker." >&2
  exit 1
}

echo "Building $IMAGE ..."
"$ENGINE" build -q -t "$IMAGE" "$HERE" >/dev/null

echo "Running clean-room verification against $REPO_ROOT"
exec "$ENGINE" run --rm --network=host \
  -v "$REPO_ROOT:/repo:ro" \
  "$IMAGE"
