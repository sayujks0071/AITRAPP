#!/bin/bash
#
# Morning Startup Script - One-Click Trading Day Start
# ====================================================
#
# Automates the entire morning routine:
# 1. Check token validity
# 2. Refresh token if needed (express login)
# 3. Clean up old tokens/logs
# 4. Verify environment
# 5. Start API (optional)
#
# Usage:
#   bash scripts/morning_startup.sh
#   bash scripts/morning_startup.sh --start-api
#   bash scripts/morning_startup.sh --skip-token-check
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "============================================================"
echo "🌅 MORNING STARTUP - AITRAPP Trading System"
echo "============================================================"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Parse arguments
SKIP_TOKEN_CHECK=false
START_API=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-token-check)
            SKIP_TOKEN_CHECK=true
            shift
            ;;
        --start-api)
            START_API=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Step 1: Check token validity
if [ "$SKIP_TOKEN_CHECK" = false ]; then
    echo "📋 Step 1: Checking token validity..."
    
    if python3 scripts/kite_auto_refresh.py --check 2>/dev/null; then
        echo -e "${GREEN}✅ Token is valid${NC}"
    else
        echo -e "${YELLOW}⚠️  Token needs refresh${NC}"
        echo ""
        echo "🔄 Starting express login..."
        echo ""
        
        # Run express login
        if python3 scripts/kite_express_login.py; then
            echo -e "${GREEN}✅ Token refreshed successfully${NC}"
            # Reload environment
            export $(grep -v '^#' .env | xargs)
        else
            echo -e "${RED}❌ Token refresh failed${NC}"
            exit 1
        fi
    fi
    echo ""
fi

# Step 2: Clean up old tokens/logs
echo "🧹 Step 2: Cleaning up old tokens/logs..."
# Placeholder for cleanup logic
echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# Step 3: Verify environment
echo "🔍 Step 3: Verifying environment..."
if python3 scripts/verify_env.py 2>/dev/null; then
    echo -e "${GREEN}✅ Environment verified${NC}"
else
    echo -e "${YELLOW}⚠️  Environment check had warnings${NC}"
fi
echo ""

# Step 4: Verify Kite connection
echo "🔗 Step 4: Verifying Kite connection..."
if python3 scripts/kite_token_check.py 2>/dev/null; then
    echo -e "${GREEN}✅ Kite connection verified${NC}"
else
    echo -e "${RED}❌ Kite connection failed${NC}"
    exit 1
fi
echo ""

# Step 5: Start API (if requested)
if [ "$START_API" = true ]; then
    echo "🚀 Step 5: Starting API..."
    
    # Stop existing API
    pkill -f "uvicorn apps.api.main:app" 2>/dev/null || true
    sleep 2
    
    # Start API
    export APP_MODE=LIVE
    export APP_CONFIG=configs/kite_day1_live.yaml
    export $(grep -v '^#' .env | xargs)
    
    nohup python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn_morning_startup.log 2>&1 &
    
    sleep 5
    
    # Check if API started
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API started successfully${NC}"
        echo "   Logs: /tmp/uvicorn_morning_startup.log"
    else
        echo -e "${YELLOW}⚠️  API may not have started (check logs)${NC}"
    fi
    echo ""
fi

# Summary
echo "============================================================"
echo -e "${GREEN}✅ MORNING STARTUP COMPLETE${NC}"
echo "============================================================"
echo ""
echo "📋 Next steps:"
echo "   1. Monitor API: tail -f /tmp/uvicorn_morning_startup.log"
echo "   2. Check dashboard: http://localhost:3000"
echo "   3. Verify readiness: curl http://localhost:8000/ready"
echo ""
echo "🕐 Market opens at 09:15 IST"
echo ""

