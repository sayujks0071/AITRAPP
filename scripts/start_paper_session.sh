#!/usr/bin/env bash
# Complete PAPER session startup script
set -euo pipefail

PORT="${PORT:-8000}"
API="${API:-http://localhost:${PORT}}"

echo "🚀 Starting PAPER Session"
echo "========================"
echo ""

# 1. Check port
echo "1️⃣  Checking port ${PORT}..."
if lsof -nP -iTCP:${PORT} | grep LISTEN >/dev/null 2>&1; then
    PID=$(lsof -nP -iTCP:${PORT} | grep LISTEN | awk '{print $2}' | head -1)
    echo "   ⚠️  Port ${PORT} is in use (PID: ${PID})"
    echo "   Kill it? (y/n)"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -TERM ${PID} 2>/dev/null || kill -9 ${PID} 2>/dev/null
        sleep 2
        echo "   ✅ Port ${PORT} freed"
    else
        echo "   → Use different port: PORT=8010 make paper"
        exit 1
    fi
else
    echo "   ✅ Port ${PORT} is free"
fi
echo ""

# 2. Check database
echo "2️⃣  Checking database..."
if command -v psql >/dev/null 2>&1 && [ -n "${DATABASE_URL:-}" ]; then
    if psql "${DATABASE_URL}" -c "SELECT 1;" >/dev/null 2>&1; then
        echo "   ✅ Database connection OK"
    else
        echo "   ⚠️  Database not accessible - start with: docker compose up -d postgres"
    fi
else
    echo "   ⚠️  psql not available or DATABASE_URL not set"
fi
echo ""

# 3. Check Redis
echo "3️⃣  Checking Redis..."
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli ping >/dev/null 2>&1; then
        echo "   ✅ Redis connection OK"
    else
        echo "   ⚠️  Redis not accessible - start with: docker compose up -d redis"
    fi
else
    echo "   ⚠️  redis-cli not available"
fi
echo ""

# 4. Apply migration if needed
echo "4️⃣  Checking migrations..."
if command -v alembic >/dev/null 2>&1; then
    echo "   → Running: alembic upgrade head"
    alembic upgrade head 2>&1 | grep -E "(Running|INFO|INFO)" || echo "   ✅ Migrations up to date"
elif python3 -c "import alembic" 2>/dev/null; then
    echo "   → Running: alembic upgrade head (via Python)"
    python3 -c "import sys; sys.path.insert(0, '.'); from alembic.config import main; main(['upgrade', 'head'])" 2>&1 | grep -E "(Running|INFO)" || echo "   ✅ Migrations up to date"
else
    echo "   ⚠️  alembic not available - skipping migration check (may already be applied)"
fi
echo ""

# 5. Check dependencies
echo "5️⃣  Checking dependencies..."
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "   ⚠️  uvicorn not found"
    echo "   → Install dependencies: pip install -r requirements.txt"
    echo "   → Or activate virtual environment: source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "   ✅ Dependencies OK"
fi
echo ""

# 6. Start API in background
echo "6️⃣  Starting API on port ${PORT}..."
echo "   → Running: PORT=${PORT} make paper"
echo "   → This will run in background. Check logs with: tail -f logs/*.log"
echo ""

# Start in background and capture PID
mkdir -p logs
(
    export APP_MODE=PAPER
    export PORT=${PORT}
    nohup python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT} > logs/api_${PORT}.log 2>&1 &
    echo $! > /tmp/aitrapp_api_${PORT}.pid
    echo "   ✅ API started (PID: $(cat /tmp/aitrapp_api_${PORT}.pid))"
)

# Wait for health check
echo "   → Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s "${API}/health" >/dev/null 2>&1; then
        echo "   ✅ API is responding"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ⚠️  API not responding after 30s - check logs: tail -f logs/api_${PORT}.log"
        exit 1
    fi
    sleep 1
done
echo ""

# 7. Run smoke check
echo "7️⃣  Running smoke check..."
make smoke-check || echo "   ⚠️  Smoke check had warnings (check output above)"
echo ""

# 8. Run quick sanity
echo "8️⃣  Running quick sanity..."
make quick-sanity || echo "   ⚠️  Quick sanity had warnings (check output above)"
echo ""

# 9. Summary
echo "✅ PAPER Session Started!"
echo ""
echo "📋 Next Steps:"
echo "   1. Open dashboard: make live-dashboard"
echo "   2. Attach to tmux: tmux attach -t live"
echo "   3. Monitor logs: tail -f logs/*.log"
echo "   4. Test trade: python scripts/synthetic_plan_injector.py --symbol NIFTY --side LONG --qty 50 --strategy ORB"
echo "   5. Check metrics: curl -s ${API}/metrics | grep trader_"
echo ""
echo "🛑 To stop: kill \$(cat /tmp/aitrapp_api_${PORT}.pid)"

