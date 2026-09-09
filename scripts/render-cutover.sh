#!/usr/bin/env bash
# Run this in your local terminal (Render CLI already logged in).
# Agent sandboxes cannot reach api.render.com.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== whoami =="
render whoami -o text

echo
echo "== validate blueprint =="
render blueprints validate ./render.yaml -o text

echo
echo "== services =="
render services -o json | python3 -c '
import json,sys
raw=sys.stdin.read()
data=json.loads(raw)
items = data if isinstance(data, list) else data.get("items") or data.get("services") or []
for row in items:
    s = row.get("service", row) if isinstance(row, dict) else row
    if not isinstance(s, dict):
        continue
    details = s.get("serviceDetails") or {}
    print("\t".join([
        s.get("id") or "?",
        s.get("type") or s.get("serviceType") or "?",
        s.get("name") or "?",
        details.get("url") or details.get("host") or "",
    ]))
'

echo
echo "If a web service id printed above, trigger deploy with:"
echo "  render deploys create <SRV_ID> --confirm"
echo
echo "Dashboard secrets still required on web (+ worker):"
echo "  GEMINI_API_KEY"
echo "  PENSIVE_BOOTSTRAP_EMAIL / PENSIVE_BOOTSTRAP_PASSWORD  (optional)"
echo "Postgres: CREATE EXTENSION IF NOT EXISTS vector;"
