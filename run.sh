#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8099}"
HOST="${HOST:-127.0.0.1}"

echo "================================================="
echo "   EXPERTOS WORLD OS — Multi-Agent Platform     "
echo "   Release v0.2.0 (Autonomous Agent Blueprint)  "
echo "================================================="

if [[ -f .env ]]; then
    echo "Loading environment from .env..."
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
fi

if [[ ! -d .venv ]]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Ensuring dependencies are installed..."
pip install -q -r requirements.txt

echo "Running automated verification tests..."
pytest -q

echo "Starting EXPERTOS WORLD OS on http://${HOST}:${PORT}..."
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"
