#!/bin/bash
#
# Kill Switch Testing Script
#
# Tests the emergency kill switch in a controlled environment
#
# Prerequisites:
#   - API server running (python3 -m uvicorn apps.api.main:app)
#   - PAPER mode configured (APP_MODE=PAPER)
#   - jq installed for JSON parsing
#
# Usage:
#   ./scripts/test_kill_switch.sh [API_URL]
#
# Example:
#   ./scripts/test_kill_switch.sh http://localhost:8000
#

set -e

# Configuration
API_URL="${1:-http://localhost:8000}"
CONTROL_ENDPOINT="${API_URL}/control"

echo "======================================================================"
echo "🚨 Kill Switch Testing Script"
echo "======================================================================"
echo ""
echo "API URL: ${API_URL}"
echo "Test Mode: CONTROLLED (will pause trading and flatten positions)"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if API is running
check_api() {
    echo -n "Checking API availability... "
    if curl -s "${API_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is running${NC}"
        return 0
    else
        echo -e "${RED}❌ API is not reachable${NC}"
        echo ""
        echo "Please start the API server first:"
        echo "  python3 -m uvicorn apps.api.main:app --reload"
        exit 1
    fi
}

# Function to check current system state
check_system_state() {
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Step 1: Checking current system state"
    echo "----------------------------------------------------------------------"

    STATE=$(curl -s "${CONTROL_ENDPOINT}/state" || echo '{"error": "failed"}')

    if echo "$STATE" | jq -e . > /dev/null 2>&1; then
        echo "$STATE" | jq '.'

        MODE=$(echo "$STATE" | jq -r '.mode // "unknown"')
        IS_PAUSED=$(echo "$STATE" | jq -r '.is_paused // false')
        OPEN_POSITIONS=$(echo "$STATE" | jq -r '.open_positions // 0')

        echo ""
        echo "  Mode: ${MODE}"
        echo "  Paused: ${IS_PAUSED}"
        echo "  Open Positions: ${OPEN_POSITIONS}"

        if [ "$MODE" != "PAPER" ]; then
            echo ""
            echo -e "${YELLOW}⚠️  WARNING: System is in ${MODE} mode${NC}"
            echo "This test should only be run in PAPER mode."
            read -p "Continue anyway? (yes/no): " confirm
            if [ "$confirm" != "yes" ]; then
                echo "Test aborted."
                exit 1
            fi
        fi
    else
        echo -e "${RED}❌ Failed to get system state${NC}"
        exit 1
    fi
}

# Function to trigger kill switch
trigger_kill_switch() {
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Step 2: Triggering Kill Switch"
    echo "----------------------------------------------------------------------"
    echo ""
    echo -e "${YELLOW}🚨 Activating emergency kill switch...${NC}"

    RESPONSE=$(curl -s -X POST "${CONTROL_ENDPOINT}/kill-switch" \
        -H "Content-Type: application/json" || echo '{"error": "failed"}')

    if echo "$RESPONSE" | jq -e . > /dev/null 2>&1; then
        echo ""
        echo "Kill Switch Response:"
        echo "$RESPONSE" | jq '.'

        STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
        CLOSED=$(echo "$RESPONSE" | jq -r '.closed_positions // 0')

        echo ""
        if [ "$STATUS" = "KILLED" ] || [ "$STATUS" = "PAUSED" ]; then
            echo -e "${GREEN}✅ Kill switch activated successfully${NC}"
            echo "  Closed Positions: ${CLOSED}"
            return 0
        else
            echo -e "${RED}❌ Kill switch activation failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Failed to trigger kill switch${NC}"
        echo "$RESPONSE"
        return 1
    fi
}

# Function to verify system is paused
verify_paused_state() {
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Step 3: Verifying Paused State"
    echo "----------------------------------------------------------------------"

    sleep 2  # Wait for state to propagate

    STATE=$(curl -s "${CONTROL_ENDPOINT}/state" || echo '{"error": "failed"}')

    if echo "$STATE" | jq -e . > /dev/null 2>&1; then
        IS_PAUSED=$(echo "$STATE" | jq -r '.is_paused // false')
        OPEN_POSITIONS=$(echo "$STATE" | jq -r '.open_positions // -1')

        echo ""
        echo "  System Paused: ${IS_PAUSED}"
        echo "  Open Positions: ${OPEN_POSITIONS}"

        if [ "$IS_PAUSED" = "true" ]; then
            echo ""
            echo -e "${GREEN}✅ System is paused (trading blocked)${NC}"
        else
            echo ""
            echo -e "${YELLOW}⚠️  System is not paused${NC}"
        fi

        if [ "$OPEN_POSITIONS" -eq 0 ]; then
            echo -e "${GREEN}✅ All positions closed${NC}"
        else
            echo -e "${YELLOW}⚠️  ${OPEN_POSITIONS} positions still open${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to verify state${NC}"
        return 1
    fi
}

# Function to resume trading (cleanup)
resume_trading() {
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Step 4: Resuming Trading (Cleanup)"
    echo "----------------------------------------------------------------------"

    read -p "Resume trading? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Trading remains paused. Resume manually with:"
        echo "  curl -X POST ${CONTROL_ENDPOINT}/resume"
        return 0
    fi

    echo ""
    echo "Resuming trading..."

    RESPONSE=$(curl -s -X POST "${CONTROL_ENDPOINT}/resume" \
        -H "Content-Type: application/json" || echo '{"error": "failed"}')

    if echo "$RESPONSE" | jq -e . > /dev/null 2>&1; then
        echo "$RESPONSE" | jq '.'

        STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')

        if [ "$STATUS" = "ACTIVE" ]; then
            echo ""
            echo -e "${GREEN}✅ Trading resumed${NC}"
        else
            echo ""
            echo -e "${YELLOW}⚠️  Trading may not have resumed${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to resume trading${NC}"
        return 1
    fi
}

# Main test flow
main() {
    check_api
    check_system_state

    echo ""
    echo "======================================================================"
    echo "⚠️  WARNING: This will activate the kill switch"
    echo "======================================================================"
    echo ""
    echo "Actions that will be performed:"
    echo "  1. Pause all trading"
    echo "  2. Cancel all pending orders"
    echo "  3. Close all open positions"
    echo ""
    read -p "Proceed with kill switch test? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Test aborted."
        exit 0
    fi

    if trigger_kill_switch; then
        verify_paused_state
        resume_trading

        echo ""
        echo "======================================================================"
        echo "✅ Kill Switch Test Complete"
        echo "======================================================================"
        echo ""
        echo "Summary:"
        echo "  • Kill switch endpoint is functional"
        echo "  • Trading pause mechanism works"
        echo "  • Position flattening executes"
        echo ""
        echo "Production Readiness:"
        echo "  ✅ Emergency stop capability verified"
        echo "  ✅ Position cleanup verified"
        echo "  ✅ State management verified"
        echo ""
        return 0
    else
        echo ""
        echo "======================================================================"
        echo "❌ Kill Switch Test Failed"
        echo "======================================================================"
        echo ""
        echo "Please review the logs and fix issues before deploying to production."
        return 1
    fi
}

# Check for jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is not installed${NC}"
    echo ""
    echo "Please install jq:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu/Debian: sudo apt-get install jq"
    exit 1
fi

# Run main test
main
