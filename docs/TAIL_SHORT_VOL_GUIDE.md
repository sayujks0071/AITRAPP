# Tail-Hedged Short Vol Overlay (H1) - Risk Protection Guide

## Overview

The Tail-Hedged Short Vol Overlay (H1) is a **risk overlay** (not a trading strategy) that automatically ensures tail hedge coverage for all short-premium strategies.

**Core idea:** Always maintain deep OTM put protection proportional to your short vol exposure, with coverage automatically adjusted based on R1 regime.

---

## How It Works

### 1. Monitoring (Every 30 minutes)

**H1 continuously:**
- Aggregates short premium notional across all short-vol strategies
- Aggregates current tail hedge notional (deep OTM puts)
- Calculates coverage percentage
- Compares to target coverage (adjusted by regime)

### 2. Coverage Targets

**Base coverage:** 15% of short premium notional

**Regime-adjusted:**
- **LOW_MEAN_REVERT:** 1.0x (15% coverage)
- **MEDIUM_TREND:** 1.1x (16.5% coverage)
- **HIGH_EVENT:** 1.5x (22.5% coverage)
- **CHAOTIC:** 2.0x (30% coverage)

### 3. Adjustment Triggers

**H1 adjusts tails when:**
- Coverage gap > 3% of short premium
- Short premium notional changes > 10%
- Rebalance interval elapsed (30 minutes)

**H1 buys:**
- Deep OTM puts (5-8% below spot)
- Next monthly expiry (or nearest with ≥20 days)
- Enough lots to reach target coverage

### 4. Tail Management

**Rolls tails when:**
- Days to expiry < 20
- Takes profit if PnL > 100%
- Stops loss if PnL < -70% (optional)

---

## Configuration

Edit `configs/tail_short_vol.yaml`:

### Short Vol Strategies
- `short_vol_strategies`: List of strategy names considered "short vol"
- These are monitored for exposure

### Tail Instruments
- `tail_underlyings`: Underlyings to hedge (NIFTY, BANKNIFTY)
- `strike_offset_pct`: How OTM (5-8%)
- `expiry_selector`: Which expiry to use

### Risk Budgets
- `max_short_premium_pct`: Max short premium cap (40%)
- `target_tail_coverage_pct`: Target coverage (15%)
- `min_tail_coverage_pct`: Minimum coverage (10%)
- `max_tail_coverage_pct`: Maximum coverage (25%)

### Rebalance Settings
- `interval_minutes`: How often to check (30)
- `min_notional_change_pct`: Minimum change to trigger (10%)
- `min_tail_gap_pct`: Minimum gap to trigger (3%)

### Regime Overlays
- Coverage multipliers per regime
- Automatically adjusts target coverage

---

## Integration

### Enable Overlay

Add to `configs/app.yaml`:

```yaml
strategies:
  - name: "TailShortVolOverlay"
    enabled: true
    params: {}
```

The overlay will automatically load from `configs/tail_short_vol.yaml`.

### Execution Cadence

H1 should run:
- **On each scan** for NIFTY/BANKNIFTY, OR
- **Separate overlay loop** every 30 minutes

The overlay respects the rebalance interval, so calling it more frequently is safe.

### Position Store Integration

H1 needs access to current positions to:
- Calculate short premium notional
- Calculate current tail hedge notional

In production, wire in your position store:
```python
strategy = TailShortVolOverlay(
    ...,
    positions_store=app_state.position_store  # Your position manager
)
```

---

## Metrics

H1 exposes Prometheus metrics:

- `tail_short_vol_short_notional{underlying}` - Short premium notional
- `tail_short_vol_tail_notional{underlying}` - Current tail hedge notional
- `tail_short_vol_coverage_pct{underlying}` - Coverage percentage
- `tail_short_vol_adjustments{underlying}` - Number of adjustments
- `tail_short_vol_over_short_cap{underlying}` - Over short cap flag (1 or 0)

### Grafana Panels

**1. Coverage Dashboard**
```promql
tail_short_vol_coverage_pct{underlying="NIFTY"}
tail_short_vol_short_notional{underlying="NIFTY"}
tail_short_vol_tail_notional{underlying="NIFTY"}
```

**2. Coverage by Regime**
```promql
tail_short_vol_coverage_pct{underlying="NIFTY"}
# Overlay with algo_vol_regime_code to see regime-adjusted targets
```

