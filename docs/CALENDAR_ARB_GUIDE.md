# Calendar Volatility Arbitrage (T1) - Term-Structure Guide

## Overview

The Calendar Volatility Arbitrage (T1) strategy exploits relative IV differences between **nearest weekly** and **nearest monthly** options on NIFTY/BANKNIFTY.

**Core idea:** When weekly IV >> monthly IV (panic/event), profit from IV convergence or time decay.

---

## How It Works

### 1. Entry (09:30 - 13:30 IST)

**Conditions:**
- Within entry window
- R1 regime allows (LOW_MEAN_REVERT, MEDIUM_TREND, or HIGH_EVENT)
- Term ratio: `IV_weekly / IV_monthly >= 1.20`
- Term spread: `IV_weekly - IV_monthly >= 0.05` (5 vol points)
- Monthly IV rank between 0.20 - 0.85
- Minimum 5 days between expiries
- Liquidity checks pass

**Action:**
- **Long Calendar Spread:**
  - **Sell** ATM weekly call + put
  - **Buy** ATM monthly call + put (same strikes)
- Net: Short high-term IV (weekly), long lower-term IV (monthly)
- Limited tail risk (both legs are ATM)

### 2. Exit Conditions

**Time-based:**
- Hard exit at 15:10 IST
- Max hold time: 3 days

**Decay/Expiry:**
- If weekly expiry is tomorrow (≤1 day) and not moving → exit

**PnL-based:**
- Target: +1.0% of capital used
- Stop: -0.7% of capital used

---

## Configuration

Edit `configs/calendar_arb.yaml`:

### Entry Settings
- `entry_window`: Time window for opening calendars
- `min_days_between_expiries`: Minimum gap (5 days)
- `term_ratio_long_cal_min`: Minimum IV ratio (1.20)
- `term_spread_long_cal_min`: Minimum spread (0.05)
- `term_ratio_extreme`: Extreme threshold for larger sizing (1.40)
- `min_iv_rank_monthly` / `max_iv_rank_monthly`: IV rank filters
- `base_lots_per_underlying` / `max_lots_per_underlying`: Position sizing

### Exit Settings
- `hard_exit_time`: Force close time ("15:10")
- `max_hold_days`: Safety timeout (3 days)
- `pnl_target_pct`: Profit target (1.0%)
- `pnl_stop_pct`: Loss stop (0.7%)
- `decay_exit_days`: Exit when weekly expiry is this close (1 day)

### Risk Settings
- `max_capital_pct`: Max capital per calendar (5%)
- `max_daily_loss_pct`: Daily loss cap (0.7%)
- `max_open_calendars_per_underlying`: Max concurrent calendars (2)

### Integration
- `require_r1_regime`: Check R1 before entry (true)
- `allowed_r1_regimes`: ["LOW_MEAN_REVERT", "MEDIUM_TREND", "HIGH_EVENT"]

---

## Integration

### Enable in Config

Add to `configs/app.yaml`:

```yaml
strategies:
  - name: "CalendarArb"
    enabled: true
    params: {}
```

The strategy will automatically load from `configs/calendar_arb.yaml`.

### R1 Integration

T1 respects R1 regime:
- Only trades when R1 regime is in allowed list
- Checks `context.features.get("regime")` or signal tags
- Can be explicitly routed by R1 (see below)

### Option: Route from R1

To make R1 route certain regimes → T1:

1. Edit `RegimeVolEngine.STRUCTURE_TO_STRATEGY`:
```python
"calendar_spread": "CalendarArb"
```

2. Add to `regime_vol_engine.yaml`:
```yaml
LOW_MEAN_REVERT:
  actions:
    secondary_structure: "calendar_spread"  # or primary_structure
```

---

## Metrics

T1 exposes Prometheus metrics:

- `calendar_arb_iv_weekly{underlying}` - Weekly ATM IV
- `calendar_arb_iv_monthly{underlying}` - Monthly ATM IV
- `calendar_arb_term_ratio{underlying}` - IV ratio (weekly/monthly)
- `calendar_arb_term_spread{underlying}` - IV spread (weekly - monthly)
- `calendar_arb_books_opened{underlying}` - Books opened today
- `calendar_arb_books_closed{underlying,reason}` - Books closed (reason: time/decay_exit/max_hold_days/pnl_target/pnl_stop)
- `calendar_arb_pnl_pct{underlying}` - Current PnL % (when wired)

### Grafana Panels

**1. Term Structure Metrics**
```promql
calendar_arb_term_ratio{underlying="NIFTY"}
calendar_arb_term_spread{underlying="NIFTY"}
```

**2. IV Comparison**
```promql
calendar_arb_iv_weekly{underlying="NIFTY"}
calendar_arb_iv_monthly{underlying="NIFTY"}
```

**3. Books Opened/Closed**
```promql
sum(increase(calendar_arb_books_opened[1d])) by (underlying)
sum(increase(calendar_arb_books_closed[1d])) by (underlying, reason)
```

