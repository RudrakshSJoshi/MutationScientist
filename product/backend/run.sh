#!/usr/bin/env bash
# MutationScientist REST API launcher (FastAPI + uvicorn on :8080).
# Wraps the EXISTING Streamlit services in ~/Desktop/application/services.
set -euo pipefail
cd "$(dirname "$0")"

# Point at the Streamlit app whose services we reuse (override with the env var).
export MUTATIONSCIENTIST_APP_DIR="${MUTATIONSCIENTIST_APP_DIR:-$HOME/Desktop/application}"

# Load the app's gitignored integration env so the API serves REAL data:
#   BOLTZ_PREDICTIONS_PATH (real Boltz run) and OPENAI_* (the :8000 model) so
#   /predict is live and /interpret calls the served model. Mock/template is used
#   for anything unset — exactly like the Streamlit app. No secrets committed.
if [ -f "$MUTATIONSCIENTIST_APP_DIR/.env" ]; then
  set -a; . "$MUTATIONSCIENTIST_APP_DIR/.env"; set +a
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install uv, or: python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi
[ -d .venv ] || uv venv --python 3.13 .venv
uv pip install -q -r requirements.txt

PORT="${PORT:-8080}"
exec uv run uvicorn main:app --host 127.0.0.1 --port "$PORT" "$@"
