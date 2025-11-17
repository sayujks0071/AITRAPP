# R1 Verification Guide

## Quick Runtime Smoke Test

### 1. Verify Engine is Loaded

Run the verification script:

```bash
python3 scripts/verify_r1.py
```

**Expected output:**
- ✅ RegimeVolEngine found in strategies
- ✅ All metrics exist (algo_vol_regime_code, algo_vol_iv_rank, etc.)
- ✅ Regime flags for all regimes
- ✅ Current regime codes for NIFTY and BANKNIFTY

**Check logs for initialization:**
```bash
grep -i "regime.*vol.*engine" /tmp/kite_api_live.log | tail -5
```

Should see:
```
"RegimeVolEngine initialized", "underlyings": ["NIFTY", "BANKNIFTY"], ...
```

---

### 2. Check Regime Metrics

**Via Prometheus endpoint:**
```bash
curl http://localhost:8000/metrics | grep algo_vol_
```

**Or use PromQL queries:**
```promql
# Current regime codes
algo_vol_regime_code{underlying="NIFTY"}
algo_vol_regime_code{underlying="BANKNIFTY"}

# Feature values
algo_vol_iv_rank{underlying="NIFTY"}
algo_vol_atr_pct{underlying="NIFTY"}
algo_vol_rv_iv_ratio{underlying="NIFTY"}
algo_vol_vix_rank{underlying="NIFTY"}

# Regime flags (one-hot)
algo_vol_regime_flag{underlying="NIFTY",regime="LOW_MEAN_REVERT"}
algo_vol_regime_flag{underlying="NIFTY",regime="MEDIUM_TREND"}
```

**If metrics are missing/NaN:**
- Check that `MarketContextAdapter` methods are working
- Verify bars data is available in `StrategyContext`
- Check logs for errors in feature computation

---

### 3. Confirm Features Populate

**Check feature values are reasonable:**
- `algo_vol_iv_rank`: Should be 0.0-1.0
- `algo_vol_atr_pct`: Should be > 0 (typically 0.3-2.0)
- `algo_vol_rv_iv_ratio`: Should be > 0 (typically 0.5-1.5)
- `algo_vol_vix_rank`: Should be 0.0-1.0

**If values are NaN or 0:**
- `iv_rank()`: Check IV percentile in context
- `atr()`: Verify bars_5s has enough data (>= 14 bars)
- `realised_vol()`: Check bars_5s has enough data (>= 10 bars)
- `vix_rank()`: Currently uses IV rank as proxy (needs real VIX data)

---

## Market Hours Test: Verify Routing

### 1. Monitor Regime + Signals Together

**Run the routing test:**
```bash
./scripts/test_r1_routing.sh BANKNIFTY
```

**Or manually:**
```bash
# Watch regime
watch -n 5 'curl -s http://localhost:8000/metrics | grep algo_vol_regime_code{underlying="BANKNIFTY"}'

# Watch signals by strategy
watch -n 5 'curl -s http://localhost:8000/metrics | grep trader_signals_total{strategy='
```

### 2. Expected Behaviors

#### LOW_MEAN_REVERT (code: 1)
- **Expected signals from:**
  - `IronCondor` (iron_condor)
  - `OptionsRanker` with short strangle config (fallback)
- **Check:** `trader_signals_total{strategy="IronCondor"}` should increment

#### MEDIUM_TREND (code: 2)
- **Expected signals from:**
  - `OptionsRanker` with credit spread config (primary)
  - `ORB` (index_sniper, secondary)
- **Check:** Both strategies should generate signals

#### HIGH_EVENT (code: 3)
- **Expected signals from:**
  - `OptionsRanker` with long straddle config (primary)
  - Or no signals if fallback to stay_flat
- **Check:** Either signals or complete silence

#### CHAOTIC (code: 4)
- **Expected:** No signals
- **Check:** `trader_signals_total` should NOT increment for any strategy

### 3. Verify Entry Regime Tagging

**Check position/order logs:**
```bash
# In your position close handler, verify:
# position.features.get("entry_regime") is set

# Or check database:
# SELECT entry_regime, COUNT(*) FROM positions GROUP BY entry_regime;
```

