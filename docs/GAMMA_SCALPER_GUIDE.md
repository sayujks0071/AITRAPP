# Gamma Scalper (G1) - Delta-Hedged Gamma Scalper Guide

## Overview

The Gamma Scalper (G1) is a volatility trading strategy that:
- **Buys ATM straddles** (long gamma position)
- **Delta hedges with futures** to keep net delta ≈ 0
- **Rebalances** when delta drifts beyond threshold
- **Exits** based on time, PnL, or vol collapse

**Core idea:** Profit from realized intraday volatility exceeding implied volatility paid.

---

## How It Works

### 1. Entry (09:20 - 11:00 IST)

**Conditions:**
- Within entry window
- R1 regime allows (MEDIUM_TREND or HIGH_EVENT)
- IV rank between 0.20 - 0.80
- RV/IV ratio ≥ 0.9 (realized vol close to or above implied)
- Liquidity checks pass

**Action:**
- Select nearest weekly expiry (1-4 days)
- Buy ATM call + ATM put (straddle)
- Store state for delta tracking

### 2. Delta Hedging

**Trigger:**
- |Total Delta| > `rebalance_delta_threshold` (default: 0.15)
- Cooldown period passed (default: 60s)
- Under max rebalances (default: 25)

**Action:**
- Compute total delta (call + put + existing futures)
- Calculate futures lots needed to offset
- Place futures hedge order
- Update rebalance count

### 3. Exit Conditions

**Time-based:**
- Hard exit at 15:10 IST
- Max hold time (default: 300 minutes)

**PnL-based:**
- Target: +0.8% of capital used
- Stop: -0.6% of capital used

**Vol collapse:**
- RV/IV drops below 0.7 (vol not realizing)

---

## Configuration

Edit `configs/gamma_scalper.yaml`:

### Entry Settings
- `entry_window`: Time window for opening books
- `min_days_to_expiry` / `max_days_to_expiry`: Expiry selection
- `min_iv_rank` / `max_iv_rank`: IV rank filters
- `rv_iv_min`: Minimum RV/IV ratio
- `lots_per_underlying`: Position size

### Hedging Settings
- `target_abs_delta`: Target delta (0.10)
- `rebalance_delta_threshold`: Trigger threshold (0.15)
- `rebalance_cooldown_seconds`: Cooldown between hedges (60s)
- `max_hedge_lots`: Cap on futures exposure (3 lots)

### Exit Settings
- `hard_exit_time`: Force close time ("15:10")
- `max_hold_minutes`: Safety timeout (300)
- `pnl_target_pct`: Profit target (0.8%)
- `pnl_stop_pct`: Loss stop (0.6%)
- `vol_collapse_rv_iv_max`: Vol collapse threshold (0.7)

### Risk Settings
- `max_capital_pct`: Max capital per book (5%)
- `max_daily_loss_pct`: Daily loss cap (0.7%)
- `max_rebalances`: Max hedge operations (25)

### Integration
- `require_r1_regime`: Check R1 before entry (true)
- `allowed_r1_regimes`: ["MEDIUM_TREND", "HIGH_EVENT"]

---

## Integration

### Enable in Config

Add to `configs/app.yaml`:

```yaml
strategies:
  - name: "GammaScalper"
    enabled: true
    params: {}
```

The strategy will automatically load from `configs/gamma_scalper.yaml`.

### R1 Integration

G1 respects R1 regime:
- Only trades when R1 regime is MEDIUM_TREND or HIGH_EVENT
- Checks `context.features.get("regime")` or signal tags
- Stays flat in CHAOTIC or LOW_MEAN_REVERT

### Option B: Route from R1

To make R1 route HIGH_EVENT → G1:

Edit `RegimeVolEngine.STRUCTURE_TO_STRATEGY`:
```python
"long_straddle": "GammaScalper"  # Instead of "kurtosis_straddle"
```

---

## Metrics

G1 exposes Prometheus metrics:

- `gamma_scalper_books_opened{underlying}` - Books opened today
- `gamma_scalper_books_closed{underlying,reason}` - Books closed (reason: time/pnl_target/pnl_stop/vol_collapse)
- `gamma_scalper_abs_delta{underlying}` - Current absolute delta
- `gamma_scalper_rebalances{underlying}` - Rebalance count

### Grafana Panels

**1. Current Delta**
```promql
gamma_scalper_abs_delta{underlying="NIFTY"}
```

**2. Rebalances Today**
```promql
sum(increase(gamma_scalper_rebalances[1d])) by (underlying)
```

