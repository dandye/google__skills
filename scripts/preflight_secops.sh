#!/usr/bin/env bash
#
# Preflight check for the Google SecOps MCP server.
#
# Agent clients register MCP tools once, when they start. If the connection
# fails the session simply has no SecOps tools and usually reports no error,
# so run this before launching. Ten seconds here replaces a long archaeology
# session.
#
# Usage: scripts/preflight_secops.sh

set -euo pipefail

: "${PROJECT_ID:?PROJECT_ID unset. Source your .env or let direnv load it.}"
: "${CUSTOMER_ID:?CUSTOMER_ID unset. Source your .env or let direnv load it.}"
: "${REGION:?REGION unset. Source your .env or let direnv load it.}"

SERVER_URL="${SERVER_URL:-https://chronicle.${REGION}.rep.googleapis.com/mcp}"

if ! TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null); then
  echo "FAIL: Application Default Credentials are unavailable."
  echo "  Either run: gcloud auth application-default login"
  echo "  Or export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json"
  exit 1
fi

CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${SERVER_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}')

if [ "${CODE}" != "200" ]; then
  echo "FAIL: ${SERVER_URL} returned HTTP ${CODE}."
  echo "  403 usually means the active principal lacks mcp.googleapis.com/tools.call."
  exit 1
fi

echo "OK: MCP reachable at ${SERVER_URL} (project ${PROJECT_ID}, region ${REGION})."
echo "Launch the CLI from this directory so it inherits these credentials."
