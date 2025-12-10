#!/usr/bin/env bash
set -euo pipefail

# Morning boot script for paper trading (runs uvicorn and verifies readiness).
# - Assumes repo in /Users/mac/CRYPTO/AITRAPP (adjust ROOT if moved).
# - Uses .venv (fallback to venv). Exits if uvicorn not installed.
# - Starts API on port 8000 and hits /health and /ready.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/api_8000.log"

# Venv detection
VENV_DIR="${VENV_DIR:-.venv}"
if [[ ! -x "$ROOT/$VENV_DIR/bin/python" && -x "$ROOT/venv/bin/python" ]]; then
  VENV_DIR="venv"
fi
PYTHON_BIN="$ROOT/$VENV_DIR/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Python not found at $VENV_DIR/bin/python. Create venv first."
  exit 1
fi

if ! "$PYTHON_BIN" -m uvicorn --version >/dev/null 2>&1; then
  echo "❌ uvicorn not installed in $VENV_DIR. Install deps: $PYTHON_BIN -m pip install -r requirements.txt"
  exit 1
fi

# Env defaults (override as needed)
export APP_MODE="${APP_MODE:-PAPER}"
export APP_CONFIG="${APP_CONFIG:-configs/kite_paper.yaml}"
export MOCK_KITE="${MOCK_KITE:-0}"
API_PORT="${API_PORT:-8000}"

if nc -z localhost "$API_PORT" >/dev/null 2>&1; then
  echo "⚠️  Port $API_PORT already in use. Stop existing service or set API_PORT."
  exit 1
fi

echo "Starting paper API (APP_MODE=$APP_MODE, MOCK_KITE=$MOCK_KITE) ..."
"$PYTHON_BIN" -m uvicorn apps.api.main:app --host 0.0.0.0 --port "$API_PORT" >>"$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$LOG_DIR/api_8000.pid"
echo "✅ Started PID $PID; logs: $LOG_FILE"

# Grace period then probe health/ready
echo "Waiting for API to start..."
sleep 8

echo ""
echo "Probing /health and /ready ..."
HEALTH_RESPONSE=$(curl -m 5 -s "http://localhost:$API_PORT/health" 2>/dev/null || echo "")
READY_RESPONSE=$(curl -m 5 -s "http://localhost:$API_PORT/ready" 2>/dev/null || echo "")

if [[ -n "$HEALTH_RESPONSE" ]]; then
  echo "✅ /health: $HEALTH_RESPONSE"
else
  echo "⚠️  /health: No response (API may still be starting)"
fi

if [[ -n "$READY_RESPONSE" ]]; then
  echo "✅ /ready: $READY_RESPONSE"
else
  echo "⚠️  /ready: No response (API may still be starting)"
fi

if [[ -z "$HEALTH_RESPONSE" && -z "$READY_RESPONSE" ]]; then
  echo ""
  echo "⚠️  API may not be ready yet. Check logs: tail -f $LOG_FILE"
  echo "   Or wait a few more seconds and check: curl http://localhost:$API_PORT/health"
else
  echo ""
  echo "✅ API appears to be running. Monitor logs: tail -f $LOG_FILE"
fi

# SEBI Compliance Checks
echo ""
echo "=================================================="
echo "Running SEBI Compliance Checks..."
echo "=================================================="

# Check 1: Verify compliance mode
if [[ "${COMPLIANCE_SEBI_2025:-0}" == "1" ]]; then
  echo "✅ COMPLIANCE_SEBI_2025 enabled"
else
  echo "⚠️  COMPLIANCE_SEBI_2025 not enabled (set COMPLIANCE_SEBI_2025=1 for production)"
fi

# Check 2: Verify audit logging implementation
if "$PYTHON_BIN" scripts/test_sebi_compliance_simple.py >/dev/null 2>&1; then
  echo "✅ SEBI compliance features verified"
else
  echo "⚠️  SEBI compliance verification failed. Run: python3 scripts/test_sebi_compliance_simple.py"
fi

# Check 3: Test kill switch endpoint
KILL_SWITCH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$API_PORT/control/state" 2>/dev/null || echo "000")
if [[ "$KILL_SWITCH_CHECK" == "200" ]]; then
  echo "✅ Kill switch endpoint accessible"
else
  echo "⚠️  Kill switch endpoint not accessible (status: $KILL_SWITCH_CHECK)"
fi

# Check 4: Database audit logs table
if [[ -n "${DATABASE_URL:-}" ]]; then
  if command -v psql >/dev/null 2>&1; then
    if psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM audit_logs LIMIT 1;" >/dev/null 2>&1; then
      echo "✅ Audit logs database accessible"
    else
      echo "⚠️  Audit logs database not accessible"
    fi
  else
    echo "⚠️  psql not available, skipping database check"
  fi
else
  echo "⚠️  DATABASE_URL not set, skipping database check"
fi

echo ""
echo "=================================================="
echo "Morning Boot Complete"
echo "=================================================="
echo ""
echo "Next Steps:"
echo "  • Monitor API: tail -f $LOG_FILE"
echo "  • View dashboard: http://localhost:3000 (if ops-browser running)"
echo "  • Check system state: curl http://localhost:$API_PORT/control/state | jq"
echo "  • Kill switch test (staging only): ./scripts/test_kill_switch.sh"
echo ""
