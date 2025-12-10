# R1 Quick Reference Card

## Verification Commands

```bash
# Quick verification (all checks)
make verify-r1

# Or directly:
python3 scripts/verify_r1.py

# Test routing during market hours
make test-r1-routing UNDERLYING=BANKNIFTY
# Or:
./scripts/test_r1_routing.sh BANKNIFTY
```

## Key Metrics

```promql
# Current regime (0-4)
algo_vol_regime_code{underlying="NIFTY"}

# Features
algo_vol_iv_rank{underlying="NIFTY"}
algo_vol_atr_pct{underlying="NIFTY"}
algo_vol_rv_iv_ratio{underlying="NIFTY"}
algo_vol_vix_rank{underlying="NIFTY"}

# Regime flags (one-hot)
algo_vol_regime_flag{underlying="NIFTY",regime="LOW_MEAN_REVERT"}
```

## Regime Codes

| Code | Regime | Expected Strategies |
|------|--------|-------------------|
| 0 | UNKNOWN | None |
| 1 | LOW_MEAN_REVERT | Iron Condor, Short Strangle |
| 2 | MEDIUM_TREND | Credit Spread, Index Sniper |
| 3 | HIGH_EVENT | Long Straddle or Stay Flat |
| 4 | CHAOTIC | Stay Flat (no trades) |

## Quick Checks

**Is R1 loaded?**
```bash
curl http://localhost:8000/state | jq '.strategies[] | select(.name=="RegimeVolEngine")'
```

**Current regimes:**
```bash
curl -s http://localhost:8000/metrics | grep algo_vol_regime_code
```

**Signals by strategy (verify routing):**
```bash
curl -s http://localhost:8000/metrics | grep trader_signals_total{strategy=
```

## Threshold Tuning

**Too flat?**
- Raise `low_iv_rank` (0.25 → 0.30)
- Lower `high_iv_rank` (0.65 → 0.60)
- Relax `atr_pct_low` (0.40 → 0.35)

**Too aggressive?**
- Tighten CHAOTIC thresholds
- Lower HIGH_EVENT `capital_pct` (0.15 → 0.10)

**Edit:** `configs/regime_vol_engine.yaml`

## Troubleshooting

**No signals?**
1. Check regime code (if 4=CHAOTIC, expected)
2. Check if enabled: `curl http://localhost:8000/state`
3. Check logs: `grep -i regime /tmp/kite_api_live.log`

**Features NaN?**
- Verify bars data (need >= 14 bars for ATR)
- Check IV percentile in context
- Review `MarketContextAdapter` methods

## Full Documentation

- `docs/R1_VERIFICATION_GUIDE.md` - Complete testing guide
- `docs/GRAFANA_R1_DASHBOARD.md` - Grafana dashboard setup
- `docs/REGIME_VOL_ENGINE.md` - R1 architecture overview