**4. PnL % (when wired)**
```promql
calendar_arb_pnl_pct{underlying="NIFTY"}
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
   - Term ratio/spread values
   - Books opening/closing
   - Entry window respected
   - R1 regime checks working

3. **Check:**
   - Calendars only open when term structure is favorable
   - Exits trigger correctly (time, decay, PnL)

### Phase 2: Small LIVE (Week 3-4)

1. **Switch to LIVE:**
   ```yaml
   mode: "LIVE"
   max_capital_pct: 0.03  # Still small
   base_lots_per_underlying: 1  # 1 lot only
   ```

2. **Tight caps:**
   - `max_daily_loss_pct: 0.5` (tighter)
   - `max_open_calendars_per_underlying: 1` (more conservative)

3. **Monitor closely:**
   - Real PnL vs expected
   - Slippage on entry/exit
   - Execution latency

### Phase 3: Scale Up (Week 5+)

1. **Gradually increase:**
   - `max_capital_pct: 0.05` → `0.08`
   - `base_lots_per_underlying: 1` → `2` (if stable)

2. **Relax constraints:**
   - Only if PnL is positive
   - Only if term structure opportunities are consistent

---

## Testing Checklist

### Pre-Market

- [ ] Config loaded correctly
- [ ] Strategy appears in `/state` endpoint
- [ ] Metrics endpoints accessible
- [ ] R1 regime check working

### During Market Hours

- [ ] Books open in entry window (09:30-13:30)
- [ ] Term ratio/spread thresholds respected
- [ ] Hard exit at 15:10 works
- [ ] Decay exit triggers when weekly expiry is tomorrow
- [ ] No trades in disallowed R1 regimes

### Post-Market

- [ ] All books closed by EOD
- [ ] Metrics recorded correctly
- [ ] PnL tracking accurate (when wired)
- [ ] Term structure metrics populate

---

## Troubleshooting

### Books Not Opening

1. **Check entry window:**
   ```bash
   # Current time should be 09:30-13:30 IST
   date
   ```

2. **Check R1 regime:**
   ```bash
   curl http://localhost:8000/metrics | grep algo_vol_regime_code
   ```
   Should be LOW_MEAN_REVERT (1), MEDIUM_TREND (2), or HIGH_EVENT (3)

3. **Check term structure:**
   ```bash
   curl http://localhost:8000/metrics | grep calendar_arb_term_ratio
   ```
   Should be >= 1.20

4. **Check logs:**
   ```bash
   grep -i "calendar.*arb" /tmp/kite_api_live.log | tail -20
   ```

### Term Structure Not Favorable

1. **Check IV values:**
   ```bash
   curl http://localhost:8000/metrics | grep calendar_arb_iv
   ```
   Verify weekly IV > monthly IV

2. **Check ratio/spread:**
   ```bash
   curl http://localhost:8000/metrics | grep calendar_arb_term
   ```
   Should meet thresholds

3. **Market conditions:**
   - Term structure distortions are event-driven
   - May not occur every day
   - More common during earnings, events, volatility spikes

### Excessive Exits

1. **Check exit reasons:**
   ```bash
   curl http://localhost:8000/metrics | grep calendar_arb_books_closed
   ```
   Review which exit reasons are most common

2. **Adjust thresholds:**
   - If too many decay exits: Increase `decay_exit_days`
   - If too many time exits: Adjust `hard_exit_time`
   - If PnL exits: Review PnL calculation

---

## Next Steps

1. ✅ **Test in PAPER mode** - Verify basic flow
2. ✅ **Monitor term structure** - Check ratio/spread values
3. ✅ **Tune thresholds** - Adjust based on observed behavior
4. ⏳ **Wire PnL tracking** - Add `calendar_arb_pnl_pct` metric
5. ⏳ **Enhance IV calculation** - Use proper Black-Scholes or market data
6. ⏳ **Add position tracking** - Track multi-leg positions accurately

---

## Production Notes

**Current Limitations:**
- IV calculation is simplified (should use Black-Scholes inversion or market data)
- Multi-leg order support is placeholder (needs proper order management)
- PnL calculation is simplified (needs mark-to-market with real option prices)

**Future Enhancements:**
- Real-time IV from options chain
- Proper multi-leg order execution
- Mark-to-market PnL with real option prices
- Support for reverse calendars (when monthly IV >> weekly IV)
- Auto-roll functionality (roll weekly leg as it expires)

---

## Understanding Term Structure

**Normal term structure:**
- Monthly IV > Weekly IV (time premium)
- Term ratio < 1.0

**Inverted term structure (opportunity):**
- Weekly IV > Monthly IV (panic/event)
- Term ratio > 1.0
- This is when T1 trades

**Why it works:**
1. **IV convergence:** Weekly IV often reverts to monthly IV
2. **Time decay:** Weekly leg decays faster (theta advantage)
3. **Event resolution:** Events resolve, weekly IV collapses

**Risks:**
- If event continues, weekly IV stays high
- If event worsens, both IVs spike (limited loss due to long leg)
- Liquidity issues on weekly options near expiry


