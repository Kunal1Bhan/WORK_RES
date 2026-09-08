#!/usr/bin/env bash
# One-command local demo: install -> API + worker -> seed -> order -> chaos -> recover.
# Uses port 8120 and a throwaway DB so it never touches your real stack.
# Usage: ./scripts/demo.sh   (Git Bash / Linux / macOS)
set -euo pipefail
cd "$(dirname "$0")/.."
PORT=8120
if (echo > /dev/tcp/127.0.0.1/$PORT) >/dev/null 2>&1; then
  echo "error: port $PORT busy — stop whatever is on it first"; exit 1
fi
pip install -q -r requirements.txt
export DATABASE_URL="sqlite:///./demo.db" REDIS_URL=""
rm -f demo.db
python -m uvicorn app.main:app --host 127.0.0.1 --port $PORT & API=$!
python -m app.worker & WORKER=$!
trap 'kill $API $WORKER 2>/dev/null; rm -f demo.db' EXIT
for i in $(seq 1 30); do curl -sf http://127.0.0.1:$PORT/health && break || sleep 1; done
python scripts/seed.py --items 3
curl -s -X POST http://127.0.0.1:$PORT/api/orders -H 'Content-Type: application/json' -d '{"item":"demo-book"}'; echo
python failure-engine/failurectl.py error --rate 1.0 --api http://127.0.0.1:$PORT
curl -s -o /dev/null -w "during chaos: %{http_code}\n" -X POST http://127.0.0.1:$PORT/api/orders -H 'Content-Type: application/json' -d '{"item":"x"}'
python failure-engine/failurectl.py --api http://127.0.0.1:$PORT clear
curl -s http://127.0.0.1:$PORT/api/orders | head -c 200; echo
echo DEMO OK
