# ✅ Signal Observability Implementation Complete

## What Was Done

Added comprehensive metrics tracking to **OptionsRanker** strategy to make "0 trades" days explainable and actionable.

---

## The Problem (Before)

**Day-3 Report:**
```
Trades: 0
Orders: 0
Signals: 0
Reason: Unknown
Action: ??? (loosen filters blindly?)
```

**Questions you couldn't answer:**
- Did OptionsRanker evaluate any setups?
- Which filter rejected signals?
- Is IV the problem? Trend? Liquidity?
- Should I widen IV range, or is strategy not running at all?

---

## The Solution (After)

**Day-4+ Report:**
```
Setups Evaluated: 14
Rejections:
  - IV Percentile: 10 (71%)
  - Liquidity: 4 (29%)
  - Trend: 0 (0%)
  - RR: 0 (0%)
Signals Approved: 0

Reason: Market IV was 85-90 all day (above 80 max)
Action: Monitor for 3 more days. If IV stays >80, widen max to 85-90.
```

**Questions you CAN now answer:**
- ✅ Yes, 14 setups were evaluated
- ✅ IV filter blocked 71% of them
- ✅ Market IV was outside acceptable range
- ✅ Targeted action: Widen IV range (not blindly loosen everything)

---

## Files Modified/Created

### **1. Modified: `packages/core/strategies/options_ranker.py`**

Added three Prometheus metrics:

```python
# Metric 1: Total setups evaluated
options_ranker_setups_evaluated.labels(
    strategy_type="DEBIT_SPREAD",
    underlying="NIFTY"
).inc()

# Metric 2: Per-filter rejections
options_ranker_filter_rejections.labels(
    strategy_type="DEBIT_SPREAD",
    underlying="NIFTY",
    filter_name="iv_percentile"  # or "trend_confirmation", "risk_reward", etc.
).inc()

# Metric 3: Signals approved
options_ranker_signals_approved.labels(
    strategy_type="DEBIT_SPREAD",
    underlying="NIFTY",
    spread_type="BULL_CALL"  # or "BEAR_PUT"
).inc()
```

**Tracked filters:**
- `iv_percentile` — IV outside 20-80 range
- `trend_confirmation` — No EMA/Supertrend directional bias
- `risk_reward` — RR below 1.5 minimum

---

### **2. New: `scripts/query_signal_metrics.sh`**

Interactive script to query and display signal generation metrics.

**Usage:**
```bash
bash scripts/query_signal_metrics.sh
```

**Output:**
- Setups evaluated (by underlying and strategy type)
- Filter rejections (grouped by filter name)
- Signals approved (by spread type)
- Summary statistics (approval rate, top blocker)
- Interpretation guide (what to do next)

---

### **3. New: `SIGNAL_OBSERVABILITY.md`**

Comprehensive documentation covering:
- Metrics reference (what each metric tracks)
- How to query metrics (script usage + raw Prometheus)
- Decision framework (when to adjust filters)
- Filter tuning guidelines (IV, trend, RR thresholds)
- Examples and scenarios
- Testing and troubleshooting

---

### **4. New: `DAY4_OBSERVABILITY_GUIDE.md`**

Quick start guide for Day-4:
- What to do before market open
- How to monitor during trading
- What to check after market close
- Example scenarios and decision rules
- Integration with daily reports

---

### **5. New: `OBSERVABILITY_SUMMARY.md`** (this file)

High-level summary of the implementation.

---

## How This Changes Your Workflow

### **Day-4 Morning (Before Open):**
```
1. Start bot as usual (no config changes needed)
2. Metrics collection starts automatically
```

---

### **Day-4 Intraday (Every 30-60 min):**
```
1. Run: bash scripts/query_signal_metrics.sh
2. Check if setups are being evaluated
3. Check if any signals are being approved
4. If 0 signals, see which filter is blocking
```

**Example Check (11:00 AM):**
```bash
$ bash scripts/query_signal_metrics.sh

📊 SETUPS EVALUATED
  NIFTY - DEBIT_SPREAD: 6 setups

❌ FILTER REJECTIONS
  IV Percentile: 5 rejections
  Trend Confirmation: 1 rejection

✅ SIGNALS APPROVED
  No signals approved

💡 Top blocker: IV Percentile
```

**Interpretation:** Strategy is running and evaluating setups, but IV is consistently out of range. This is expected behavior (filters working). If this continues all day, may consider widening IV range.

---

### **Day-4 EOD (After Close):**
```
1. Run final metrics query
2. Review full day's data:
   - Total setups: 14
   - Top blocker: IV (71% of rejections)
   - Approval rate: 0%

3. Add to daily report:
   - "Evaluated 14 setups, all rejected"
   - "Primary blocker: IV filter (10/14)"
   - "Market IV ranged 85-90 (above 80 max)"

4. Decision:
   - DON'T adjust yet (only 1 day of data)
   - Track for Days 5-7
   - If pattern continues, widen IV max to 85-90
```

