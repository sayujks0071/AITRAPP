# Trading Analyst MCP - Quick Start Guide

## What is this?

A **"trading analyst + risk officer"** MCP server that sits on top of your Kite + bot stack, giving you:

- Pre-digested risk views (not 10+ raw API calls)
- Strategy performance analysis
- Broker vs algo reconciliation (state drift detection)
- Regime + event context in plain language
- Config change proposals (you review & apply manually)

**Safety:** READ-ONLY. No trading tools. Human-in-loop for all actions.

---

## Install (One-time)

```bash
cd mcp-servers/trading-analyst
./install.sh
```

This will:
1. Install Node.js dependencies
2. Build TypeScript MCP server
3. Make Python adapter executable
4. Generate Cursor MCP config

Then copy the config to Cursor:

```bash
# Workspace-level (recommended)
mkdir -p .cursor
cp mcp-servers/trading-analyst/cursor-mcp-config.json .cursor/mcp.json

# OR user-level (all Cursor projects)
mkdir -p ~/.cursor
cp mcp-servers/trading-analyst/cursor-mcp-config.json ~/.cursor/mcp.json
```

**Restart Cursor** after copying config.

---

## Daily Workflow

### Pre-open (9:00 AM)

**Prompt:**
```
Call get_broker_vs_algo_reconciliation and get_live_risk_snapshot.

Confirm I'm flat where I should be, margin & tail coverage are
within my pre-open sanity limits, and tell me in one paragraph
if it's safe to start the LIVE session from a state perspective.
```

**What it does:**
- Checks for orphan/ghost positions
- Validates margin usage is < 50% (pre-open)
- Checks tail coverage is within configured bounds
- Gives you a GO/NO-GO in plain language

---

### Intraday (Every 30 min or on alert)

**Prompt:**
```
Using get_live_risk_snapshot, tell me if any of these thresholds
are breached:
- margin utilisation > 70%
- net delta > |15|
- tail coverage < 10% while short premium > ₹500k

If any breach happens, give me a plain-language summary so I can
decide whether to manually cut risk or pause the bot.
```

**What it does:**
- Computes portfolio greeks
- Checks margin usage
- Validates tail coverage vs short premium
- Flags breaches with actionable context

---

### Mid-day Check (12:30 PM)

**Prompt:**
```
Using get_event_and_regime_context, tell me:
- What regime we're in (LOW/MEDIUM/HIGH vol)
- Whether it's an event day (PRE_EVENT/EVENT_DAY/POST_EVENT)
- Which of my strategies should naturally be doing well vs struggling

Keep it to 2-3 sentences.
```

**What it does:**
- Gets R1 regime classification
- Gets E1 event day type
- Explains which strategies are favored/disfavored

---

### Post-close (3:45 PM)

**Prompt:**
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

**What it does:**
- Per-strategy PnL + hit rates
- Regime vs performance alignment check
- Flags underperforming strategies
- Suggests allocator weight changes (you review manually)

---

### Weekly Review (Friday EOD)

**Prompt:**
```
Using propose_config_tweaks with analysis_window_days=30 and
focus='allocator', analyze the last 30 days.

Propose weight changes for strategies that are consistently
underperforming or outperforming. I'll manually review and apply
the changes to my YAML configs.

For each suggestion, explain:
- Current allocation %
- Suggested new allocation %
- Reason (hit rate, drawdown, PnL trend)
```

**What it does:**
- Analyzes 30-day performance window
- Compares strategies against each other
- Proposes weight adjustments with reasoning
- Returns JSON patch you can manually apply

---

## Example Conversations

### Pre-open Safety Check

**You:**
> Using get_broker_vs_algo_reconciliation and get_live_risk_snapshot,
> give me a pre-open safety check. Are we flat, margin OK, no orphans?

**Cursor (via MCP):**
> ✅ **Pre-open Safety Check: GO**
>
> - **Reconciliation:** No mismatches. Broker and algo state match perfectly.
> - **Positions:** Flat (0 open positions)
> - **Margin:** Used ₹0, Available ₹1,000,000 (0% utilization)
> - **Tail Coverage:** N/A (no short premium)
>
> Safe to start LIVE session.

