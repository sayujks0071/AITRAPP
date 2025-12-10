# Trading Analyst MCP Server

High-level trading analysis and risk monitoring MCP server for AITRAPP.

## Overview

This MCP server provides **read-only** analysis tools that sit on top of your Kite + algo stack. It exposes 5 core tools designed to give you pre-digested views instead of requiring dozens of low-level API calls.

### Safety Model

- **No trading tools** - This server is READ-ONLY
- **Human-in-loop** - All recommendations require manual review
- **Analysis only** - Provides insights, flags, and config suggestions, but never places orders

## Tools

### 1. `get_live_risk_snapshot`

**Purpose:** Single call → full live risk view

**Returns:**
- Portfolio greeks (delta/gamma/vega/theta)
- Margin usage and utilization %
- Short premium exposure by underlying
- Tail coverage percentages
- Risk flags (MARGIN_OK, TAIL_COVERAGE_LOW, etc.)

**Example Prompt:**
```
Using get_live_risk_snapshot, tell me whether my margin, net delta,
and tail coverage are inside my configured limits. If not, which
underlying is causing the breach and what kind of action the bot
should consider?
```

---

### 2. `get_strategy_summary`

**Purpose:** Per-strategy performance and allocation context

**Returns:**
- Realised/unrealised PnL per strategy
- Hit rate over lookback window
- Max drawdown
- Current allocation %
- Regime usage (which regimes each strategy is active in)

**Example Prompt:**
```
Using get_strategy_summary, evaluate which strategies currently
justify more or less allocation based on hit-rate, max drawdown,
and recent PnL. Propose a list of suggested allocator weight
adjustments (increase/decrease/no change) and state the reasoning.
```

---

### 3. `get_broker_vs_algo_reconciliation`

**Purpose:** Detect state drift between Kite and your bot

**Returns:**
- Orphan positions (on broker but not in algo)
- Ghost positions (in algo but not on broker)
- Quantity mismatches
- Status (OK / MISMATCH_DETECTED)

**Example Prompt:**
```
Using get_broker_vs_algo_reconciliation, check for any mismatches.
For each mismatch, explain whether it's a likely reporting delay,
a partial fill the bot has not ingested, or a serious state drift.
Suggest what I should do manually if it's serious.
```

---

### 4. `get_event_and_regime_context`

**Purpose:** R1 regime + E1 event joint view

**Returns:**
- R1 regime classification (LOW/MEDIUM/HIGH) per underlying
- IV rank, ATR %, RV/IV ratio
- E1 event day type (NORMAL/PRE_EVENT/EVENT_DAY/POST_EVENT)
- Event name and severity

**Example Prompt:**
```
Using get_event_and_regime_context, summarise today's environment
in plain language: vol regime per index, whether it's a PRE_EVENT /
EVENT / POST_EVENT day, and which of my strategies (income, long gamma,
calendars, dispersion) are naturally favoured or should be toned down.
```

---

### 5. `propose_config_tweaks`

**Purpose:** Analyze recent performance and propose config changes

**Parameters:**
- `analysis_window_days` (default: 30)
- `focus`: 'allocator' | 'regimes' | 'strategies' | 'all'

**Returns:**
- Allocator weight change suggestions
- Regime band edit suggestions
- Strategy parameter edit suggestions

**Example Prompt:**
```
Using propose_config_tweaks with focus='allocator', analyze the last
30 days and propose weight changes for strategies that are consistently
underperforming or outperforming. I'll manually review and apply the
changes to my YAML configs.
```

---

## Installation

### 1. Install dependencies

```bash
cd mcp-servers/trading-analyst
npm install
npm run build
```

### 2. Make Python adapter executable

```bash
chmod +x ../../mcp-adapters/trading_analyst_adapter.py
```

### 3. Configure Cursor

