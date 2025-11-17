# Trading Analyst MCP Server - Implementation Summary

## What We Built

A **streamlined, read-only MCP server** that acts as a **senior analyst + risk officer** for your AITRAPP trading stack.

Instead of exposing 15+ low-level Kite API tools, we created **5 high-level analysis tools** that return pre-digested views.

---

## Architecture

```
┌─────────────────────┐
│      Cursor         │  ← You interact here
│    (AI Brain)       │
└──────────┬──────────┘
           │
           │ MCP Protocol (stdio)
           │
┌──────────▼──────────────────────┐
│  Trading Analyst MCP Server     │
│  (TypeScript, Node.js)          │
│                                 │
│  Tools:                         │
│  1. get_live_risk_snapshot      │
│  2. get_strategy_summary        │
│  3. get_broker_vs_algo_recon    │
│  4. get_event_and_regime_context│
│  5. propose_config_tweaks       │
│                                 │
│  ✅ Read-only                   │
│  ✅ No trading actions          │
│  ✅ Human-in-loop               │
└──────────┬──────────────────────┘
           │
           │ subprocess (python3)
           │
┌──────────▼──────────────────────┐
│  Python Adapter                 │
│  (trading_analyst_adapter.py)  │
│                                 │
│  Aggregates + normalizes data   │
│  from:                          │
│  - FastAPI bot (/api/*)         │
│  - Kite (via kite_client.py)   │
└───────┬──────────────┬──────────┘
        │              │
   ┌────▼────┐    ┌───▼────┐
   │ Bot API │    │  Kite  │
   │ :8000   │    │  API   │
   └─────────┘    └────────┘
```

---

## Files Created

### 1. MCP Server (TypeScript)
- `mcp-servers/trading-analyst/package.json` - Node.js dependencies
- `mcp-servers/trading-analyst/tsconfig.json` - TypeScript config
- `mcp-servers/trading-analyst/src/index.ts` - Main MCP server with 5 tools
- `mcp-servers/trading-analyst/cursor-mcp-config.json` - Cursor config template
- `mcp-servers/trading-analyst/install.sh` - One-command installation script
- `mcp-servers/trading-analyst/README.md` - Full documentation

### 2. Python Adapter
- `mcp-adapters/trading_analyst_adapter.py` - Fetches + aggregates data from bot + Kite

### 3. FastAPI Endpoints (New)
- `apps/api/routes/mcp_analyst.py` - 8 new endpoints for MCP tools:
  - `/api/risk/greeks` - Portfolio-level greeks
  - `/api/risk/short_premium` - Short option exposure
  - `/api/risk/tail_coverage` - Tail hedge coverage %
  - `/api/strategies/summary` - Per-strategy performance
  - `/api/regime/current` - R1 regime classification
  - `/api/events/today` - E1 event context
  - `/api/report/today` - Daily report JSON

### 4. Documentation
- `docs/MCP_ANALYST_QUICK_START.md` - Daily workflow guide with example prompts

---

## The 5 Tools

### 1. `get_live_risk_snapshot`
**What it returns:**
- Portfolio greeks (delta/gamma/vega/theta)
- Margin: used, available, utilization %
- Short premium by underlying
- Tail coverage %
- Risk flags (MARGIN_OK, TAIL_COVERAGE_LOW, etc.)

**Example use:**
> "Using get_live_risk_snapshot, tell me if margin > 70% or tail coverage < 10%"

---

### 2. `get_strategy_summary`
**What it returns:**
- Per-strategy PnL (realised + unrealised)
- Hit rate over lookback window
- Max drawdown
- Current allocation %
- Regime usage

**Example use:**
> "Using get_strategy_summary, which strategies should get more/less capital?"

---

### 3. `get_broker_vs_algo_reconciliation`
**What it returns:**
- Orphan positions (on Kite but not in bot)
- Ghost positions (in bot but not on Kite)
- Quantity mismatches
- Status: OK / MISMATCH_DETECTED

**Example use:**
> "Using get_broker_vs_algo_reconciliation, check for state drift"

---

### 4. `get_event_and_regime_context`
**What it returns:**
- R1 regime (LOW/MEDIUM/HIGH) per underlying
- IV rank, ATR%, RV/IV
- E1 event day type (NORMAL/PRE_EVENT/EVENT_DAY/POST_EVENT)
- Event name + severity

**Example use:**
> "Using get_event_and_regime_context, explain today's environment"

---

### 5. `propose_config_tweaks`
**What it returns:**
- Allocator weight change suggestions
- Regime band edit suggestions
- Strategy param edit suggestions
- All with reasoning

**Example use:**
> "Using propose_config_tweaks, suggest allocator changes based on last 30 days"

---

## Safety Model

### What MCP Does
✅ Reads data from bot + Kite
✅ Aggregates + analyzes
✅ Flags issues
✅ Suggests config changes
✅ Explains context

### What MCP Does NOT Do
❌ Place orders
❌ Modify positions
❌ Change config files
❌ Execute any trading actions

**You** review all suggestions and apply manually.

---

## Installation

```bash
# 1. Install and build MCP server
cd mcp-servers/trading-analyst
./install.sh

# 2. Copy config to Cursor
mkdir -p .cursor
cp mcp-servers/trading-analyst/cursor-mcp-config.json .cursor/mcp.json

# 3. Restart Cursor
```

---

## Daily Workflow Example