---

### Intraday Risk Breach

**You:**
> Using get_live_risk_snapshot, check if margin > 70% or tail coverage < 10%

**Cursor (via MCP):**
> ⚠️ **RISK BREACH DETECTED**
>
> - **Margin:** 78% utilized (₹780,000 / ₹1,000,000) ❌ OVER 70%
> - **Short Premium:** ₹850,000
> - **Tail Coverage:** 8.2% ❌ BELOW 10%
>
> **Suggested Actions:**
> 1. Reduce short premium in BANKNIFTY (₹450k exposed, only 6% tail coverage)
> 2. OR add more tail hedges (need ₹35k notional to reach 10% coverage)
> 3. OR pause new short vol positions until coverage improves
>
> **No automatic action taken.** Manual review required.

---

### Weekly Allocator Review

**You:**
> Using propose_config_tweaks with analysis_window_days=30,
> suggest allocator weight changes.

**Cursor (via MCP):**
> **Allocator Weight Change Proposals (30-day analysis)**
>
> 1. **R1 (RegimeVolEngine)**
>    - Current: 15%
>    - Suggested: 18% (+3%)
>    - Reason: 68% hit rate, ₹45k PnL, max DD ₹-12k. Strong in MEDIUM regime.
>
> 2. **G1 (GammaScalper)**
>    - Current: 8%
>    - Suggested: 5% (-3%)
>    - Reason: 42% hit rate, ₹-8k PnL, struggling in LOW vol regime.
>
> 3. **T1 (CalendarArb)**
>    - Current: 10%
>    - Suggested: 10% (no change)
>    - Reason: 55% hit rate, consistent but not exceptional.
>
> **To apply:**
> Edit `configs/strategy_allocator.yaml` weights and restart bot.

---

## Troubleshooting

### "Python adapter failed"

**Fix:**
```bash
# Make adapter executable
chmod +x mcp-adapters/trading_analyst_adapter.py

# Test directly
python3 mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}'
```

---

### "Bot API not available"

**Fix:**
```bash
# Check bot is running
curl http://localhost:8000/health

# If not, start it
make run-api
# OR
python -m apps.api.main
```

---

### "Kite client errors"

**Fix:**
```bash
# Refresh Kite access token
python scripts/kite_token_refresh.py

# Verify token in .env
cat .env | grep KITE_ACCESS_TOKEN
```

---

## Tips

1. **Bookmark common prompts** - Save your favorite prompts in a text file for quick copy-paste

2. **Chain multiple tools** - Cursor can call multiple MCP tools in one response:
   ```
   Using get_live_risk_snapshot AND get_broker_vs_algo_reconciliation,
   give me a full pre-open safety check.
   ```

3. **Be specific about thresholds** - The more specific you are, the better:
   ```
   Using get_live_risk_snapshot, flag if:
   - margin > 75%
   - net delta > |20|
   - tail coverage < 12%
   ```

4. **Use it for learning** - Ask "why" questions:
   ```
   Using get_event_and_regime_context, explain why R1 is favored
   in today's regime but G1 is not.
   ```

---

## What's Next?

Once you're comfortable with the 5 core tools, you can:

1. **Add custom tools** - See `README.md` for extending the server
2. **Automate common checks** - Create slash commands in Cursor
3. **Integrate with alerts** - Use MCP tools in response to Grafana/Prometheus alerts

---

## Architecture Reminder

```
Cursor (You + AI)
    ↓
Trading Analyst MCP (5 tools, read-only)
    ↓
Python Adapter (aggregates data)
    ↓
Bot API + Kite API
```

**No direct trading.** MCP is your analyst, not your trader.

---

## Support

- Full docs: `mcp-servers/trading-analyst/README.md`
- Python adapter: `mcp-adapters/trading_analyst_adapter.py`
- API endpoints: `apps/api/routes/mcp_analyst.py`
