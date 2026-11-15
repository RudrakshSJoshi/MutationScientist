#!/usr/bin/env bash
# serve_forever.sh — keep the MutationScientist avatar server up all night.
# Restarts node server.js if it ever exits. Logs to tools/serve_forever.log.
# Usage (from anam-explainer/):  bash tools/serve_forever.sh
set -u
cd "$(dirname "$0")/.."
PORT="${PORT:-3000}"
LOG="tools/serve_forever.log"
echo "[$(date '+%F %T')] watchdog starting on :$PORT" >> "$LOG"

# free the port if something stale holds it
lsof -ti tcp:"$PORT" | xargs kill 2>/dev/null || true
sleep 1

while true; do
  echo "[$(date '+%F %T')] starting server" >> "$LOG"
  PORT="$PORT" node server.js >> "$LOG" 2>&1
  code=$?
  echo "[$(date '+%F %T')] server exited (code $code); restarting in 3s" >> "$LOG"
  sleep 3
done
