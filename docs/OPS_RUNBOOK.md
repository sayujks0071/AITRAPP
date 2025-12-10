# Ops Runbook - One-Page Daily Operations Guide

## 🌅 Morning (Pre-Open: 8:45 - 9:10 IST)

### 6 Critical Checks

1. **System Health**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/state
   curl http://localhost:8000/ready
   ```
   ✅ All return `200 OK`, `/ready` shows `ready: true`

2. **Leader Lock**
   ```bash
   curl http://localhost:8000/metrics | grep trader_is_leader
   ```
   ✅ Should be `1.0` (not `0`)

3. **Heartbeats**
   ```bash
   curl http://localhost:8000/metrics | grep heartbeat
   ```
   ✅ All < 5 seconds

4. **Scan Activity**
   ```bash
   curl http://localhost:8000/metrics | grep trader_scan_ticks_total
   ```
   ✅ Increasing (not stuck at 0)

5. **Strategy Verification** (MANDATORY)
   ```bash
   make verify-r1 verify-g1 verify-t1 verify-d1 verify-h1 verify-allocator
   make sanity-check  # Quick metrics check - DO NOT SKIP
   ```
   ✅ All pass
   ⚠️  **If anything looks off (no regimes, NaNs, absurd coverage) → DO NOT RUN SESSION until explained**
   📋 See `docs/OBSERVATION_CHECKLIST.md` for pass/fail criteria

6. **MCP Pre-Flight Check** (RECOMMENDED)
   ```
   Using get_broker_vs_algo_reconciliation and get_live_risk_snapshot,
   give me GO/NO-GO for LIVE session.
   ```
   - Check for orphan positions (broker vs algo drift)
   - Verify risk state (margin, greeks, tail coverage)
   - Flag any issues before market open
   📋 See `docs/CURSOR_PROMPTS.md` for more MCP prompts

7. **Allocator Run**
   - Check allocator ran (logs or metrics)
   - Review allocation decisions
   - Verify caps set correctly

---

## 📈 During Market (9:15 - 15:30 IST)

### MCP Intraday Checks (Every 30-60 min)
```
Using get_live_risk_snapshot, flag if:
- margin > 70%
- |net delta| > 15
- tail coverage < 10% while short premium > ₹500k
```
- Quick risk check without manual metric queries
- Natural language flags for issues
- Regime-aware context included

### 5 Graphs to Watch

1. **Regime Status**
   - Query: `algo_vol_regime_code{underlying="NIFTY"}`
   - Watch: Current regime, regime switches
   - Expected: Matches market conditions

2. **Strategy Activity**
   - Queries:
     - `gamma_scalper_books_opened`
     - `calendar_arb_books_opened`
     - `dispersion_arb_books_opened`
   - Watch: Books opening/closing
   - Expected: Activity matches regime

3. **Allocator Weights**
   - Query: `allocator_final_weight{strategy=~".*"}`
   - Watch: Which strategies get higher weights
   - Expected: Good strategies up, bad strategies down

4. **Tail Coverage**
   - Query: `tail_short_vol_coverage_pct{underlying="NIFTY"}`
   - Watch: Coverage percentage
   - Expected: 10-15% normal, 20-30% in HIGH_EVENT/CHAOTIC

5. **System Health**
   - Queries:
     - `trader_is_leader`
     - `trader_marketdata_heartbeat_seconds`
     - `trader_scan_heartbeat_seconds`
   - Watch: Leader lock, heartbeats
   - Expected: All green, no stale

---

## 🌆 Evening (Post-Close: 15:30 - 16:00 IST)

### 4 Report Items to Review

1. **Per-Strategy PnL vs Allocator Caps**
   - Check: Did strategies with higher caps perform better?
   - Look for: Mismatches (high cap but poor performance, or vice versa)
   - Action: Tune allocator weights if needed

2. **Tail Coverage Profile**
   - Check: Coverage over the day
   - Look for: Coverage adjusted with regime? Costs reasonable?
   - Action: Adjust H1 targets if needed

3. **R1 Regime Timeline vs Price Action**
   - Check: Did regime classification match actual market?
   - Look for: Regime switches align with events? Classification makes sense?
   - Action: Tune R1 thresholds if needed

4. **Daily Report & Snapshot**
   ```bash
   make daily-report
   make sanity-check  # Optional: quick post-close metrics glance
   ./scripts/save_daily_snapshot.sh  # Archive report + sanity check + configs
   ```
   - Review: `reports/daily/YYYY-MM-DD_report.md`
   - Check: All sections populated, numbers make sense
   - Action: Note any anomalies for next day

4b. **MCP EOD Analysis** (RECOMMENDED)
   ```
   Using get_strategy_summary and get_event_and_regime_context,
   give me EOD PM note with strategy performance vs regime.
   ```
   - Pre-digested strategy performance summary
   - Regime context for the day
   - Natural language insights
   📋 See `docs/CURSOR_PROMPTS.md` for more prompts

5. **Config Changes (if any)**
   ```bash
   # If you tuned any YAML thresholds today:
   ./scripts/commit_configs.sh "tune: R1 bands + T1 NIFTY term structure thresholds"
   ```
   - Commit config changes with descriptive message
   - This creates audit trail: "We changed X on this date, PnL/regimes changed like this"

---

## 🚨 Red Flags - Stop Trading If

- ❌ Leader lock lost (`trader_is_leader = 0`)
- ❌ Heartbeats stale (> 30 seconds)
- ❌ Daily loss limit hit
- ❌ Portfolio heat exceeded
- ❌ Execution errors (> 2 in a day)
- ❌ System errors detected

**Action:** Stop trading, investigate, fix, verify in PAPER before resuming.

---

## 📋 Quick Reference

### Verification Commands
```bash
make verify-r1        # Regime engine
make verify-g1        # Gamma scalper
make verify-t1        # Calendar arb
make verify-d1        # Dispersion arb
make verify-h1        # Tail overlay
make verify-allocator # Capital allocator
make sanity-check     # Quick metrics check (all strategies)
```

### MCP Tools (via Cursor)
```
get_live_risk_snapshot              # Complete risk view
get_strategy_summary                # Per-strategy performance
get_broker_vs_algo_reconciliation   # State drift detection
get_event_and_regime_context        # R1 + E1 joint view
propose_config_tweaks               # AI config suggestions
```
📋 See `docs/CURSOR_PROMPTS.md` for prompt library

### Health Checks
```bash
curl http://localhost:8000/health
curl http://localhost:8000/state
curl http://localhost:8000/ready
curl http://localhost:8000/metrics | grep trader_is_leader
```

### Daily Report
```bash
make daily-report
# Review: reports/daily/YYYY-MM-DD_report.md
```

### Key Metrics Endpoints
- Health: `http://localhost:8000/health`
- State: `http://localhost:8000/state`
- Ready: `http://localhost:8000/ready`
- Metrics: `http://localhost:8000/metrics`

---

## 📞 Emergency Contacts

- **System Issues:** Check logs: `tail -f /tmp/kite_api_live.log`
- **Position Issues:** Check position store
- **Execution Issues:** Check broker connection
- **Data Issues:** Check market data stream

---

## ✅ Daily Checklist

```
Pre-Open:
[ ] System health OK
[ ] Leader lock acquired
[ ] Heartbeats < 5s
[ ] Scan ticks > 0
[ ] All verifications pass
[ ] MCP pre-flight check (GO/NO-GO)
[ ] Allocator ran

During Market:
[ ] Regime status monitored
[ ] Strategy activity tracked
[ ] Allocator weights reviewed
[ ] Tail coverage checked
[ ] MCP intraday risk check (every 30-60 min)
[ ] System health stable

Post-Close:
[ ] Daily report generated
[ ] MCP EOD analysis
[ ] PnL vs caps reviewed
[ ] Tail coverage reviewed
[ ] Regime timeline reviewed
[ ] Anomalies noted
```

---

**Print this page and keep it handy during trading hours.**