---

## Decision Matrix

### **When to Adjust Filters:**

| Scenario | Setups | Approved | Action |
|----------|--------|----------|--------|
| **0 setups, 0 approved** | 0 | 0 | Check if strategy running |
| **Many setups, 0 approved** | 10+ | 0 | Identify top blocker filter |
| **Many setups, few approved** | 20 | 2-3 | Filters working correctly ✅ |
| **Many setups, many approved** | 20 | 15+ | Filters may be too loose ⚠️ |

### **Filter Adjustment Timeline:**

```
Day 1-3: Collect data, don't adjust
Day 4-7: Identify patterns (which filter consistently blocks?)
Day 8+: Make targeted adjustment to specific filter
Day 9-14: Measure impact, iterate
```

**Never adjust on 1 day of data.**

---

## Example: Full Week Analysis

### **Week 1 Signal Data:**

| Day | Setups | IV Rejects | Trend Rejects | RR Rejects | Approved | Trades |
|-----|--------|------------|---------------|------------|----------|--------|
| 1 | 10 | 8 (80%) | 2 | 0 | 0 | 0 |
| 2 | 12 | 11 (92%) | 1 | 0 | 0 | 0 |
| 3 | 14 | 10 (71%) | 4 | 0 | 0 | 0 |
| 4 | 15 | 12 (80%) | 3 | 0 | 0 | 0 |
| 5 | 11 | 9 (82%) | 2 | 0 | 0 | 0 |

**Analysis:**
- Total setups: 62
- IV rejections: 50 (81% of all rejections)
- Pattern: Consistent across all 5 days
- Market IV: 85-95 all week (above 80 max)

**Conclusion:** IV filter is primary blocker.

**Action:**
```yaml
# Widen IV max from 80 → 90
strategies:
  - name: OptionsRanker
    params:
      ivp_max: 90  # Was 80
```

**Expected Week 2 Results:**
- More setups pass IV filter
- Approval rate increases from 0% to 10-20%
- Monitor trade quality (win rate, RR)

---

## What You DON'T Need to Do

### **❌ Don't:**
1. **Manually log filter rejections** — Automated via metrics
2. **Guess why no signals** — Metrics tell you exactly why
3. **Blindly loosen all filters** — Targeted adjustments only
4. **Adjust on 1 day of data** — Wait for patterns (5-7 days)
5. **Write custom analysis scripts** — `query_signal_metrics.sh` does it

### **✅ Do:**
1. **Run metrics script daily** — Takes 5 seconds
2. **Track patterns across days** — Which filter consistently blocks?
3. **Make data-driven decisions** — Adjust only the problematic filter
4. **Measure impact** — Did adjustment improve approval rate?
5. **Iterate gradually** — Small tweaks, observe, repeat

---

## Verification (Day-4 Morning)

After starting bot, verify metrics are recording:

```bash
# Wait 30 minutes after market open (09:45 IST)

# Check metrics endpoint
curl -s http://localhost:8000/metrics | grep options_ranker

# Should see:
# options_ranker_setups_evaluated_total{...} X.0
# Where X > 0 if OptionsRanker has run
```

If you see 0 or no metrics:
1. Verify OptionsRanker is loaded: `curl -s http://localhost:8000/api/strategies/summary`
2. Check if market data is flowing: `curl -s http://localhost:8000/ready`
3. Verify entry window (09:30-14:00 IST)

---

## Long-Term Benefits

### **Week 1-2:**
- Understand why 0 trades (data, not guesses)
- Identify bottleneck filters
- Build confidence in filter logic

### **Month 1:**
- Have 20-30 days of filter rejection data
- Identify if filters need seasonal adjustment (high IV weeks vs low IV weeks)
- Tune filters with statistical backing

### **Month 2+:**
- Build Grafana dashboard for real-time visibility
- Set up alerts ("If IV filter blocks >80% of setups for 3 days, notify me")
- Backtest historical filter thresholds
- Regime-aware filter tuning (adjust IV range based on R1 regime)

---

## Summary

**Before:** "0 trades" → Blind guessing → Random filter adjustments → Still no trades

**After:** "0 trades" → Check metrics → "IV filter blocked 80%" → Targeted adjustment → Monitor impact

**Key Principle:** **Measure before you optimize.**

---

## Next Steps

1. ✅ **Day-4:** Run with metrics collection (no filter changes)
2. ⏳ **Day-4 EOD:** Run `query_signal_metrics.sh`, add to daily report
3. ⏳ **Days 5-7:** Continue collecting data, identify patterns
4. ⏳ **Day 8:** If clear bottleneck filter, make targeted adjustment
5. ⏳ **Days 9-14:** Measure impact of adjustment, iterate

---

**🎯 Observability implemented. Filters stay unchanged. Let the data guide you.** 📊
