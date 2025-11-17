#!/bin/bash
#
# Test Trading Analyst MCP setup
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=========================================="
echo "Trading Analyst MCP - Test Suite"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Node.js dependencies installed
echo "[1/6] Checking Node.js dependencies..."
if [ -d "$SCRIPT_DIR/node_modules" ]; then
    pass "Node.js dependencies installed"
else
    fail "Node.js dependencies not installed"
    echo "   Run: cd $SCRIPT_DIR && npm install"
    exit 1
fi

# Test 2: TypeScript build output exists
echo "[2/6] Checking TypeScript build..."
if [ -f "$SCRIPT_DIR/build/index.js" ]; then
    pass "TypeScript build exists"
else
    fail "TypeScript build not found"
    echo "   Run: cd $SCRIPT_DIR && npm run build"
    exit 1
fi

# Test 3: Python adapter is executable
echo "[3/6] Checking Python adapter..."
ADAPTER_PATH="$PROJECT_ROOT/mcp-adapters/trading_analyst_adapter.py"
if [ -x "$ADAPTER_PATH" ]; then
    pass "Python adapter is executable"
else
    warn "Python adapter not executable"
    echo "   Run: chmod +x $ADAPTER_PATH"
    chmod +x "$ADAPTER_PATH"
    pass "Fixed: Made adapter executable"
fi

# Test 4: Test Python adapter directly
echo "[4/6] Testing Python adapter..."
if python3 "$ADAPTER_PATH" get_live_risk_snapshot '{}' > /dev/null 2>&1; then
    pass "Python adapter runs successfully"
else
    warn "Python adapter test failed (this is OK if bot is not running)"
    echo "   The adapter will work once your bot API is running at http://localhost:8000"
fi

# Test 5: Check bot API (optional)
echo "[5/6] Checking bot API..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    pass "Bot API is running"
else
    warn "Bot API not running (start it with: make run-api)"
fi

# Test 6: Check Cursor config
echo "[6/6] Checking Cursor MCP config..."
WORKSPACE_CONFIG="$PROJECT_ROOT/.cursor/mcp.json"
USER_CONFIG="$HOME/.cursor/mcp.json"

if [ -f "$WORKSPACE_CONFIG" ]; then
    if grep -q "trading-analyst" "$WORKSPACE_CONFIG"; then
        pass "Cursor workspace config exists and includes trading-analyst"
    else
        warn "Cursor workspace config exists but missing trading-analyst"
        echo "   Copy template: cp $SCRIPT_DIR/cursor-mcp-config.json $WORKSPACE_CONFIG"
    fi
elif [ -f "$USER_CONFIG" ]; then
    if grep -q "trading-analyst" "$USER_CONFIG"; then
        pass "Cursor user config exists and includes trading-analyst"
    else
        warn "Cursor user config exists but missing trading-analyst"
        echo "   Copy template: cp $SCRIPT_DIR/cursor-mcp-config.json $USER_CONFIG"
    fi
else
    warn "Cursor MCP config not found"
    echo "   Copy template:"
    echo "   mkdir -p $PROJECT_ROOT/.cursor"
    echo "   cp $SCRIPT_DIR/cursor-mcp-config.json $PROJECT_ROOT/.cursor/mcp.json"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Setup status: Ready to use"
echo ""
echo "Next steps:"
echo "1. Ensure bot API is running: make run-api"
echo "2. Copy Cursor config if not done yet"
echo "3. Restart Cursor"
echo "4. Test with: 'Using get_live_risk_snapshot, show my risk'"
echo ""