**3. Adjustment Frequency**
```promql
sum(increase(tail_short_vol_adjustments[1d])) by (underlying)
```

---

## Safe Rollout Plan

### Phase 1: Observe Mode (Week 1-2)

1. **Enable but don't enforce:**
   - Let H1 calculate coverage
   - Log adjustments
   - Monitor metrics
   - Don't execute tail trades

2. **Review behavior:**
   - Does coverage make sense?
   - Are adjustments reasonable?
   - Does regime adjustment work?

### Phase 2: Small Coverage (Week 3-4)

1. **Enable with modest targets:**
   ```yaml
   target_tail_coverage_pct: 0.10  # Lower
   min_tail_coverage_pct: 0.08
   max_tail_coverage_pct: 0.15
   ```

2. **Monitor:**
   - Tail trades executing
   - Coverage staying in range
   - Costs vs protection

### Phase 3: Full Coverage (Week 5+)

1. **Increase to target:**
   ```yaml
   target_tail_coverage_pct: 0.15
   min_tail_coverage_pct: 0.10
   max_tail_coverage_pct: 0.25
   ```

2. **Monitor performance:**
   - Does tail protection help during events?
   - Are costs reasonable?
   - Adjust multipliers if needed

---

## Testing Checklist

### Pre-Market

- [ ] Config loaded correctly
- [ ] Overlay appears in `/state` endpoint
- [ ] Metrics endpoints accessible
- [ ] Position store integrated (if available)

### During Market Hours

- [ ] Coverage metrics populate
- [ ] Adjustments trigger when needed
- [ ] Regime multipliers apply correctly
- [ ] Tail trades execute (if enabled)

### Post-Market

- [ ] Review coverage over day
- [ ] Check adjustment frequency
- [ ] Verify regime adjustments worked
- [ ] Review tail costs vs protection

---

## Troubleshooting

### Coverage Not Updating

1. **Check if overlay is running:**
   ```bash
   grep -i "tail.*hedge" /tmp/kite_api_live.log | tail -10
   ```

2. **Check metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep tail_short_vol
   ```

3. **Check short premium:**
   - Are short-vol strategies actually trading?
   - Is short_notional > 0?

### Coverage Too High/Low

1. **Adjust targets:**
   - Lower `target_tail_coverage_pct` if too high
   - Raise `min_tail_coverage_pct` if too low

2. **Check regime multipliers:**
   - May be too aggressive in HIGH_EVENT/CHAOTIC
   - Adjust `coverage_multiplier` values

### Tails Not Executing

1. **Check rebalance interval:**
   - May be too long
   - Reduce `interval_minutes`

2. **Check thresholds:**
   - `min_tail_gap_pct` may be too high
   - `min_notional_change_pct` may be too high

---

## Next Steps

1. ✅ **Wire position store** - Enable actual position tracking
2. ✅ **Test in observe mode** - Verify calculations
3. ✅ **Enable tail trades** - Start with small coverage
4. ⏳ **Add tail roll logic** - Auto-roll near expiry
5. ⏳ **Add profit-taking** - Take profit on big wins
6. ⏳ **Event calendar integration** - Boost coverage around events

---

## Production Notes

**Current Limitations:**
- Position store integration is placeholder (needs actual position manager)
- Short premium calculation is simplified (needs proper notional calculation)
- Tail notional calculation is placeholder (needs position tracking)
- Option price estimation is simplified (should use market data)

**Future Enhancements:**
- Proper position store integration
- Accurate notional calculations
- Real-time option prices
- Tail roll logic
- Profit-taking logic
- Event calendar integration
- Multi-leg tail structures (butterflies, etc.)

---

## Understanding Tail Hedging

**Why tail hedges:**
- Short vol strategies profit from time decay
- But vulnerable to large moves (tail risk)
- Deep OTM puts provide cheap protection

**How it works:**
- Buy deep OTM puts (5-8% below spot)
- If market crashes, puts appreciate
- Offsets losses from short vol positions
- Cost is small compared to protection

**Regime adjustment:**
- In calm markets: Lower coverage (cheaper)
- In volatile markets: Higher coverage (more protection)
- Automatically adjusts based on R1 regime

**Cost vs benefit:**
- Tail hedges cost premium (drag on returns)
- But provide insurance against tail events
- Net effect: Lower volatility of returns, better risk-adjusted returns