**3. Books Opened/Closed**
```promql
sum(increase(gamma_scalper_books_opened[1d])) by (underlying)
sum(increase(gamma_scalper_books_closed[1d])) by (underlying, reason)
```

**4. PnL % (when wired)**
```promql
gamma_scalper_pnl_pct{underlying="NIFTY"}
```

---

## Safe Rollout Plan

### Phase 1: PAPER Mode (Week 1-2)

1. **Enable in PAPER:**
   ```yaml
   mode: "PAPER"
   max_capital_pct: 0.02  # Start small
   ```

2. **Monitor:**
   - Books opening/closing
   - Delta rebalancing frequency
   - Rebalance count (should stay < 25)

3. **Check:**
   - Entry window respected
   - R1 regime checks working
   - Exits triggering correctly

### Phase 2: Small LIVE (Week 3-4)

1. **Switch to LIVE:**
   ```yaml
   mode: "LIVE"
   max_capital_pct: 0.03  # Still small
   lots_per_underlying: 1  # 1 lot only
   ```

2. **Tight caps:**
   - `max_daily_loss_pct: 0.5` (tighter)
   - `max_rebalances: 20` (more conservative)

3. **Monitor closely:**
   - Real PnL vs expected
   - Slippage on rebalances
   - Execution latency

### Phase 3: Scale Up (Week 5+)

1. **Gradually increase:**
   - `max_capital_pct: 0.05` → `0.08`
   - `lots_per_underlying: 1` → `2` (if stable)

2. **Relax constraints:**
   - Only if PnL is positive
   - Only if rebalances stay reasonable

---

## Testing Checklist

### Pre-Market

- [ ] Config loaded correctly
- [ ] Strategy appears in `/state` endpoint
- [ ] Metrics endpoints accessible
- [ ] R1 regime check working

### During Market Hours

- [ ] Books open in entry window (09:20-11:00)
- [ ] Delta hedging triggers when threshold exceeded
- [ ] Rebalance cooldown respected
- [ ] Hard exit at 15:10 works
- [ ] No trades in CHAOTIC regime

### Post-Market

- [ ] All books closed by EOD
- [ ] Metrics recorded correctly
- [ ] PnL tracking accurate (when wired)
- [ ] Rebalance count reasonable

---

## Troubleshooting

### Books Not Opening

1. **Check entry window:**
   ```bash
   # Current time should be 09:20-11:00 IST
   date
   ```

2. **Check R1 regime:**
   ```bash
   curl http://localhost:8000/metrics | grep algo_vol_regime_code
   ```
   Should be MEDIUM_TREND (2) or HIGH_EVENT (3)

3. **Check IV rank:**
   ```bash
   curl http://localhost:8000/metrics | grep algo_vol_iv_rank
   ```
   Should be 0.20-0.80

4. **Check logs:**
   ```bash
   grep -i "gamma.*scalper" /tmp/kite_api_live.log | tail -20
   ```

### Delta Not Hedging

1. **Check delta value:**
   ```bash
   curl http://localhost:8000/metrics | grep gamma_scalper_abs_delta
   ```
   Should be > 0.15 to trigger

2. **Check cooldown:**
   - Verify `last_rebalance_time` logic
   - Check if rebalance count hit max

3. **Check futures availability:**
   - Verify futures contract found
   - Check futures lot size

### Excessive Rebalances

1. **Tighten threshold:**
   - Increase `rebalance_delta_threshold` (0.15 → 0.20)

2. **Increase cooldown:**
   - `rebalance_cooldown_seconds: 60` → `120`

3. **Check Greeks calculation:**
   - Verify delta computation is accurate
   - May need proper Black-Scholes implementation

---

## Next Steps

1. ✅ **Test in PAPER mode** - Verify basic flow
2. ✅ **Monitor metrics** - Check delta, rebalances, exits
3. ✅ **Tune thresholds** - Adjust based on observed behavior
4. ⏳ **Wire PnL tracking** - Add `gamma_scalper_pnl_pct` metric
5. ⏳ **Enhance Greeks** - Use proper Black-Scholes or market data
6. ⏳ **Add position tracking** - Track existing futures positions for delta

---

## Production Notes

**Current Limitations:**
- Greeks are simplified approximations (should use Black-Scholes or market data)
- Futures position tracking is placeholder (needs integration with position manager)
- PnL calculation is simplified (needs mark-to-market)

**Future Enhancements:**
- Real-time Greeks from options chain
- Proper position tracking for delta calculation
- Mark-to-market PnL with real option prices
- Multi-leg order support (straddle as single order)


