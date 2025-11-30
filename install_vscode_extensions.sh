#!/bin/bash

# Install VS Code Extensions for Claude Code + Kite MCP Integration
# This script installs the required extensions to connect Claude Code to Kite MCP

set -e

echo "🚀 Installing VS Code Extensions for Claude Code + Kite MCP Integration"
echo ""

# Check if 'code' command is available
if ! command -v code &> /dev/null; then
    echo "❌ Error: 'code' command not found in PATH"
    echo ""
    echo "To fix this, add VS Code to your PATH:"
    echo "1. Open VS Code"
    echo "2. Press Cmd+Shift+P (macOS) or Ctrl+Shift+P (Windows/Linux)"
    echo "3. Type 'Shell Command: Install code command in PATH'"
    echo "4. Select it and restart your terminal"
    echo ""
    echo "Alternatively, you can install extensions manually:"
    echo "1. Open VS Code"
    echo "2. Go to Extensions (Cmd+Shift+X / Ctrl+Shift+X)"
    echo "3. Search and install:"
    echo "   - 'Claude Code' (by Anthropic)"
    echo "   - 'VSCode MCP Bridge' (by YuTengjing)"
    exit 1
fi

echo "✅ Found 'code' command"
echo ""

# Extension IDs
CLAUDE_CODE_EXT="anthropic.claude-code"
MCP_BRIDGE_EXT="YuTengjing.vscode-mcp-bridge"

echo "📦 Installing extensions..."
echo ""

# Install Claude Code extension
echo "1️⃣ Installing Claude Code extension..."
if code --install-extension "$CLAUDE_CODE_EXT" --force; then
    echo "   ✅ Claude Code installed"
else
    echo "   ⚠️  Failed to install Claude Code (may already be installed)"
fi
echo ""

# Install VSCode MCP Bridge extension
echo "2️⃣ Installing VSCode MCP Bridge extension..."
if code --install-extension "$MCP_BRIDGE_EXT" --force; then
    echo "   ✅ VSCode MCP Bridge installed"
else
    echo "   ⚠️  Failed to install VSCode MCP Bridge (may already be installed)"
fi
echo ""

echo "✅ Extension installation complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Reload VS Code window (Cmd+Shift+P → 'Reload Window')"
echo "2. Open Claude Code panel (click the Spark icon in sidebar)"
echo "3. Verify MCP connection by asking: 'What MCP servers are connected?'"
echo ""
echo "🔧 Current MCP Configuration:"
echo "   Server: kite"
echo "   URL: http://localhost:8081/mcp"
echo "   Transport: http"
echo ""
echo "🧪 Test the connection:"
echo "   Ask Claude Code: 'Get the current quote for RELIANCE'"
echo ""



