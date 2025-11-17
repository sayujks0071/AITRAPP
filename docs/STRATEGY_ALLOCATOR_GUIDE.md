# Strategy Allocator - Multi-Strategy Capital Allocation Guide

## Overview

The Strategy Allocator is a **meta-layer** that decides how much capital each strategy is allowed to use. It acts as a "fund-of-strategies" manager, dynamically allocating capital based on:

- **Performance statistics** (hit rate, expectancy, drawdown)
- **R1 regime compatibility** (which strategies work best in current regime)
- **Market conditions** (IV rank, volatility, etc.)

**Key point:** The allocator does NOT generate trades. It sets per-strategy capital caps that the risk engine enforces.

---

## How It Works

### 1. Periodic Allocation Cycle

The allocator runs periodically (e.g. start-of-day, hourly):

1. **Gather stats** for each strategy (last 50 trades, last 30 days)
2. **Score strategies** based on performance (rule-based or ML)
3. **Apply regime overlay** (boost/cut strategies based on R1 regime)
4. **Normalize weights** (ensure weights sum to ≤ 1)
5. **Calculate capital caps** (weight × global_max_capital_pct)
6. **Update risk engine** (set per-strategy caps)
7. **Emit metrics** (for monitoring)

### 2. Scoring Logic (Rule-Based)

For each strategy:

- **Hit rate:** Wins / trades (must be ≥ 0.45)
- **Expectancy:** Avg PnL per trade (% of risk) (must be ≥ 0.10%)
- **Drawdown:** Max drawdown % (disable if > 5%)
- **Loss streak:** Consecutive losses (disable if ≥ 7)

Score components:
- Hit rate: 40-90% of score
- Expectancy: 30% of score
- Drawdown penalty: -50% if high drawdown

### 3. Regime Overlays

Based on current R1 regime, boost or cut strategy roles:

- **LOW_MEAN_REVERT:** Boost income_short_vol, cut long_vol
- **MEDIUM_TREND:** Boost directional_trend, cut income_short_vol
- **HIGH_EVENT:** Boost long_vol, cut income_short_vol
- **CHAOTIC:** Boost long_vol, cut most others

### 4. Capital Allocation

Final capital cap per strategy:
```
max_capital_pct = final_weight × global_max_capital_pct
```

Capped between `min_capital_pct_per_strategy` and `max_capital_pct_per_strategy`.

---

## Configuration

Edit `configs/strategy_allocator.yaml`:

### Global Settings
- `global_max_capital_pct`: Total capital under allocator control (60%)
- `min_capital_pct_per_strategy`: Floor per strategy (1%)
- `max_capital_pct_per_strategy`: Cap per strategy (25%)

### Stats Lookbacks
- `trade_window`: Last N trades to consider (50)
- `day_window`: Last N days to consider (30)

### Performance Thresholds
- `min_hit_rate`: Minimum hit rate (0.45)
- `min_expectancy_perc`: Minimum expectancy (0.10%)
- `max_drawdown_perc`: Max drawdown before disable (5.0%)
- `cold_streak_trades`: Losses in a row to disable (7)

### Strategy Configuration
Each strategy has:
- `name`: Strategy name (must match strategy registry)
- `base_weight`: Base allocation weight (0.0-1.0)
- `role`: Strategy role (for regime overlays)

### Regime Overlays
Define which roles to boost/cut per regime.

---

## Integration

### Enable Allocator

The allocator is not a strategy - it's a service that runs periodically.

Add to orchestrator initialization:

```python
from packages.core.stats_engine import StatsEngine
from packages.core.strategies.strategy_allocator import StrategyAllocator

# Initialize stats engine
stats_engine = StatsEngine(strategies=app_state.strategies)

# Initialize allocator
allocator = StrategyAllocator(
    cfg=config["strategy_allocator"],
    risk_engine=app_state.risk_manager,
    stats_engine=stats_engine,
    metrics=MetricsWrapper()
)

# Run at start of day (or periodically)
current_regime = get_current_r1_regime()  # From R1 metrics
allocs = allocator.run_allocation_cycle(current_regime=current_regime)
```

### Periodic Execution

Run allocator:
- **Start of day:** Once at market open
- **Hourly:** Every hour during market hours
- **On regime change:** When R1 regime switches

---

## Metrics

Allocator exposes Prometheus metrics:

