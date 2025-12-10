#!/usr/bin/env bash
set -euo pipefail

# Start the paper-trading API with the local virtualenv and log to logs/api_8000.log
# - Uses .venv by default; falls back to venv if VENV_DIR not provided.
# - Defaults: APP_MODE=PAPER, APP_CONFIG=configs/kite_paper.yaml, API_PORT=8000

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/api_8000.log"

VENV_DIR="${VENV_DIR:-.venv}"
if [[ ! -x "$ROOT/$VENV_DIR/bin/python" && -x "$ROOT/venv/bin/python" ]]; then
  VENV_DIR="venv"
fi
PYTHON_BIN="$ROOT/$VENV_DIR/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Python not found at $VENV_DIR/bin/python. Set VENV_DIR or create the venv first."
  exit 1
fi

if ! "$PYTHON_BIN" -m uvicorn --version >/dev/null 2>&1; then
  echo "❌ uvicorn not installed in $VENV_DIR. Install deps: $PYTHON_BIN -m pip install -r requirements.txt"
  exit 1
fi

export APP_MODE="${APP_MODE:-PAPER}"
export APP_CONFIG="${APP_CONFIG:-configs/kite_paper.yaml}"
API_PORT="${API_PORT:-8000}"

if nc -z localhost "$API_PORT" >/dev/null 2>&1; then
  echo "⚠️  Port $API_PORT already in use. Stop the existing service or set API_PORT to another port."
  exit 1
fi

echo "Starting API (APP_MODE=$APP_MODE, APP_CONFIG=$APP_CONFIG) on port $API_PORT ..."
"$PYTHON_BIN" -m uvicorn apps.api.main:app --host 0.0.0.0 --port "$API_PORT" >>"$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$LOG_DIR/api_8000.pid"
echo "✅ Started PID $PID; logs: $LOG_FILE"
echo "Monitor: tail -f $LOG_FILE"