**Expected:** Every opened position should have `entry_regime` tag set.

---

## Simple Backtest Sanity Check

### 1. Run Historical Replay (if available)

```python
# Pseudo-code for backtest
for date in historical_dates:
    for bar in bars_for_date:
        context = create_context(bar)
        signals = regime_engine.generate_signals(context)
        
        # Log regime + signals
        log_regime(date, context.instrument.symbol, regime, signals)
```

### 2. Generate CSV Report

**Columns:**
- `date, time, underlying, regime, strategy, trade_id, pnl`

**Check:**
- ✅ All regimes appear at least sometimes
- ✅ CHAOTIC days → bot stayed flat (no trades)
- ✅ MEDIUM_TREND correlates with trending days on charts
- ✅ LOW_MEAN_REVERT → mostly iron condors/strangles

---

## Threshold Tuning

### If Bot is Too Flat

**Adjustments:**
1. **Raise `low_iv_rank`** (e.g., 0.25 → 0.30)
   - More time in MEDIUM_TREND
   - Less time in LOW_MEAN_REVERT

2. **Lower `high_iv_rank`** (e.g., 0.65 → 0.60)
   - Less time in CHAOTIC/HIGH_EVENT
   - More time in MEDIUM_TREND

3. **Relax `atr_pct_low`** (e.g., 0.40 → 0.35)
   - MEDIUM_TREND triggers more often

**Edit:** `configs/regime_vol_engine.yaml`

### If Bot is Too Aggressive in Bad Days

**Tighten CHAOTIC:**
1. **Lower `rv_iv_low`** (e.g., 0.60 → 0.55)
2. **Raise `rv_iv_high`** (e.g., 1.10 → 1.15)
3. **Raise `atr_pct_high`** (e.g., 1.50 → 1.60)

**Reduce HIGH_EVENT capital:**
- Change `capital_pct: 0.15` → `0.10` or `0.05`

**⚠️ Always test in PAPER mode first!**

---

## Monitoring Queries

### Grafana/Prometheus Queries

**Current regime:**
```promql
last_over_time(algo_vol_regime_code{underlying="NIFTY"}[5m])
```

**Regime over time:**
```promql
algo_vol_regime_code{underlying="NIFTY"}
```

**Time in each regime (last 30 days):**
```promql
avg_over_time(algo_vol_regime_flag{underlying="NIFTY"}[30d])
```

**Signals by strategy (verify routing):**
```promql
sum(increase(trader_signals_total{strategy=~"IronCondor|OptionsRanker|ORB"}[1h])) by (strategy)
```

**PnL by regime (once wired):**
```promql
sum(increase(algo_pnl_realized{underlying="NIFTY"}[30d])) by (regime)
```

---

## Troubleshooting

### R1 Not Generating Signals

1. **Check if enabled:**
   ```bash
   curl http://localhost:8000/state | jq '.strategies[] | select(.name=="RegimeVolEngine")'
   ```

2. **Check regime classification:**
   ```bash
   curl http://localhost:8000/metrics | grep algo_vol_regime_code
   ```
   - If always UNKNOWN (0) → check feature computation
   - If CHAOTIC (4) → expected, no signals

3. **Check strategy registry:**
   - Verify child strategies are loaded
   - Check `STRUCTURE_TO_STRATEGY` mapping

### Features Always NaN

1. **Check bars data:**
   - Verify `context.bars_5s` has >= 14 bars
   - Check `context.latest_tick` is not None

2. **Check IV percentile:**
   - Verify `context.iv_percentile` is set
   - If None, `MarketContextAdapter` falls back to estimated values

3. **Check logs:**
   ```bash
   grep -i "regime\|vol" /tmp/kite_api_live.log | tail -20
   ```

---

## Next Steps

1. ✅ Run `verify_r1.py` to confirm basic setup
2. ✅ Monitor during market hours with `test_r1_routing.sh`
3. ✅ Verify entry_regime tagging on trades
4. ✅ Tune thresholds based on observed behavior
5. ✅ Wire PnL tracking by regime (future enhancement)


