#!/bin/bash
# 60-second infrastructure verification
# Checks orchestrator, metrics, docker, and watch commands

set -e

echo "🔍 Infrastructure Verification"
echo "=============================="
echo ""

# 1) Check orchestrator
echo "1️⃣  TradingOrchestrator & Core Components"
echo "-------------------------------------------"
if grep -q "class TradingOrchestrator" packages/core/orchestrator.py; then
    echo "   ✅ TradingOrchestrator class found"
else
    echo "   ❌ TradingOrchestrator class NOT found"
    exit 1
fi

if grep -q "flatten_all" packages/core/orchestrator.py; then
    echo "   ✅ flatten_all() method found"
else
    echo "   ❌ flatten_all() method NOT found"
fi

if grep -qi "orphan\|_scan_supervisor" packages/core/orchestrator.py; then
    echo "   ✅ Orphan scan / supervisor found"
else
    echo "   ⚠️  Orphan scan / supervisor not found (may be in different location)"
fi

if grep -q "crypto_router" packages/core/orchestrator.py apps/api/main.py; then
    echo "   ✅ crypto_router wiring found"
else
    echo "   ⚠️  crypto_router wiring not found"
fi

echo ""

# 2) Check metrics
echo "2️⃣  Metrics Definitions"
echo "------------------------"
if grep -q "crypto_flatten_duration_seconds" packages/core/metrics.py apps/api/main.py; then
    echo "   ✅ crypto_flatten_duration_seconds found"
else
    echo "   ❌ crypto_flatten_duration_seconds NOT found"
fi

if grep -q "binance_used_weight_1m\|binance_order_count_1m\|binance_time_skew_ms" packages/core/metrics.py; then
    echo "   ✅ Binance metrics found"
else
    echo "   ❌ Binance metrics NOT found"
fi

if grep -q "trader_is_leader\|trader_.*_heartbeat_seconds\|trader_oco_orphans_total\|trader_leader_changes_total" packages/core/metrics.py; then
    echo "   ✅ Core equity metrics found"
else
    echo "   ⚠️  Some core equity metrics may be missing"
fi

echo ""

# 3) Check crypto router
echo "3️⃣  Crypto Router & Venue Support"
echo "----------------------------------"
if grep -q "BINANCE_SPOT\|KRAKEN_SPOT" packages/core/venues/crypto_router.py configs/crypto_*.yaml 2>/dev/null; then
    echo "   ✅ Venue support (BINANCE_SPOT/KRAKEN_SPOT) found"
else
    echo "   ⚠️  Venue support not found in expected locations"
fi

if grep -q "use_native_oco\|spread" packages/core/venues/crypto_router.py 2>/dev/null; then
    echo "   ✅ OCO and spread guards found"
else
    echo "   ⚠️  OCO/spread guards not found"
fi

echo ""

# 4) Check docker config
echo "4️⃣  Docker Infrastructure"
echo "-------------------------"
if [ -f docker-compose.yml ]; then
    if grep -q "postgres\|redis" docker-compose.yml; then
        echo "   ✅ docker-compose.yml found with postgres/redis"
    else
        echo "   ⚠️  docker-compose.yml found but postgres/redis not configured"
    fi
    
    if grep -q "healthcheck" docker-compose.yml; then
        echo "   ✅ Healthchecks configured"
    else
        echo "   ⚠️  Healthchecks not found"
    fi
else
    echo "   ❌ docker-compose.yml NOT found"
fi

echo ""

# 5) Check Makefile targets
echo "5️⃣  Makefile Targets"
echo "--------------------"
if grep -q "watch-metrics:" Makefile; then
    echo "   ✅ watch-metrics target found"
else
    echo "   ❌ watch-metrics target NOT found"
fi

if grep -q "watch-crypto:" Makefile; then
    echo "   ✅ watch-crypto target found"
else
    echo "   ❌ watch-crypto target NOT found"
fi

if grep -q "kite-canary-launch:" Makefile; then
    echo "   ✅ kite-canary-launch target found"
else
    echo "   ⚠️  kite-canary-launch target not found"
fi

echo ""

# 6) Check API endpoints
echo "6️⃣  API Endpoints (if running)"
echo "-------------------------------"
if curl -fsS http://localhost:8000/ready > /dev/null 2>&1; then
    echo "   ✅ /ready endpoint responding"
    
    if curl -fsS http://localhost:8000/metrics > /dev/null 2>&1; then
        echo "   ✅ /metrics endpoint responding"
        
        # Check for key metrics
        METRICS=$(curl -s http://localhost:8000/metrics)
        if echo "$METRICS" | grep -q "trader_is_leader"; then
            echo "   ✅ trader_is_leader metric present"
        else
            echo "   ⚠️  trader_is_leader metric not found"
        fi
        
        if echo "$METRICS" | grep -q "trader_.*_heartbeat_seconds"; then
            echo "   ✅ Heartbeat metrics present"
        else
            echo "   ⚠️  Heartbeat metrics not found"
        fi
    else
        echo "   ⚠️  /metrics endpoint not responding"
    fi
else
    echo "   ⚠️  API not running (start with: make paper or make live)"
fi

echo ""

# 7) Check docker services
echo "7️⃣  Docker Services"
echo "--------------------"
if docker compose ps 2>/dev/null | grep -q "postgres\|redis"; then
    echo "   ✅ Docker services running"
    docker compose ps 2>/dev/null | grep -E "postgres|redis" || true
else
    echo "   ⚠️  Docker services not running (start with: docker compose up -d postgres redis)"
fi

echo ""
echo "=============================="
echo "✅ Verification complete!"
echo ""
echo "Next steps:"
echo "  1. Start infra: docker compose up -d postgres redis"
echo "  2. Start API: make paper (or make live for LIVE mode)"
echo "  3. Watch metrics: make watch-metrics (or make watch-crypto)"
echo "  4. Check status: make kite-canary-status"

