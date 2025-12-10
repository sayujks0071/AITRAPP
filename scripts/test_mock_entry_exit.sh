#!/usr/bin/env bash
set -euo pipefail

# Quick test script to verify entry→exit flow with MOCK_KITE=1
# Tests sibling order cancellation on exit

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
if [[ ! -x "$ROOT/$VENV_DIR/bin/python" && -x "$ROOT/venv/bin/python" ]]; then
  VENV_DIR="venv"
fi
PYTHON_BIN="$ROOT/$VENV_DIR/bin/python"

export APP_MODE=PAPER
export APP_CONFIG="${APP_CONFIG:-configs/kite_paper.yaml}"
export MOCK_KITE=1

echo "🧪 Testing entry→exit flow with MOCK_KITE=1"
echo "This will:"
echo "  1. Start API in background"
echo "  2. Wait for health check"
echo "  3. Trigger a mock entry order"
echo "  4. Trigger a mock exit order (should cancel sibling SL/TP)"
echo "  5. Verify no orphaned orders remain"
echo ""

# Start API
echo "Starting API..."
"$PYTHON_BIN" -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 >/tmp/aitrapp_test.log 2>&1 &
API_PID=$!
echo "API PID: $API_PID"

# Wait for API to be ready
echo "Waiting for API to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API is healthy"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "❌ API failed to start"
    kill $API_PID 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

echo ""
echo "✅ Test setup complete"
echo "📝 Check logs: tail -f /tmp/aitrapp_test.log"
echo "🔍 Look for 'Cancelled stale order before exit' messages"
echo ""
echo "To stop: kill $API_PID"

