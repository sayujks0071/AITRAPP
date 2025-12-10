# 🎯 Day-4+ Observability Guide

## What Changed

Added **comprehensive signal generation tracking** to OptionsRanker to answer:
- "How many setups were evaluated today?"
- "Why were signals rejected?"
- "Which filter is blocking the most trades?"

---

## Quick Start (Day-4)

### **1. Before Market Open (08:55 IST)**
Nothing new needed. Start bot as usual:

```bash
export APP_MODE=LIVE
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

Metrics will automatically start collecting.

---

### **2. During Trading (Every 30-60 min)**

Run this script to see signal generation activity:

```bash
bash scripts/query_signal_metrics.sh
```

**What you'll see:**
```
📊 SETUPS EVALUATED
  NIFTY - DEBIT_SPREAD: 14 setups

❌ FILTER REJECTIONS
  IV Percentile: 10 rejections
  Liquidity: 4 rejections

✅ SIGNALS APPROVED
  No signals approved

💡 INTERPRETATION
  Top blocker: IV Percentile (71% of rejections)
  → Market IV consistently outside 20-80 range
```

---

### **3. After Market Close (15:30 IST)**

Run the analysis script to get full session summary:

```bash
bash scripts/query_signal_metrics.sh > reports/daily/day4_signal_analysis.txt
```

Then review:
- Total setups evaluated
- Which filters rejected most
- Whether 0 trades was due to:
  - No setups (strategy didn't run)
  - All setups filtered (filters working)
  - Specific filter blocking (e.g., IV)

---

## Example Scenarios

### **Scenario A: "0 Trades, But Why?"**

**Before (Day-3):**
```
Trades: 0
Orders: 0
Status: ???
```

**After (Day-4+):**
```
Setups Evaluated: 14
Rejections:
  - IV Percentile: 10 (71%)
  - Liquidity: 4 (29%)
Approved: 0

Reason: Market IV was 85-90 all day (above 80 max)
Action: If this continues Day-5-7, widen IV max to 85
```

---

### **Scenario B: "Lots of Signals, Still No Trades"**

**Metrics Show:**
```
Setups Evaluated: 20
Signals Approved: 5
Trades Executed: 0
```

**Diagnosis:**
- Signals are being generated
- Filters are passing setups
- But trades not executing

**Check:**
1. Risk manager blocking? (check `/risk` endpoint)
2. Margin not available?
3. Execution errors?

**This is NEW visibility** — before, you'd think "strategy not working"; now you know "strategy IS working, issue is downstream".

---

### **Scenario C: "Filters Too Strict?"**

**Week 1 Metrics:**
```
Day-1: 10 setups, 0 approved (100% rejected by IV)
Day-2: 12 setups, 0 approved (92% rejected by IV)
Day-3: 14 setups, 0 approved (71% rejected by IV)
Day-4: 15 setups, 0 approved (80% rejected by IV)
```

**Conclusion:** IV filter is consistently the blocker.

**Action:**
1. Check market IV range for past 4 days
2. If IV was 80-90 all week → Widen max from 80 to 90
3. If IV was 20-80 but strategy rejecting → Bug in IV calculation

**Data-driven decision, not guesswork.**

---

## Decision Rules

### **When to Adjust Filters:**

**✅ DO adjust if:**
- 5-7 consecutive days with same filter blocking >70% of setups
- Market regime changed (e.g., entered high IV period)
- Approval rate <5% consistently

**❌ DON'T adjust if:**
- Only 1-2 days of data
- Approval rate is already healthy (10-20%)
- Market is choppy/ranging (filters protecting you)

---

## Filter Adjustment Process

### **Example: Widening IV Percentile**

**Current:** `ivp_min: 20, ivp_max: 80`

**Data Shows:**
```
Day-1 to Day-7: 80% of setups rejected by IV
Market IV: 85-95 all week
```

**Adjustment:**
```yaml
# In configs/kite_day1_live.yaml

strategies:
  - name: OptionsRanker
    params:
      ivp_min: 15  # Was 20
      ivp_max: 90  # Was 80
      # ... rest unchanged
```

**Track Impact:**
- Day-8: Monitor approval rate
- Expected: More setups pass IV filter
- If approval rate jumps to 50%+ → Too loose, revert
- If approval rate is 10-20% → Good calibration

---

## Integration with Daily Reports

Future daily reports can now include:

```markdown
## Signal Generation (OptionsRanker)

| Metric | Value |
|--------|-------|
| Setups Evaluated | 14 |
| Signals Approved | 0 |
| Approval Rate | 0% |

### Filter Breakdown
- IV Percentile: 10 rejections (71%)
- Liquidity: 4 rejections (29%)
- Trend: 0 rejections
- RR: 0 rejections

### Analysis
**Primary bottleneck: IV Percentile filter**

Market IV was consistently 85-90 (above max of 80). Strategy correctly filtered out high-IV setups, but this may indicate need to widen IV range if high volatility persists.

**Recommendation:** Monitor for 3 more days. If IV stays >80, consider widening max to 85-90.
```

---

## Files Added/Modified

### **Modified:**
1. `packages/core/strategies/options_ranker.py`
   - Added Prometheus metrics
   - Track setups evaluated
   - Track per-filter rejections
   - Track signals approved

### **New Files:**
1. `scripts/query_signal_metrics.sh`
   - Query and display signal metrics
   - Human-readable output
   - Interpretation guide

2. `SIGNAL_OBSERVABILITY.md`
   - Full documentation
   - Metrics reference
   - Decision framework
   - Examples

3. `DAY4_OBSERVABILITY_GUIDE.md` (this file)
   - Quick start guide
   - Day-4 specific instructions

---

## Troubleshooting

### **"Metrics show 0 setups evaluated"**

**Possible causes:**
1. OptionsRanker not enabled in config
2. Market data not flowing
3. Strategy not being called by orchestrator
4. Entry window restriction (only 09:30-14:00)

**Check:**
```bash
# Verify strategy loaded
curl -s http://localhost:8000/api/strategies/summary | jq '.strategies[].name'
# Should include "OptionsRanker"

# Verify market data
curl -s http://localhost:8000/ready | jq '.marketdata_heartbeat'
# Should be <5 seconds
```

---

### **"Metrics don't reset day-to-day"**

**Expected behavior:** Prometheus counters are cumulative (don't reset daily).

**To see daily breakdown:**
- Use Prometheus query with time range
- Or restart bot daily (counters reset)
- Or calculate delta (Day-4 count - Day-3 count)

**For daily reports:** Calculate difference from previous day's count.

---

## Next Steps After Day-4

1. **Review Day-4 metrics** — Which filter blocked most?
2. **Wait for Day-5-7 data** — Confirm pattern (don't act on 1 day)
3. **Make targeted adjustment** — Only tune the filter causing issues
4. **Measure impact** — Did adjustment improve approval rate without sacrificing quality?

---

## Summary

**Observability transforms "0 trades, ???" into "0 trades because..."**

You now have:
- ✅ Real-time visibility into signal generation
- ✅ Per-filter rejection tracking
- ✅ Data-driven filter tuning process
- ✅ Evidence for "filters too strict" vs "no setups available"

**Use this before adjusting ANY filters.**

---

**🎯 For Day-4: Just collect data. Don't tune yet. Let the metrics speak.** 📊