### Pre-open (9:00 AM)
```
Call get_broker_vs_algo_reconciliation and get_live_risk_snapshot.

Confirm I'm flat, margin OK, and no orphans. Give me a GO/NO-GO
for starting LIVE.
```

### Intraday (Every 30 min)
```
Using get_live_risk_snapshot, check if:
- margin > 70%
- net delta > |15|
- tail coverage < 10%

Flag any breaches.
```

### Post-close (3:45 PM)
```
Use get_strategy_summary and get_event_and_regime_context.
Give me a mini PM note: which strategies made/lost money, whether
that matches the regime, and any red flags.
```

### Weekly (Friday EOD)
```
Using propose_config_tweaks with 30-day window, suggest allocator
weight changes. I'll review and apply manually.
```

---

## Why This Design?

### Problem: Raw MCP Tools
If we exposed raw Kite API tools, you'd need to:
1. Call `get_positions()`
2. Call `get_margins()`
3. Call `get_orders()`
4. Calculate greeks manually
5. Aggregate across underlyings
6. Compute risk flags
7. Format for decision-making

**10+ tool calls** for a single risk snapshot.

### Solution: High-Level Analysis Tools
One tool call → complete view:
```
get_live_risk_snapshot() → {
  portfolio greeks,
  margin usage,
  short premium,
  tail coverage,
  risk flags
}
```

**1 tool call** → actionable insight.

---

## Next Steps

### Immediate (to use it)
1. Run `cd mcp-servers/trading-analyst && ./install.sh`
2. Copy config to Cursor
3. Restart Cursor
4. Test: "Using get_live_risk_snapshot, show me my current risk"

### Short-term enhancements
1. **Add real greeks calculation** - Currently placeholder in `/api/risk/greeks`
2. **Wire up position store** - Use H1's position_store for tail coverage
3. **Add historical data** - Store daily snapshots for trend analysis

### Medium-term extensions
1. **Add tool 6: `get_intraday_pnl_curve`** - PnL every 5 minutes
2. **Add tool 7: `get_regime_transition_alerts`** - Warn before regime shifts
3. **Integrate with Grafana alerts** - MCP responds to Prometheus alerts

### Advanced (after battle-testing)
1. **Auto-generate daily reports** - Call MCP tools on schedule
2. **Connect to WhatsApp** - Send key metrics to your phone
3. **Build custom Cursor slash commands** - `/risk-check`, `/eod-summary`

---

## Comparison: Before vs After

### Before (Raw API approach)
```
You: "What's my current risk?"

Cursor calls:
1. get_positions() → 15 items
2. get_margins() → raw JSON
3. get_orders() → 30 items
4. manually calculate net delta
5. manually calculate short premium
6. manually calculate tail coverage
7. format into readable summary

Result: 7 tool calls, ~30 seconds, hard to interpret
```

### After (Analyst MCP)
```
You: "What's my current risk?"

Cursor calls:
1. get_live_risk_snapshot()

Result: 1 tool call, ~2 seconds, pre-formatted with flags
```

---

## Success Metrics

After using this for 1 week, you should see:

1. **Faster decisions** - Pre-open check goes from 5 min → 30 sec
2. **Fewer misses** - Reconciliation catches orphan positions before they're a problem
3. **Better allocation** - Weekly reviews lead to data-driven weight changes
4. **Clearer context** - You know *why* strategies are working/not working (regime alignment)

---

## Troubleshooting

### "MCP server not showing up in Cursor"
1. Check config location: `.cursor/mcp.json` or `~/.cursor/mcp.json`
2. Restart Cursor (quit + reopen, not just reload window)
3. Check Cursor logs: View → Output → MCP

### "Python adapter failed"
1. Make sure bot API is running: `curl http://localhost:8000/health`
2. Test adapter directly: `python3 mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}'`
3. Check dependencies: `pip install -r requirements.txt`

### "Kite client errors"
1. Refresh token: `python scripts/kite_token_refresh.py`
2. Check `.env` has valid `KITE_ACCESS_TOKEN`

---

## Files Summary

```
AITRAPP/
├── mcp-servers/
│   └── trading-analyst/
│       ├── src/index.ts              ← MCP server (5 tools)
│       ├── package.json
│       ├── tsconfig.json
│       ├── install.sh                ← One-command setup
│       ├── cursor-mcp-config.json    ← Cursor config template
│       └── README.md                 ← Full docs
│
├── mcp-adapters/
│   └── trading_analyst_adapter.py    ← Python data aggregator
│
├── apps/api/routes/
│   └── mcp_analyst.py                ← 8 new FastAPI endpoints
│
└── docs/
    └── MCP_ANALYST_QUICK_START.md    ← Daily workflow guide
```

---

## Credits

Design philosophy: **"Not a second trading engine, but a decision + analysis brain"**

Inspired by the principle of **high-level abstraction over raw API access**.

Built for **human-in-loop decision support**, not autonomous trading.

---

## Support

- Full docs: [mcp-servers/trading-analyst/README.md](mcp-servers/trading-analyst/README.md)
- Quick start: [docs/MCP_ANALYST_QUICK_START.md](docs/MCP_ANALYST_QUICK_START.md)
- Python adapter: [mcp-adapters/trading_analyst_adapter.py](mcp-adapters/trading_analyst_adapter.py)
- API endpoints: [apps/api/routes/mcp_analyst.py](apps/api/routes/mcp_analyst.py)