Add to your Cursor MCP settings (`~/.cursor/mcp.json` or workspace `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "trading-analyst": {
      "command": "node",
      "args": [
        "/Users/mac/CRYPTO/AITRAPP/mcp-servers/trading-analyst/build/index.js"
      ],
      "env": {
        "BOT_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Important:** Update the absolute path in `args` to match your system.

### 4. Restart Cursor

After updating MCP config, restart Cursor for changes to take effect.

---

## Usage in Cursor

Once installed, you can use these tools in natural language prompts:

### Pre-open Checklist
```
Call get_broker_vs_algo_reconciliation and get_live_risk_snapshot.

Confirm I'm flat where I should be, margin & tail coverage are
within my pre-open sanity limits, and tell me in one paragraph
if it's safe to start the LIVE session from a state perspective.
```

### Intraday Risk Monitor
```
Using get_live_risk_snapshot, tell me if any of these thresholds
are breached:
- margin utilisation > 70%
- net delta > |15|
- tail coverage < 10% while short premium > ₹500k

If any breach happens, give me a plain-language summary so I can
decide whether to manually cut risk or pause the bot.
```

### Post-close Review
```
Use get_strategy_summary and get_event_and_regime_context for today.
Give me a mini PM note:
- which strategies made/lost money
- whether that matches the kind of regime we were in
- any obvious red flags (e.g., strategy consistently losing in the
  regimes it's supposed to be good at)

Also, draft a short bullet list of suggested config changes which
I can later review and apply manually.
```

---

## Architecture

```
┌─────────────────┐
│     Cursor      │
│   (AI Brain)    │
└────────┬────────┘
         │
         │ MCP Protocol
         │
┌────────▼────────────────────────┐
│  Trading Analyst MCP Server     │
│  (TypeScript, Node.js)          │
│                                 │
│  5 High-Level Tools:            │
│  - get_live_risk_snapshot       │
│  - get_strategy_summary         │
│  - get_broker_vs_algo_recon     │
│  - get_event_and_regime_context │
│  - propose_config_tweaks        │
└────────┬────────────────────────┘
         │
         │ subprocess calls
         │
┌────────▼────────────────────────┐
│  Python Adapter                 │
│  (trading_analyst_adapter.py)  │
│                                 │
│  Aggregates data from:          │
│  - FastAPI bot (/api/*)         │
│  - Kite (via kite_client.py)   │
└─────────────────────────────────┘
         │           │
         │           │
    ┌────▼───┐   ┌──▼─────┐
    │  Bot   │   │  Kite  │
    │  API   │   │  API   │
    └────────┘   └────────┘
```

---

## Development

### Building

```bash
npm run build
```

### Watch mode (for development)

```bash
npm run watch
```

### Testing the adapter directly

```bash
python3 mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}'
```

This should output JSON with risk snapshot data.

---

## Troubleshooting

### "Python adapter failed"

**Check:**
1. Python adapter is executable: `chmod +x mcp-adapters/trading_analyst_adapter.py`
2. Python dependencies installed: `pip install -r requirements.txt`
3. Bot API is running: `curl http://localhost:8000/health`

### "Bot API not available"

**Check:**
1. FastAPI app is running: `make run-api` or `python -m apps.api.main`
2. API port is correct (default: 8000)
3. Update `BOT_API_URL` env var in Cursor MCP config if using different port

### "Kite client errors"

**Check:**
1. Kite access token is valid and not expired
2. `.env` file has correct `KITE_API_KEY` and `KITE_ACCESS_TOKEN`
3. Run `python scripts/kite_token_refresh.py` if token expired

---

## Extending

To add a new tool:

1. **Add tool definition** in `src/index.ts` (in `ListToolsRequestSchema` handler)
2. **Add handler** in `src/index.ts` (in `CallToolRequestSchema` switch statement)
3. **Add Python method** in `mcp-adapters/trading_analyst_adapter.py`
4. **Add API endpoint** in `apps/api/routes/mcp_analyst.py` (if needed)
5. Rebuild: `npm run build`
6. Restart Cursor

---

## License

MIT