- `allocator_raw_score{strategy}` - Raw performance score (0-1)
- `allocator_final_weight{strategy}` - Final normalized weight
- `allocator_max_capital_pct{strategy}` - Capital cap (%)
- `allocator_enabled{strategy}` - Whether strategy is enabled (1 or 0)

### Grafana Panels

**1. Allocation Table**
```promql
allocator_max_capital_pct{strategy=~".*"}
```

**2. Strategy Scores**
```promql
allocator_raw_score{strategy=~".*"}
```

**3. Enabled Strategies**
```promql
allocator_enabled{strategy=~".*"} == 1
```

**4. Allocation by Role**
Group by role to see which strategy types are favored.

---

## Safe Rollout Plan

### Phase 1: Observe Mode (Week 1-2)

1. **Run allocator but don't enforce caps:**
   - Let it compute allocations
   - Log them
   - Monitor metrics
   - Don't enforce in risk engine

2. **Review allocations:**
   - Do they make sense?
   - Are good strategies getting higher caps?
   - Are bad strategies getting cut?

### Phase 2: Soft Enforcement (Week 3-4)

1. **Enforce caps but with wide margins:**
   - Set `global_max_capital_pct: 0.40` (lower)
   - Set `max_capital_pct_per_strategy: 0.15` (lower)
   - Monitor if strategies hit caps

2. **Tune thresholds:**
   - Adjust `min_hit_rate`, `min_expectancy_perc`
   - Review regime overlays

### Phase 3: Full Enforcement (Week 5+)

1. **Increase to target caps:**
   - `global_max_capital_pct: 0.60`
   - `max_capital_pct_per_strategy: 0.25`

2. **Monitor performance:**
   - Does allocator improve overall returns?
   - Are allocations stable or too volatile?

---

## Testing Checklist

### Pre-Market

- [ ] Config loaded correctly
- [ ] Stats engine initialized
- [ ] Allocator initialized
- [ ] Metrics endpoints accessible

### During Market Hours

- [ ] Allocator runs at start of day
- [ ] Allocation metrics populate
- [ ] Strategy caps updated in risk engine
- [ ] Caps are enforced on trades

### Post-Market

- [ ] Review allocation decisions
- [ ] Compare allocations vs performance
- [ ] Tune thresholds if needed

---

## Troubleshooting

### Allocations Not Updating

1. **Check if allocator is running:**
   ```bash
   grep -i "allocation.*cycle" /tmp/kite_api_live.log | tail -10
   ```

2. **Check metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep allocator
   ```

3. **Verify stats engine:**
   - Ensure strategies are registered
   - Check if stats are being computed

### All Strategies Getting Zero Caps

1. **Check thresholds:**
   - May be too strict
   - Lower `min_hit_rate` or `min_expectancy_perc`

2. **Check stats:**
   - Are strategies reporting stats?
   - May need more trades to build history

### Allocations Too Volatile

1. **Increase lookback windows:**
   - `trade_window: 50` → `100`
   - `day_window: 30` → `60`

2. **Smooth scores:**
   - Add exponential moving average
   - Add minimum change threshold

---

## ML Integration (Future)

To swap in ML model:

1. **Train model offline:**
   - Features: hit_rate, expectancy, drawdown, regime_onehots, role_onehot, market_features
   - Target: score (0-1) or allocation bucket

2. **Host model:**
   - HTTP endpoint, or
   - Local model file

3. **Update `_score_strategy`:**
   ```python
   if self.cfg["model"]["type"] == "ML_REMOTE":
       score = self._call_ml_endpoint(features)
       enabled = score > some_min_threshold
   ```

Everything else (allocation, normalization, risk cap update) stays the same.

---

## Next Steps

1. ✅ **Wire allocator into orchestrator** - Run at start of day
2. ✅ **Test in observe mode** - Don't enforce caps initially
3. ✅ **Monitor allocations** - Review decisions vs performance
4. ⏳ **Tune thresholds** - Adjust based on observed behavior
5. ⏳ **Enhance stats engine** - Better trade history tracking
6. ⏳ **Add ML model** - Replace rule-based scoring

---

## Production Notes

**Current Limitations:**
- Stats engine uses simplified stats from strategy instances
- In production, would read from trade database
- Drawdown calculation is placeholder
- Loss streak tracking is simplified

**Future Enhancements:**
- Proper trade history database
- Accurate drawdown calculation
- Loss streak tracking
- ML model integration
- Allocation smoothing (EMA)
- Minimum change thresholds


