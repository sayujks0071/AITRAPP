# Trading Analyst MCP - Pre-Flight Checklist

Run through this checklist **before** installing the MCP server to ensure smooth setup.

---

## ✅ Pre-Flight Checklist

### 1. Node.js & Python Versions

**Node.js:**
```bash
node --version
# Should be ≥ 18.x
```

**Python:**
```bash
python3 --version
# Should match what your AITRAPP bot uses (3.10 or 3.11 recommended)
```

---

### 2. Bot API Running

Your FastAPI app needs to be running and accessible:

```bash
# Start bot API (if not already running)
make run-api
# OR
python -m apps.api.main

# Test endpoints that MCP will use
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/risk/greeks
curl -s http://localhost:8000/api/strategies/summary
```

**Expected:** JSON responses, not 404/500 errors.

**If bot API is not running:**
- MCP server will still install, but tools will return placeholder data
- You'll see warnings like "Bot API not available"

---

### 3. Kite Client Configured

**Check environment variables:**
```bash
cat .env | grep KITE
```

**Expected:**
```
KITE_API_KEY=your_api_key
KITE_ACCESS_TOKEN=your_access_token
KITE_USER_ID=your_user_id
```

**Test Kite connection:**
```bash
# If your bot can connect to Kite, MCP will too
python3 -c "
from packages.exchanges.kite_client import get_kite_client
from packages.core.config import load_config
kite = get_kite_client(load_config())
print(kite.margins())
"
```

**If Kite token expired:**
```bash
python scripts/kite_token_refresh.py
```

---

### 4. Python Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies MCP adapter needs:**
- `requests` (for calling bot API)
- `kiteconnect` (for Kite API)
- Your `packages/` modules (core, exchanges)

---

### 5. Disk Space & Permissions

**Check build directory permissions:**
```bash
# Should be writable
ls -la mcp-servers/trading-analyst/
```

**Ensure you can create files:**
```bash
touch mcp-servers/trading-analyst/test_write && rm mcp-servers/trading-analyst/test_write
```

---

## 🚀 Installation

Once all checks pass, run:

```bash
cd mcp-servers/trading-analyst
./install.sh
```

**What it does:**
1. Installs Node.js dependencies (`npm install`)
2. Builds TypeScript (`npm run build`)
3. Makes Python adapter executable
4. Tests Python adapter
5. Generates Cursor MCP config

---

## 🧪 Verify Installation

After `./install.sh` completes, run:

```bash
./test.sh
```

**Expected output:**
```
✓ Node.js dependencies installed
✓ TypeScript build exists
✓ Python adapter is executable
✓ Python adapter runs successfully
✓ Bot API is running
✓ Cursor workspace config exists and includes trading-analyst
```

---

## 📋 Configure Cursor

### Option A: Workspace-level (Recommended)

```bash
mkdir -p .cursor
cp mcp-servers/trading-analyst/cursor-mcp-config.json .cursor/mcp.json
```

**Why workspace-level?**
- Only affects this project
- Easier to version control
- Won't interfere with other Cursor projects

### Option B: User-level (All projects)

```bash
mkdir -p ~/.cursor
cp mcp-servers/trading-analyst/cursor-mcp-config.json ~/.cursor/mcp.json
```

**Why user-level?**
- Available in all Cursor workspaces
- Good if you want trading analyst everywhere

---

## 🔄 Restart Cursor

**Important:** You MUST restart Cursor after updating MCP config.

**Not enough:**
- ❌ Reload window (Cmd+R)
- ❌ Reload extensions

**Required:**
- ✅ Quit Cursor completely (Cmd+Q)
- ✅ Reopen Cursor

---

## 🎯 First Test

Open Cursor and type in chat:

```
Using get_live_risk_snapshot, show me my current risk state.
```

**Expected:**
- Tool call to `get_live_risk_snapshot`
- JSON response with greeks, margin, tail coverage
- Natural language summary from Cursor

**If it works:** ✅ You're ready to use!

**If it doesn't work:** See troubleshooting below.

---

## 🔧 Troubleshooting

### "MCP server not showing up in Cursor"

**Check 1: Config location**
```bash
# Workspace config
cat .cursor/mcp.json

# OR user config
cat ~/.cursor/mcp.json
```

**Check 2: Config syntax**
```bash
# Should be valid JSON
python3 -c "import json; json.load(open('.cursor/mcp.json'))"
```

**Check 3: Cursor logs**
- View → Output → Select "MCP" from dropdown
- Look for "trading-analyst" server startup messages

---

### "Python adapter failed"

**Test adapter directly:**
```bash
python3 mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}'
```

**Common issues:**
1. **Bot API not running** → Start with `make run-api`
2. **Import errors** → Run `pip install -r requirements.txt`
3. **Kite token expired** → Run `python scripts/kite_token_refresh.py`

---

### "Tool returns placeholder data"

This means bot API endpoints are returning errors or empty data.

**Check endpoints:**
```bash
# Should return real data, not errors
curl http://localhost:8000/api/risk/greeks
curl http://localhost:8000/api/strategies/summary
curl http://localhost:8000/api/regime/current
```

**If endpoints return errors:**
1. Check bot logs for exceptions
2. Ensure orchestrator is initialized
3. Ensure strategies are loaded

---

### "Kite client errors"

**Error: "Invalid token"**
```bash
python scripts/kite_token_refresh.py
```

**Error: "Too many requests"**
- Kite has rate limits (3 req/sec)
- MCP adapter caches data to avoid hitting limits
- Wait 60 seconds and retry

**Error: "Connection refused"**
- Kite API might be down
- Check https://kite.trade/status

---

## 📊 Health Check Script

Quick script to verify everything is working:

```bash
#!/bin/bash
echo "=== Trading Analyst MCP Health Check ==="
echo ""

# 1. Bot API
echo -n "Bot API: "
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✓ Running"
else
    echo "✗ Not running"
fi

# 2. MCP Server Build
echo -n "MCP Server Build: "
if [ -f mcp-servers/trading-analyst/build/index.js ]; then
    echo "✓ Exists"
else
    echo "✗ Missing"
fi

# 3. Python Adapter
echo -n "Python Adapter: "
if python3 mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}' > /dev/null 2>&1; then
    echo "✓ Working"
else
    echo "✗ Failed"
fi

# 4. Cursor Config
echo -n "Cursor Config: "
if [ -f .cursor/mcp.json ] || [ -f ~/.cursor/mcp.json ]; then
    echo "✓ Exists"
else
    echo "✗ Missing"
fi

echo ""
echo "=== End Health Check ==="
```

Save as `scripts/mcp_health_check.sh` and run before each session.

---

## 🎓 What's Next?

Once pre-flight passes and installation succeeds:

1. **Read**: [docs/MCP_ANALYST_QUICK_START.md](../../docs/MCP_ANALYST_QUICK_START.md)
2. **Try**: First-use prompts in [FIRST_USE_PROMPTS.md](FIRST_USE_PROMPTS.md)
3. **Integrate**: Add to your daily workflow

---

## 📞 Support

If pre-flight checks fail and you can't resolve:

1. Check bot logs: `tail -f logs/api.log`
2. Check MCP logs: Cursor → View → Output → MCP
3. Test components individually (see troubleshooting)

Most issues are:
- Bot API not running (80%)
- Kite token expired (15%)
- Config typo (5%)
