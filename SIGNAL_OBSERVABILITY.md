# 📊 OptionsRanker Signal Observability

## Overview

Added comprehensive metrics tracking to **OptionsRanker** strategy to explain WHY signals are (or aren't) being generated.

**Before:** "0 trades today" (no explanation)
**After:** "Evaluated 14 setups; 10 failed IV filter, 4 failed liquidity; 0 passed all filters"

---

## Metrics Tracked

### 1. **Setups Evaluated** (`options_ranker_setups_evaluated_total`)
- **What:** Total number of option spread candidates evaluated
- **Labels:** `strategy_type` (DEBIT_SPREAD/CREDIT_SPREAD), `underlying` (NIFTY/BANKNIFTY)
- **When Incremented:** Every time `_generate_debit_spread()` is called (per scan cycle)

### 2. **Filter Rejections** (`options_ranker_filter_rejections_total`)
- **What:** Count of setups rejected by each specific filter
- **Labels:** `strategy_type`, `underlying`, `filter_name`
- **Filter Names:**
  - `iv_percentile` — IV outside configured range (20-80)
  - `trend_confirmation` — No clear directional bias (EMA/Supertrend)
  - `risk_reward` — RR ratio below minimum (1.5)
  - `liquidity` — Bid-ask spread too wide (future enhancement)
  - `cost` — Spread cost exceeds max (future enhancement)

### 3. **Signals Approved** (`options_ranker_signals_approved_total`)
- **What:** Signals that passed ALL filters and were sent to risk manager
- **Labels:** `strategy_type`, `underlying`, `spread_type` (BULL_CALL/BEAR_PUT)
- **When Incremented:** Right before returning approved signal

---

## How to Use

### **Intraday Monitoring**

Run this script every 30-60 minutes during trading hours:

```bash
bash scripts/query_signal_metrics.sh
```

**Example Output:**
```
📊 SETUPS EVALUATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NIFTY - DEBIT_SPREAD: 14 setups

❌ FILTER REJECTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IV Percentile (out of range): 10 rejections
  Liquidity (bid-ask too wide): 4 rejections
  Trend Confirmation (no bias): 0 rejections
  Risk-Reward Ratio (too low): 0 rejections

✅ SIGNALS APPROVED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No signals approved (0 passed all filters)

📈 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Setups Evaluated: 14
Total Rejected: 14
Total Approved: 0
Approval Rate: 0.0%

💡 INTERPRETATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  All setups rejected (14 evaluated)
   → Filters are working, but preventing all entries
   → Review which filters caused most rejections (above)
   → Top blocker: iv_percentile

   Possible actions:
     • Check if market IV is consistently outside 20-80 range
     • Consider widening IV range (e.g., 15-85)
```

---

### **Direct Prometheus Query**

Query raw metrics:

```bash
curl -s http://localhost:8000/metrics | grep options_ranker
```

**Sample Output:**
```
# HELP options_ranker_setups_evaluated_total Total number of option spread setups evaluated
# TYPE options_ranker_setups_evaluated_total counter
options_ranker_setups_evaluated_total{strategy_type="DEBIT_SPREAD",underlying="NIFTY"} 14.0

# HELP options_ranker_filter_rejections_total Option setups rejected by each filter
# TYPE options_ranker_filter_rejections_total counter
options_ranker_filter_rejections_total{filter_name="iv_percentile",strategy_type="DEBIT_SPREAD",underlying="NIFTY"} 10.0
options_ranker_filter_rejections_total{filter_name="liquidity",strategy_type="DEBIT_SPREAD",underlying="NIFTY"} 4.0

# HELP options_ranker_signals_approved_total Option signals that passed all filters
# TYPE options_ranker_signals_approved_total counter
options_ranker_signals_approved_total{spread_type="BULL_CALL",strategy_type="DEBIT_SPREAD",underlying="NIFTY"} 0.0
```

---

## Integration with Daily Reports

### **Enhanced Daily Report (Future)**

The `scripts/day3_analysis.py` (or similar) can now include:

```markdown
## Signal Generation Analysis

### OptionsRanker
- **Setups Evaluated**: 14
- **Signals Approved**: 0
- **Approval Rate**: 0.0%

### Filter Performance
| Filter | Rejections | % of Total |
|--------|------------|------------|
| IV Percentile | 10 | 71.4% |
| Liquidity | 4 | 28.6% |
| Trend Confirmation | 0 | 0.0% |
| Risk-Reward | 0 | 0.0% |

### Interpretation
All 14 candidate spreads were rejected. **Top blocker: IV Percentile** (71.4% of rejections).

Market IV was consistently outside the configured 20-80 range. Consider:
- Checking current IV percentile range (use R1 regime data)
- Widening acceptable IV range to 15-85
- Reviewing if IV filter is aligned with market conditions
```

---

## Decision Framework: When to Adjust Filters

### **Scenario 1: 0 Signals, High Evaluation Count**
```
Setups Evaluated: 20+
Signals Approved: 0
```

**Analysis:** Strategy is running and evaluating candidates, but filters are blocking everything.

**Action:**
1. Identify top rejection filter
2. Review if filter threshold is appropriate for current market
3. Consider temporary adjustment (but track impact)

**Example:**
- Top blocker: IV Percentile (90% of rejections)
- Current IV: 85 (above 80 max)
- Market: High volatility week
- **Action:** Widen IV max from 80 → 90 temporarily

---

### **Scenario 2: 0 Signals, 0 Evaluation Count**
```
Setups Evaluated: 0
Signals Approved: 0
```

**Analysis:** Strategy isn't running at all or not triggered.

**Action:**
1. Check if OptionsRanker is enabled
2. Check if market data is flowing
3. Check if entry window is correct (09:30-14:00)
4. Verify strategy is loaded in config

---

### **Scenario 3: High Approval Rate**
```
Setups Evaluated: 20
Signals Approved: 15
Approval Rate: 75%
```

**Analysis:** Filters are very permissive, possibly letting marginal setups through.

**Action:**
1. Review trades taken to ensure quality
2. If many losing trades: Tighten filters
3. If winning trades: Filters are calibrated well

---

### **Scenario 4: Moderate Approval Rate (Target)**
```
Setups Evaluated: 20
Signals Approved: 2-3
Approval Rate: 10-15%
```

**Analysis:** Filters are selective (as designed).

**Action:** No change needed. This is healthy.

---

## Filter Tuning Guidelines

### **IV Percentile**
```yaml
Current: 20-80
Too Strict If: >70% of setups rejected by IV, and market is in prolonged high/low IV period
Adjustment: Widen to 15-85 or 10-90
Too Loose If: Approval rate >50%, many losing trades
Adjustment: Narrow to 25-75
```

### **Trend Confirmation**
```yaml
Current: Required (EMA34 > EMA89 for bullish)
Too Strict If: >60% of setups have no directional bias in ranging market
Adjustment: Make optional or use softer threshold
Too Loose If: Whipsaw trades in choppy market
Adjustment: Require stronger confirmation (e.g., ATR-adjusted bands)
```

### **Risk-Reward**
```yaml
Current: 1.5 minimum
Too Strict If: >50% of setups rejected by RR
Adjustment: Lower to 1.2 or 1.3
Too Loose If: Many trades hit stop loss before target
Adjustment: Raise to 1.8 or 2.0
```

---

## Example: Day-3 with Observability

**Without Observability (Current State):**
```
Day-3: 0 trades
Reason: Unknown
Action: ???
```

**With Observability:**
```
Day-3: 0 trades

Signal Metrics:
  Setups Evaluated: 14
  Rejections:
    - IV Percentile: 10 (71%)
    - Liquidity: 4 (29%)
  Approved: 0

Reason: Market IV was 85 (above 80 max) for most of session
Action:
  1. Wait 3 more days to confirm pattern
  2. If IV consistently >80, widen max to 85
  3. If Day-4 to Day-7 also have high IV rejections, adjust filter
```

---

## Testing the Metrics

### **1. Verify Metrics are Being Recorded**

After market close:

```bash
curl -s http://localhost:8000/metrics | grep options_ranker_setups_evaluated
```

Should show non-zero if OptionsRanker ran.

---

### **2. Reset Metrics (Dev/Test)**

Prometheus counters are cumulative. To reset for testing:

```bash
# Restart the bot (counters reset to 0)
# Or use Prometheus `__admin/tsdb/delete_series` API
```

---

### **3. Simulate Signal Rejection**

Manually trigger OptionsRanker with different contexts to test filter rejection tracking:

```python
# In test script or debug mode
context = StrategyContext(
    timestamp=datetime.now(),
    instrument=nifty_instrument,
    iv_percentile=85,  # Above max (80)
    ...
)

signal = options_ranker._generate_debit_spread(context, ivp=85)
# Should return None and increment iv_percentile rejection counter
```

---

## Next Steps

### **Immediate (Day-4 onwards):**
1. ✅ Observability code deployed
2. ⏳ Run Day-4 with metrics collection
3. ⏳ At end of Day-4, run `bash scripts/query_signal_metrics.sh`
4. ⏳ Review which filters are blocking signals

### **Short-term (Week 2):**
1. Integrate metrics into automated daily report
2. Add liquidity and cost filter tracking (once implemented)
3. Add metrics for credit spreads and directional signals

### **Medium-term (Week 3-4):**
1. Build Grafana dashboard for real-time signal rejection visibility
2. Add alerting: "If >20 setups rejected by same filter, send notification"
3. Backtest filter thresholds against historical data

---

## Summary

**Before:** Flying blind — "0 trades, no idea why"
**After:** Data-driven decisions — "10/14 setups failed IV filter, consider widening"

**Key Insight:** Measure before you optimize. Don't blindly loosen filters; understand which filter is the bottleneck, then make targeted adjustments.

---

**📊 Observability is your friend. Use it before tuning anything.** 🎯
