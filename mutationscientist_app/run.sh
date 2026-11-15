#!/usr/bin/env bash
# Convenience launcher for the MutationScientist app (uses uv + Python 3.13).
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install uv, or use: python -m venv .venv && pip install -r requirements.txt && streamlit run app.py"
  exit 1
fi

[ -d .venv ] || uv venv --python 3.13 .venv
uv pip install -q -r requirements.txt
exec uv run streamlit run app.py "$@"
