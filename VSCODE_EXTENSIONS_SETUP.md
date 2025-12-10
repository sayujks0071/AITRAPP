# VS Code Extensions Setup for Claude Code + Kite MCP

This guide helps you install the required VS Code extensions to connect Claude Code to the Kite MCP server.

## Required Extensions

1. **Claude Code** - The main Claude AI assistant extension for VS Code
   - Extension ID: `anthropic.claude-code`
   - Publisher: Anthropic

2. **VSCode MCP Bridge** - Enables Model Context Protocol (MCP) support in VS Code
   - Extension ID: `YuTengjing.vscode-mcp-bridge`
   - Publisher: YuTengjing

## Installation Methods

### Method 1: Automated Script (Recommended)

Run the installation script:

```bash
cd /Users/mac/CRYPTO/AITRAPP
./install_vscode_extensions.sh
```

**Note**: If you get an error about `code` command not found, see "Adding VS Code to PATH" below.

### Method 2: Manual Installation via VS Code UI

1. **Open VS Code**
2. **Open Extensions View**:
   - Click the Extensions icon in the Activity Bar (left sidebar)
   - Or press `Cmd+Shift+X` (macOS) / `Ctrl+Shift+X` (Windows/Linux)

3. **Install Claude Code**:
   - Search for: `Claude Code`
   - Look for the extension by **Anthropic**
   - Click **Install**

4. **Install VSCode MCP Bridge**:
   - Search for: `VSCode MCP Bridge`
   - Look for the extension by **YuTengjing**
   - Click **Install**

### Method 3: Command Line (if `code` is in PATH)

```bash
# Install Claude Code
code --install-extension anthropic.claude-code

# Install VSCode MCP Bridge
code --install-extension YuTengjing.vscode-mcp-bridge
```

## Adding VS Code to PATH

If the `code` command is not available:

1. **Open VS Code**
2. **Open Command Palette**:
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
3. **Install Shell Command**:
   - Type: `Shell Command: Install 'code' command in PATH`
   - Select it and press Enter
4. **Restart Terminal**:
   - Close and reopen your terminal
   - Verify: `code --version`

## Verify Installation

After installing the extensions:

1. **Reload VS Code**:
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
   - Type: `Developer: Reload Window`
   - Press Enter

2. **Check Extensions**:
   - Go to Extensions view (`Cmd+Shift+X`)
   - Search for "Claude Code" - should show "Installed"
   - Search for "VSCode MCP Bridge" - should show "Installed"

3. **Verify MCP Configuration**:
   - Your `.vscode/settings.json` already has the Kite MCP server configured:
   ```json
   {
     "claudeCode.mcpServers": {
       "kite": {
         "transport": "http",
         "url": "http://localhost:8081/mcp",
         "description": "Zerodha Kite Connect API - Market data, portfolio, and orders (read-only mode)"
       }
     }
   }
   ```

## Testing the Connection

1. **Open Claude Code**:
   - Click the **Spark icon** (✨) in the VS Code sidebar
   - Or press `Cmd+Shift+P` and type "Claude Code"

2. **Test MCP Connection**:
   ```
   What MCP servers are currently connected?
   ```
   
   Expected response should mention the "kite" server.

3. **Test Kite MCP Tools**:
   ```
   Get the current quote for RELIANCE
   ```
   
   Or:
   ```
   Show me my current holdings
   ```

## Troubleshooting

### Extensions Not Installing

- **Check VS Code Version**: Ensure you're using a recent version of VS Code
- **Check Internet Connection**: Extensions are downloaded from the marketplace
- **Try Manual Installation**: Use Method 2 (UI) if command line fails

### MCP Server Not Connecting

1. **Verify Server is Running**:
   ```bash
   curl http://localhost:8081/
   ```
   Should return a status response.

2. **Check VS Code Settings**:
   - Open `.vscode/settings.json`
   - Verify the MCP server configuration is correct
   - No JSON syntax errors

3. **Reload VS Code**:
   - Sometimes a full restart is needed (quit and reopen VS Code)

### "Claude Code" Panel Not Showing

- Look for the **Spark icon** (✨) in the left sidebar
- If not visible, the extension may not be installed correctly
- Try reinstalling the extension

### MCP Tools Not Available

- Ensure the Kite MCP server is running on port 8081
- Check server logs: `tail -f kite-mcp-server/mcp-server.log`
- Verify the URL in settings matches the server URL

## Current Configuration

Your workspace is already configured with:

- **MCP Server**: `kite`
- **Transport**: `http`
- **URL**: `http://localhost:8081/mcp`
- **Mode**: Read-only (16 safe tools)

## Next Steps

After successful installation:

1. ✅ Extensions installed
2. ✅ MCP server configured (already done)
3. ⏳ Reload VS Code window
4. ⏳ Test connection with Claude Code
5. ⏳ Start using Kite MCP tools!

## Related Documentation

- [KITE_MCP_VSCODE_SETUP.md](KITE_MCP_VSCODE_SETUP.md) - Detailed MCP setup guide
- [CLAUDE_MCP_SETUP.md](CLAUDE_MCP_SETUP.md) - Claude Desktop setup (different from VS Code)
- [CONNECT_MCP_TO_CLAUDE.md](CONNECT_MCP_TO_CLAUDE.md) - CLI-based connection guide

---

**Ready to go!** Install the extensions and start using Claude Code with Kite MCP! 🚀



