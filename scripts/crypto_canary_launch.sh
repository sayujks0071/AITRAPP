#!/bin/bash
# Crypto Canary Launch Script
# Pre-flight → Launch → Watch → Wrap

set -Eeuo pipefail

# Trap errors and attempt safe flatten on failure
trap 'echo "[FATAL] Launch failed – attempting safe flatten"; curl -fsS -X POST http://localhost:8000/flatten >/dev/null 2>&1 || true' ERR

API="${API:-http://localhost:8000}"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Crypto Canary Launch Script${NC}"
echo "=================================="
echo ""

# Pre-flight (90 seconds)
echo -e "${YELLOW}📋 Pre-Flight (90 seconds)${NC}"
echo ""

echo "1️⃣  Starting infra..."
docker compose up -d postgres redis
echo "   ✅ Infra started"
echo ""

echo "2️⃣  Activating venv and installing deps..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "   ✅ Virtual environment activated"
else
    echo "   ⚠️  No venv found, using system Python"
fi

if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo "   ✅ Dependencies installed"
else
    echo "   ⚠️  requirements.txt not found"
fi
echo ""

echo "3️⃣  Running GO/NO-GO check..."
if bash scripts/crypto_gonogo_check.sh; then
    echo -e "${GREEN}   ✅ GO/NO-GO check PASSED${NC}"
else
    echo -e "${RED}   ❌ GO/NO-GO check FAILED${NC}"
    echo ""
    echo "Please fix issues before proceeding."
    exit 1
fi
echo ""

# Launch
echo -e "${YELLOW}🚀 Launch (Canary LIVE: BTCUSDT Only)${NC}"
echo ""

echo "4️⃣  Copying canary config..."
cp configs/crypto_canary_live.yaml configs/app.yaml
echo "   ✅ Config copied"
echo ""

echo "5️⃣  Setting environment variables..."
export APP_MODE=CRYPTO_LIVE
export APP_TIMEZONE=UTC
export PYTHONPATH=.

# Check if API keys are set (bomb-proof check)
echo "${KRAKEN_API_KEY:?"Set KRAKEN_API_KEY"}" >/dev/null
echo "${KRAKEN_API_SECRET:?"Set KRAKEN_API_SECRET"}" >/dev/null
echo "   ✅ API keys validated"
echo ""

echo "6️⃣  Starting API..."
make crypto-paper > /tmp/crypto_canary_api.log 2>&1 &
API_PID=$!
echo "   ✅ API started (PID: $API_PID)"
echo "   Logs: /tmp/crypto_canary_api.log"
echo ""

echo "7️⃣  Waiting for API to be ready..."
for i in {1..30}; do
    if curl -fsS "$API/ready" > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ API is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}   ❌ API not ready after 30 attempts${NC}"
        echo "   Check logs: tail -f /tmp/crypto_canary_api.log"
        exit 1
    fi
    sleep 1
done
echo ""

echo "8️⃣  Health check..."
READY_RESPONSE=$(curl -fsS "$API/ready" | jq .)
echo "$READY_RESPONSE" | jq .
echo ""

# Watch instructions
echo -e "${YELLOW}👀 Watch (First 10 Minutes)${NC}"
echo ""
echo "In another terminal, run:"
echo -e "${GREEN}   make watch-crypto${NC}"
echo ""
echo "Or manually check metrics:"
echo -e "${GREEN}   curl -s $API/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total)'${NC}"
echo ""
echo "Expected healthy state:"
echo "   - trader_is_leader = 1"
echo "   - All *heartbeat_seconds < 5"
echo "   - trader_oco_orphans_total = 0"
echo "   - trader_crypto_ws_reconnects_total stays flat (≤1/10m)"
echo ""

# Post-canary wrap instructions
echo -e "${YELLOW}📊 Post-Canary Wrap (After 60-90 min)${NC}"
echo ""
echo "When ready, run:"
echo -e "${GREEN}   make score-crypto-day1${NC}"
echo -e "${GREEN}   make crypto-report${NC}"
echo ""
echo "Reports will be in:"
echo "   - reports/burnin/crypto_day1_*.json"
echo "   - reports/crypto/crypto_report_*.md"
echo ""

# Tripwires
echo -e "${YELLOW}🚨 Tripwires & Rollback${NC}"
echo ""
echo "Panic flatten:"
echo -e "${GREEN}   curl -fsS -X POST $API/flatten | jq${NC}"
echo ""
echo "Rollback to PAPER:"
echo -e "${GREEN}   export APP_MODE=CRYPTO_PAPER${NC}"
echo -e "${GREEN}   pkill -f 'uvicorn' || true${NC}"
echo -e "${GREEN}   make crypto-paper &${NC}"
echo ""

echo -e "${GREEN}✅ Crypto Canary Launch Complete!${NC}"
echo ""
echo "API is running in background (PID: $API_PID)"
echo "Monitor with: make watch-crypto"
echo "Stop with: pkill -f 'uvicorn'"
echo ""

