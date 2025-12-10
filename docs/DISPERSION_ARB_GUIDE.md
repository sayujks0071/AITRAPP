# Dispersion Arbitrage (D1) - Index vs Sector Guide

## Overview

The Dispersion Arbitrage (D1) strategy exploits volatility divergence between **parent index** (NIFTY) and **sector index** (BANKNIFTY).

**Core idea:** When sector vol >> parent vol (dispersion), profit from the divergence by:
- **Long vol in sector** (long straddle/strangle)
- **Short vol in parent** (short strangle/condor)

---

## How It Works

### 1. Entry (10:00 - 14:00 IST)

**Conditions:**
- Within entry window
- R1 regime allows (LOW_MEAN_REVERT or MEDIUM_TREND)
- **Correlation ≥ 0.6** (reasonably high)
- **Vol ratio ≥ 1.5** (sector RV ≥ 1.5x parent RV)
- **IV ratio ≥ 1.2** (sector IV ≥ 1.2x parent IV)
- Liquidity checks pass

**Action:**
- **Long Calendar Spread:**
  - **Long vol in sector:** Buy ATM straddle/strangle in BANKNIFTY
  - **Short vol in parent:** Sell OTM strangle in NIFTY
- Net: Long sector vol, short parent vol
- Sizes scaled to keep net vega ≈ 0 or slightly long

### 2. Exit Conditions

**Time-based:**
- Hard exit at 15:10 IST

**Structural:**
- **Correlation breakdown:** Correlation < 0.4
- **Vol normalization:** Vol ratio < 1.2 (dispersion faded)

**PnL-based:**
- Target: +1.0% of capital used
- Stop: -0.8% of capital used

---

## Configuration

Edit `configs/dispersion_arb.yaml`:

### Entry Settings
- `entry_window`: Time window for opening pairs
- `rv_lookback_minutes`: Realized vol window (60 minutes)
- `corr_lookback_minutes`: Correlation window (60 minutes)
- `min_corr`: Minimum correlation (0.6)
- `min_vol_ratio_sector_parent`: Minimum vol ratio (1.5)
- `min_iv_ratio_sector_parent`: Minimum IV ratio (1.2)
- `lots_sector_long_vol` / `lots_parent_short_vol`: Position sizing

### Exit Settings
- `hard_exit_time`: Force close time ("15:10")
- `pnl_target_pct`: Profit target (1.0%)
- `pnl_stop_pct`: Loss stop (0.8%)
- `corr_break_min`: Correlation breakdown threshold (0.4)
- `vol_ratio_normalise_max`: Vol normalization threshold (1.2)

### Risk Settings
- `max_capital_pct`: Max capital per pair (5%)
- `max_daily_loss_pct`: Daily loss cap (0.8%)

### Integration
- `require_r1_regime`: Check R1 before entry (true)
- `allowed_r1_regimes`: ["LOW_MEAN_REVERT", "MEDIUM_TREND"]

---

## Integration

### Enable in Config

Add to `configs/app.yaml`:

```yaml
strategies:
  - name: "DispersionArb"
    enabled: true
    params: {}
```

The strategy will automatically load from `configs/dispersion_arb.yaml`.

### R1 Integration

D1 respects R1 regime:
- Only trades when R1 regime is in allowed list
- Checks `context.features.get("regime")` or signal tags
- Works best in LOW_MEAN_REVERT (calm parent, hyper sector)

### Pair Configuration

Configure pairs in `dispersion_arb.yaml`:

```yaml
pairs:
  - parent: "NIFTY"
    sector: "BANKNIFTY"
  # Can add more pairs later:
  # - parent: "NIFTY"
  #   sector: "FINNIFTY"
```

---

## Metrics

D1 exposes Prometheus metrics:

- `dispersion_arb_rv_parent{parent,sector}` - Parent realized vol
- `dispersion_arb_rv_sector{parent,sector}` - Sector realized vol
- `dispersion_arb_vol_ratio{parent,sector}` - Vol ratio (sector/parent)
- `dispersion_arb_corr{parent,sector}` - Correlation
- `dispersion_arb_iv_ratio{parent,sector}` - IV ratio (sector/parent)
- `dispersion_arb_books_opened{parent,sector}` - Books opened today
- `dispersion_arb_books_closed{parent,sector,reason}` - Books closed
- `dispersion_arb_pnl_pct{parent,sector}` - Current PnL % (when wired)

### Grafana Panels

**1. Dispersion Metrics**
```promql
dispersion_arb_vol_ratio{parent="NIFTY", sector="BANKNIFTY"}
dispersion_arb_iv_ratio{parent="NIFTY", sector="BANKNIFTY"}
```

**2. Correlation**
```promql
dispersion_arb_corr{parent="NIFTY", sector="BANKNIFTY"}
```

**3. Realized Vols**
```promql
dispersion_arb_rv_parent{parent="NIFTY", sector="BANKNIFTY"}
dispersion_arb_rv_sector{parent="NIFTY", sector="BANKNIFTY"}
```

