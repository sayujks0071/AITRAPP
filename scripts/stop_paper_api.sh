#!/usr/bin/env bash
set -euo pipefail

# Stop the paper-trading API by PID file or process name
# - Reads PID from logs/api_8000.pid if it exists
# - Falls back to killing uvicorn processes if PID file missing
# - Defaults to port 8000, but respects API_PORT env var

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
PID_FILE="$LOG_DIR/api_8000.pid"
API_PORT="${API_PORT:-8000}"

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    echo "Stopping API (PID $PID)..."
    kill "$PID" || true
    # Wait a bit for graceful shutdown
    sleep 2
    if ps -p "$PID" >/dev/null 2>&1; then
      echo "Force killing PID $PID..."
      kill -9 "$PID" || true
    fi
    rm -f "$PID_FILE"
    echo "✅ Stopped API (PID $PID)"
  else
    echo "⚠️  PID $PID from $PID_FILE is not running (stale PID file)"
    rm -f "$PID_FILE"
  fi
else
  # Fallback: find and kill uvicorn processes on the port
  echo "No PID file found, searching for uvicorn processes on port $API_PORT..."
  PIDS=$(lsof -ti :"$API_PORT" 2>/dev/null || true)
  if [[ -n "$PIDS" ]]; then
    for pid in $PIDS; do
      if ps -p "$pid" >/dev/null 2>&1; then
        echo "Stopping process $pid on port $API_PORT..."
        kill "$pid" || true
        sleep 1
        if ps -p "$pid" >/dev/null 2>&1; then
          kill -9 "$pid" || true
        fi
        echo "✅ Stopped process $pid"
      fi
    done
  else
    echo "⚠️  No API process found on port $API_PORT"
  fi
fi




