#!/bin/bash
#
# Install and configure Trading Analyst MCP server for Cursor
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=========================================="
echo "Trading Analyst MCP Server Setup"
echo "=========================================="
echo ""

# 1. Install Node.js dependencies
echo "[1/5] Installing Node.js dependencies..."
cd "$SCRIPT_DIR"
npm install

# 2. Build TypeScript
echo "[2/5] Building TypeScript..."
npm run build

# 3. Make Python adapter executable
echo "[3/5] Making Python adapter executable..."
chmod +x "$PROJECT_ROOT/mcp-adapters/trading_analyst_adapter.py"

# 4. Test Python adapter
echo "[4/5] Testing Python adapter..."
python3 "$PROJECT_ROOT/mcp-adapters/trading_analyst_adapter.py" get_live_risk_snapshot '{}' > /dev/null 2>&1 || {
    echo "⚠️  Warning: Python adapter test failed. Make sure your bot dependencies are installed:"
    echo "    pip install -r $PROJECT_ROOT/requirements.txt"
}

# 5. Generate Cursor MCP config
echo "[5/5] Generating Cursor MCP config..."

# Get absolute path for config
MCP_SERVER_PATH="$SCRIPT_DIR/build/index.js"

# Create Cursor MCP config
cat > "$SCRIPT_DIR/cursor-mcp-config.json" <<EOF
{
  "mcpServers": {
    "trading-analyst": {
      "command": "node",
      "args": [
        "$MCP_SERVER_PATH"
      ],
      "env": {
        "BOT_API_URL": "http://localhost:8000",
        "NODE_ENV": "production"
      },
      "disabled": false
    }
  }
}
EOF

echo ""
echo "✅ Installation complete!"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Copy MCP config to Cursor settings:"
echo ""
echo "   Option A (Workspace-level - Recommended):"
echo "   cp $SCRIPT_DIR/cursor-mcp-config.json $PROJECT_ROOT/.cursor/mcp.json"
echo ""
echo "   Option B (User-level - All Cursor projects):"
echo "   mkdir -p ~/.cursor"
echo "   cp $SCRIPT_DIR/cursor-mcp-config.json ~/.cursor/mcp.json"
echo ""
echo "2. Restart Cursor for changes to take effect"
echo ""
echo "3. Test by opening Cursor and typing:"
echo "   'Using get_live_risk_snapshot, show me my current risk state'"
echo ""
echo "=========================================="
echo "Troubleshooting:"
echo "=========================================="
echo ""
echo "If the MCP server doesn't work:"
echo ""
echo "1. Ensure bot API is running:"
echo "   curl http://localhost:8000/health"
echo ""
echo "2. Test Python adapter directly:"
echo "   python3 $PROJECT_ROOT/mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}'"
echo ""
echo "3. Check Cursor logs (View → Output → MCP)"
echo ""