**4. Books Opened/Closed**
```promql
sum(increase(dispersion_arb_books_opened[1d])) by (parent, sector)
sum(increase(dispersion_arb_books_closed[1d])) by (parent, sector, reason)
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
   - Vol ratio/spread values
   - Correlation stability
   - Books opening/closing
   - Entry window respected

3. **Check:**
   - Pairs only open when dispersion is favorable
   - Exits trigger correctly (time, correlation, vol normalization)

### Phase 2: Small LIVE (Week 3-4)

1. **Switch to LIVE:**
   ```yaml
   mode: "LIVE"
   max_capital_pct: 0.03  # Still small
   lots_sector_long_vol: 1  # 1 lot only
   lots_parent_short_vol: 1
   ```

2. **Tight caps:**
   - `max_daily_loss_pct: 0.6` (tighter)
   - `max_pair_books_per_pair: 1` (one at a time)

3. **Monitor closely:**
   - Real PnL vs expected
   - Correlation stability during trades
   - Execution latency

### Phase 3: Scale Up (Week 5+)

1. **Gradually increase:**
   - `max_capital_pct: 0.05` → `0.08`
   - `lots_sector_long_vol: 1` → `2` (if stable)

2. **Relax constraints:**
   - Only if PnL is positive
   - Only if dispersion opportunities are consistent

---

## Testing Checklist

### Pre-Market

- [ ] Config loaded correctly
- [ ] Strategy appears in `/state` endpoint
- [ ] Metrics endpoints accessible
- [ ] R1 regime check working
- [ ] Pair configuration correct

### During Market Hours

- [ ] Books open in entry window (10:00-14:00)
- [ ] Vol ratio/correlation thresholds respected
- [ ] Hard exit at 15:10 works
- [ ] Correlation breakdown exit triggers
- [ ] Vol normalization exit triggers
- [ ] No trades in disallowed R1 regimes

### Post-Market

- [ ] All books closed by EOD
- [ ] Metrics recorded correctly
- [ ] PnL tracking accurate (when wired)
- [ ] Correlation/vol metrics populate

---

## Troubleshooting

### Books Not Opening

1. **Check entry window:**
   ```bash
   # Current time should be 10:00-14:00 IST
   date
   ```

2. **Check R1 regime:**
   ```bash
   curl http://localhost:8000/metrics | grep algo_vol_regime_code
   ```
   Should be LOW_MEAN_REVERT (1) or MEDIUM_TREND (2)

3. **Check dispersion metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep dispersion_arb_vol_ratio
   ```
   Should be >= 1.5

4. **Check correlation:**
   ```bash
   curl http://localhost:8000/metrics | grep dispersion_arb_corr
   ```
   Should be >= 0.6

5. **Check logs:**
   ```bash
   grep -i "dispersion.*arb" /tmp/kite_api_live.log | tail -20
   ```

### Correlation Too Low

1. **Market conditions:**
   - Correlation can break during major events
   - Strategy requires reasonably high correlation to work
   - May not trade on days with low correlation

2. **Adjust threshold:**
   - Lower `min_corr` if too restrictive (but be careful)
   - Default 0.6 is reasonable for NIFTY-BANKNIFTY

### Vol Ratio Not Meeting Threshold

1. **Market conditions:**
   - Dispersion opportunities are event-driven
   - May not occur every day
   - More common during sector-specific news/events

2. **Check realized vols:**
   ```bash
   curl http://localhost:8000/metrics | grep dispersion_arb_rv
   ```
   Verify sector RV > parent RV

---

## Next Steps

1. ✅ **Test in PAPER mode** - Verify basic flow
2. ✅ **Monitor dispersion metrics** - Check vol ratio, correlation
3. ✅ **Tune thresholds** - Adjust based on observed behavior
4. ⏳ **Wire PnL tracking** - Add `dispersion_arb_pnl_pct` metric
5. ⏳ **Enhance correlation calculation** - Use proper time series correlation
6. ⏳ **Add position tracking** - Track multi-leg positions accurately
7. ⏳ **Extend to more pairs** - Add FINNIFTY, MIDCPNIFTY pairs

---

## Production Notes

**Current Limitations:**
- Correlation calculation is simplified (should use proper time series)
- Realized vol calculation uses approximation (should use proper intraday vol)
- Multi-leg order support is placeholder (needs proper order management)
- PnL calculation is simplified (needs mark-to-market with real option prices)
- Peer context fetching is simplified (needs proper context store)

**Future Enhancements:**
- Real-time correlation from shared price history
- Proper intraday realized vol calculation
- Multi-leg order execution
- Mark-to-market PnL with real option prices
- Support for multiple pairs simultaneously
- Auto-roll functionality
- Vega-neutral sizing

---

## Understanding Dispersion

**Normal correlation:**
- NIFTY and BANKNIFTY move together
- Correlation typically 0.7-0.9
- Vol ratios similar

**Dispersion regime (opportunity):**
- Sector (BANKNIFTY) becomes hyperactive
- Parent (NIFTY) stays relatively calm
- Correlation still reasonably high (≥0.6)
- Vol ratio > 1.5

**Why it works:**
1. **Vol convergence:** Sector vol often reverts to parent vol
2. **Correlation stability:** High correlation means pair relationship holds
3. **Event resolution:** Sector-specific events resolve, vol normalizes

**Risks:**
- If correlation breaks, pair relationship fails
- If dispersion widens further, losses can mount
- Liquidity issues on sector options during events
- Execution risk on multi-leg orders
