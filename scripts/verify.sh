#!/usr/bin/env bash
# The gate: run this before every push. Three checks, offline, no Discord account.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/5: python version"
python3 - <<'PY'
import sys
assert sys.version_info >= (3, 10), "Python 3.10+ is required"
print("   python", ".".join(map(str, sys.version_info[:3])))
PY

echo "== 2/5: ruff"
python3 -m ruff check .

echo "== 3/5: tests"
python3 -m pytest -q

echo "== 4/5: imports with an empty environment"
env -u DISCORD_PUBLIC_KEY -u DISCORD_APPLICATION_ID python3 -c "import app; print('   app imports with nothing configured')"

echo "== 5/5: real server, real HTTP"
# Start with a dummy public key so the signature path is exercised. Without one the
# endpoint correctly answers 503 "not configured", which would prove nothing.
DUMMY_KEY="$(python3 -c 'print("ab" * 32)')"
DISCORD_PUBLIC_KEY="$DUMMY_KEY" DISCORD_APPLICATION_ID=1 \
  python3 -m uvicorn app:app --host 127.0.0.1 --port 8127 --log-level warning &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:8127/health" >/dev/null 2>&1; then break; fi
  sleep 0.25
done
code_health=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8127/health")
code_unsigned=$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:8127/interactions" -H 'Content-Type: application/json' -d '{"type":1}')
code_admin=$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:8127/admin/register-commands")
[ "$code_health" = "200" ] || { echo "GATE FAILED: /health returned $code_health"; exit 1; }
[ "$code_unsigned" = "401" ] || { echo "GATE FAILED: unsigned /interactions returned $code_unsigned (must be 401)"; exit 1; }
[ "$code_admin" = "401" ] || [ "$code_admin" = "503" ] || { echo "GATE FAILED: /admin without token returned $code_admin"; exit 1; }
echo "   health 200, unsigned interaction 401, admin 401/503"

echo "== gardening: no gateway loop"
if grep -rInE "discord\.py|bot\.run\(|GatewayBot" --include=*.py app.py bot/ ; then
  echo "GATE FAILED: a gateway client crept in; this repo is HTTP-interactions only"
  exit 1
fi

echo
echo "GATE PASSED"
python3 -m pytest 2>/dev/null | grep -E "[0-9]+ (passed|failed)" | tail -1
