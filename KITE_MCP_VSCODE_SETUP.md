# Connecting Kite MCP Server to Claude Code (VSCode Extension)

Since you're using the **Claude Code VSCode Extension**, the MCP server needs to be configured through VSCode settings, not the CLI.

---

## ✅ Server Status

The Kite MCP Server is **already running** and ready to connect:
- **URL:** http://localhost:8081/mcp
- **Mode:** Read-only (16 safe tools)
- **Status:** Active

---

## 🔌 Connection Methods

### Method 1: VSCode Settings UI (Recommended)

1. **Open VSCode Settings:**
   - Press `Cmd+,` (macOS) or `Ctrl+,` (Windows/Linux)
   - Or go to: `Code` → `Settings` → `Settings`

2. **Search for "Claude Code MCP":**
   - Type "mcp" in the search box
   - Look for **"Claude Code: MCP Servers"**

3. **Add Server Configuration:**
   - Click "Edit in settings.json"
   - Add the following configuration:

   ```json
   {
     "claudeCode.mcpServers": {
       "kite": {
         "transport": "http",
         "url": "http://localhost:8081/mcp"
       }
     }
   }
   ```

4. **Reload VSCode:**
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Reload Window" and press Enter

---

### Method 2: Edit settings.json Directly

1. **Open Command Palette:**
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)

2. **Open User Settings (JSON):**
   - Type: `Preferences: Open User Settings (JSON)`
   - Press Enter

3. **Add MCP Configuration:**
   ```json
   {
     // ... your existing settings ...

     "claudeCode.mcpServers": {
       "kite": {
         "transport": "http",
         "url": "http://localhost:8081/mcp",
         "description": "Kite Connect API - Market data & portfolio (read-only)"
       }
     }
   }
   ```

4. **Save and Reload:**
   - Save the file (`Cmd+S` / `Ctrl+S`)
   - Reload VSCode window

---

### Method 3: Workspace Settings (Project-Specific)

If you want the MCP server only for this project:

1. **Create `.vscode/settings.json`:**
   ```bash
   mkdir -p /Users/mac/CRYPTO/AITRAPP/.vscode
   ```

2. **Add configuration:**
   ```json
   {
     "claudeCode.mcpServers": {
       "kite": {
         "transport": "http",
         "url": "http://localhost:8081/mcp",
         "description": "Kite Connect - Read-only market data"
       }
     }
   }
   ```

3. **Reload VSCode**

---

## 🧪 Testing the Connection

After configuring and reloading VSCode:

1. **Open a new Claude Code chat**

2. **Test with a simple query:**
   ```
   Using the Kite MCP server, get the current quote for RELIANCE
   ```

3. **I should respond with:**
   - Real-time quote data from Kite API
   - Confirmation that the MCP tool was used

4. **Check available tools:**
   ```
   List all available Kite MCP tools
   ```

---

## 🔍 Verifying Connection

### Check if MCP Server is Recognized

In Claude Code chat, ask:
```
What MCP servers are currently connected?
```

I should list:
- **kite** - Kite Connect API server at http://localhost:8081/mcp

### Test Individual Tools

Try these queries:
```
1. Get my Kite profile information
2. Show my current holdings
3. What are my account margins?
4. Search for NIFTY options
```

---

## ⚠️ Troubleshooting

### MCP Server Not Showing Up

**Check 1: Server is Running**
```bash
lsof -i :8081
ps aux | grep kite-mcp.bin
```

**Check 2: VSCode Settings**
- Open settings.json
- Verify the configuration is correct
- No syntax errors (trailing commas, missing brackets)

**Check 3: Reload VSCode**
- Sometimes VSCode needs a full restart
- Close and reopen VSCode completely

### Connection Errors

**Server logs:**
```bash
tail -f /Users/mac/CRYPTO/AITRAPP/kite-mcp-server/mcp-server.log
```

**Test endpoint directly:**
```bash
curl http://localhost:8081/
```
Should return the Kite MCP status page.

### Settings Not Taking Effect

1. **Check settings precedence:**
   - User settings (global)
   - Workspace settings (project-specific)
   - Workspace settings override user settings

2. **Restart VSCode completely:**
   - Don't just reload window
   - Quit VSCode and reopen

---

## 📋 Complete Settings Example

Here's a complete `settings.json` with the Kite MCP server:

```json
{
  // Claude Code MCP Servers
  "claudeCode.mcpServers": {
    "kite": {
      "transport": "http",
      "url": "http://localhost:8081/mcp",
      "description": "Zerodha Kite Connect API - Market data, portfolio, and orders (read-only mode)",
      "enabled": true
    }
  },

  // Other VSCode settings...
  "editor.fontSize": 14,
  "workbench.colorTheme": "Dark+"
}
```

---

## 🎯 What You Can Do After Connecting

### Market Data Queries
- "What's the current price of RELIANCE?"
- "Show me NIFTY 50 quotes"
- "Get OHLC data for SBIN"
- "Search for Bank Nifty options expiring next week"

### Portfolio Management
- "Show my current positions"
- "What are my holdings?"
- "Check my account margins"
- "List today's orders"

### Analysis Requests
- "Analyze the options chain for NIFTY"
- "Find the most liquid BANKNIFTY options"
- "What's my portfolio's delta exposure?"
- "Suggest iron condor strikes for NIFTY"

---

## 🔄 Managing the Server

### Keep Server Running in Background

**Option 1: Terminal Window**
```bash
cd /Users/mac/CRYPTO/AITRAPP/kite-mcp-server
bash start-readonly.sh
# Keep this terminal open
```

**Option 2: Background Process**
```bash
cd /Users/mac/CRYPTO/AITRAPP/kite-mcp-server
nohup bash start-readonly.sh > mcp-server.log 2>&1 &
echo $! > mcp-server.pid
```

**Stop Background Process:**
```bash
kill $(cat /Users/mac/CRYPTO/AITRAPP/kite-mcp-server/mcp-server.pid)
```

### Automatic Startup (Optional)

Create a LaunchAgent to start the server automatically on login:

```bash
# Create LaunchAgent directory if needed
mkdir -p ~/Library/LaunchAgents

# Create plist file
cat > ~/Library/LaunchAgents/com.kite.mcpserver.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kite.mcpserver</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/mac/CRYPTO/AITRAPP/kite-mcp-server/start-readonly.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/mac/CRYPTO/AITRAPP/kite-mcp-server/mcp-server.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mac/CRYPTO/AITRAPP/kite-mcp-server/mcp-server-error.log</string>
</dict>
</plist>
EOF

# Load the LaunchAgent
launchctl load ~/Library/LaunchAgents/com.kite.mcpserver.plist
```

**Unload (disable auto-start):**
```bash
launchctl unload ~/Library/LaunchAgents/com.kite.mcpserver.plist
```

---

## 📚 Related Documentation

- [KITE_MCP_INSTALLATION_SUMMARY.md](KITE_MCP_INSTALLATION_SUMMARY.md) - Installation guide
- [SETUP_KITE_MCP.md](SETUP_KITE_MCP.md) - Original setup instructions
- [docs/KITE_MCP_INTEGRATION.md](docs/KITE_MCP_INTEGRATION.md) - Integration details

---

## 🎉 Next Steps

1. ✅ Server is running on port 8081
2. ⏳ **Add MCP configuration to VSCode settings** (follow Method 1 or 2 above)
3. ⏳ **Reload VSCode window**
4. ⏳ **Test the connection** with a market data query
5. ⏳ **Start using AI-powered market insights!**

---

*The Kite MCP Server is ready - just add the configuration to VSCode and you're all set!* 🚀
