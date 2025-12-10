# Trading Analyst MCP - Quick Reference Card

**Print this or keep it open in a terminal during trading hours.**

---

## 🚀 5 Core Tools

| Tool | What It Does | When to Use |
|------|--------------|-------------|
| `get_live_risk_snapshot` | Complete risk view: greeks, margin, tail coverage, flags | Every 30-60 min |
| `get_strategy_summary` | Per-strategy PnL, hit rates, allocation | EOD, weekly review |
| `get_broker_vs_algo_reconciliation` | State drift detection (orphans/ghosts) | Pre-open, EOD |
| `get_event_and_regime_context` | R1 regime + E1 event joint view | Pre-open, intraday |
| `propose_config_tweaks` | AI config suggestions (you review) | Weekly, monthly |

---

## ⏰ Daily Checklist

### Pre-Open (9:00 AM)
```
Using MCP, call get_broker_vs_algo_reconciliation and get_live_risk_snapshot.
Give me GO/NO-GO for LIVE session.
```
**Check:** Flatness, no orphans, margin < 50%

---

### Intraday (Every 30-60 min)
```
Using get_live_risk_snapshot, flag if:
- margin > 70%
- |net delta| > 15
- tail coverage < 10% while short premium > ₹500k
```
**Check:** Risk within limits

---

### Mid-Day (12:30 PM - Optional)
```
Using get_event_and_regime_context, summarise today's regime and which strategies should work.
```
**Check:** Environment alignment

---

### Post-Close (3:45 PM)
```
Using get_strategy_summary and get_event_and_regime_context, give me EOD PM note.
```
**Check:** Strategy performance vs regime

---

## 🔴 Emergency Prompts

### Sudden PnL Drop
```
We just had unexpected PnL drop. Using MCP tools, diagnose:
- Which strategy/underlying?
- Broker vs algo match?
- Risk metrics within limits?
- Normal volatility or bug?
```

### Weird Behaviour
```
Something feels off. Using get_live_risk_snapshot + get_broker_vs_algo_reconciliation, check for state drift or config issues.
```

---

## 📊 Your Risk Limits (Quick Reference)

**Update these to match YOUR configs:**

| Metric | Comfortable | Warning | Hard Stop |
|--------|-------------|---------|-----------|
| Margin | < 50% | 50-70% | > 70% |
| Net Delta | < 10 | 10-15 | > 15 |
| Tail Coverage | > 15% | 10-15% | < 10% |
| Daily PnL | Any | -₹30k | -₹50k |

---

## 🎯 Common Prompts (Copy-Paste)

### Pre-Open GO/NO-GO
```
Using the Trading Analyst MCP tools, call get_broker_vs_algo_reconciliation and get_live_risk_snapshot.

Confirm:
1. No mismatches between broker and algo
2. Flat where expected
3. Margin < 50%, no orphans

Answer with GO or NO-GO for LIVE session.
```

### Intraday Risk Check
```
Using get_live_risk_snapshot, flag if:
- margin > 70%
- |net delta| > 15
- tail coverage < 10% while short premium > ₹500k

Keep it to one paragraph if all OK, RED FLAGS if breached.
```

### Environment Check
```
Using get_live_risk_snapshot and get_event_and_regime_context, check if my current positioning is aligned with today's regime or fighting it.
```

### EOD PM Note
```
Using get_strategy_summary and get_event_and_regime_context for today, give me EOD PM note:
- PnL per strategy
- Regime alignment
- Red flags
- Config suggestions
```

### Weekly Review
```
Using get_strategy_summary with 30-day lookback and propose_config_tweaks, suggest allocator weight changes. I'll review and apply manually.
```

---

## 🔧 Troubleshooting (30-Second Fixes)

| Problem | Fix |
|---------|-----|
| MCP not showing in Cursor | Restart Cursor (quit + reopen) |
| Python adapter failed | `make run-api` to start bot |
| Kite client error | `python scripts/kite_token_refresh.py` |
| Tool returns placeholder data | Check bot API: `curl localhost:8000/health` |

---

## 💡 Pro Tips

1. **Chain tools**: "Using get_live_risk_snapshot AND get_broker_vs_algo_reconciliation, ..."
2. **Be specific**: "Flag if margin > 70%" not "tell me if bad"
3. **Save favorites**: Keep common prompts in `~/trading_prompts.txt`
4. **Ask why**: "Explain why R1 works in MEDIUM_TREND regime"

---

## 📁 File Locations

```
Trading Analyst Setup:
mcp-servers/trading-analyst/install.sh   # Install
mcp-servers/trading-analyst/test.sh      # Test
.cursor/mcp.json                         # Cursor config

Documentation:
docs/CURSOR_PROMPTS.md                   # Full prompt playbook
docs/MCP_ANALYST_QUICK_START.md          # Daily workflow guide
mcp-servers/trading-analyst/README.md    # Technical docs
```

---

## 🎓 Learning Path

**Week 1:** Pre-open, intraday, EOD checks
**Week 2:** Weekly allocator review
**Week 3:** Strategy-specific diagnostics
**Week 4+:** Custom prompts

---

## ⚠️ Remember

**MCP is READ-ONLY**
- ✅ Reads data from bot + Kite
- ✅ Analyzes and suggests
- ❌ Never places orders
- ❌ Never modifies configs

**You** make all final decisions.

---

## 🆘 Emergency Contacts

**Bot not responding?**
```bash
# Check status
make status

# Restart
make restart

# Check logs
tail -f logs/api.log
```

**MCP issues?**
```bash
# Test health
cd mcp-servers/trading-analyst
./test.sh

# Check Cursor logs
Cursor → View → Output → MCP
```

---

## 📞 Quick Commands

```bash
# Start bot
make run-api

# Test MCP adapter
python3 mcp-adapters/trading_analyst_adapter.py get_live_risk_snapshot '{}'

# Refresh Kite token
python scripts/kite_token_refresh.py

# Check health
curl localhost:8000/health

# Run MCP tests
cd mcp-servers/trading-analyst && ./test.sh
```

---

**Last Updated:** 2025-11-17

**Keep this reference card handy during trading hours!**
