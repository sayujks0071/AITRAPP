#!/bin/bash
# Setup Claude Desktop MCP configuration

CONFIG_FILE="$HOME/Library/Application Support/Claude/config.json"
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "🔧 Setting up Claude Desktop MCP Configuration"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    echo "   Make sure Claude Desktop is installed"
    exit 1
fi

# Backup current config
echo "📦 Backing up current config..."
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "   Backup saved to: $BACKUP_FILE"
echo ""

# Check if mcpServers already exists
if grep -q '"mcpServers"' "$CONFIG_FILE"; then
    echo "⚠️  MCP servers already configured in config file"
    echo "   Current config:"
    cat "$CONFIG_FILE" | python3 -m json.tool 2>/dev/null | grep -A 10 "mcpServers" || cat "$CONFIG_FILE"
    echo ""
    read -p "Do you want to add Kite MCP server? (y/n): " answer
    if [ "$answer" != "y" ]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo "📝 Adding Kite MCP server configuration..."
echo ""

# Create Python script to update JSON
python3 << 'PYTHON_SCRIPT'
import json
import sys
import os

config_file = os.path.expanduser("~/Library/Application Support/Claude/config.json")

try:
    # Read current config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Initialize mcpServers if not exists
    if 'mcpServers' not in config:
        config['mcpServers'] = {}
    
    # Add Kite MCP server
    print("Choose MCP server option:")
    print("1. Local server (http://localhost:8080/mcp) - requires server running")
    print("2. Hosted server (https://mcp.kite.trade/mcp) - no local server needed")
    print()
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        # Local server
        config['mcpServers']['kite'] = {
            "command": "npx",
            "args": [
                "mcp-remote",
                "http://localhost:8080/mcp",
                "--allow-http"
            ],
            "env": {
                "KITE_API_KEY": "nhe2vo0afks02ojs",
                "KITE_API_SECRET": "cs82nkkdvin37nrydnyou6cwn2b8zojl"
            }
        }
        print("✅ Configured for LOCAL server")
    elif choice == "2":
        # Hosted server
        config['mcpServers']['kite'] = {
            "command": "npx",
            "args": [
                "mcp-remote",
                "https://mcp.kite.trade/mcp"
            ]
        }
        print("✅ Configured for HOSTED server")
    else:
        print("❌ Invalid choice")
        sys.exit(1)
    
    # Write updated config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent='\t')
    
    print("✅ Configuration updated successfully!")
    print()
    print("📋 Updated config:")
    print(json.dumps(config['mcpServers'], indent=2))
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Restart Claude Desktop (required!)"
    echo "   2. In Claude, ask: 'What MCP tools are available?'"
    echo "   3. Try: 'Get NIFTY quote'"
    echo ""
    echo "💡 To view current config:"
    echo "   cat ~/Library/Application\\ Support/Claude/config.json | python3 -m json.tool"
else
    echo ""
    echo "❌ Setup failed. Config backup saved to: $BACKUP_FILE"
    exit 1
fi

