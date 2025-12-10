# NIFTY ORB Validation - Run Instructions

## Prerequisites

```bash
# Ensure dependencies are installed
source venv/bin/activate  # or: python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 1. Run Validation

```bash
source venv/bin/activate

python scripts/tune_walkforward.py \
  --strategy ORB \
  --symbol NIFTY \
  --start 2023-01-01 --end 2025-11-15 \
  --in-sample 60d --out-of-sample 20d --stride 20d \
  --grid grids/orb_small.json \
  --cost-model configs/costs/india_equities.yaml \
  --max-trials 256 --seed 1337 \
  --export reports/tuning/orb_nifty_walkforward.json
```

## 2. Quick Readout

```bash
# Best parameters
jq '.best_params' reports/tuning/orb_nifty_walkforward.json

# Best metrics
jq '.best_metrics' reports/tuning/orb_nifty_walkforward.json

# PBO and risk metrics
jq '{pbo: .pbo, mar: .best_mar, sharpe: .best_metrics.oos_sharpe_mean}' reports/tuning/orb_nifty_walkforward.json

# Acceptance criteria check
jq '{
  sharpe: .best_metrics.oos_sharpe_mean,
  mar: .best_mar,
  win_rate: .best_metrics.oos_win_rate_mean,
  pbo: .pbo,
  pass: (.best_metrics.oos_sharpe_mean >= 0.8 and .best_mar >= 0.5 and .best_metrics.oos_win_rate_mean >= 45 and .pbo <= 0.2)
}' reports/tuning/orb_nifty_walkforward.json
```

## 3. Write Back to Configs (if PASS)

### Manual Write-Back

Edit `configs/app.yaml`:

```yaml
strategies:
  orb:
    session_or: "15m"
    atr_len: 14
    atr_mult: 1.0      # From .best_params.atr_mult
    confirm_candles: 1 # From .best_params.confirm_candles
    vol_z: 0.5         # From .best_params.vol_z
    widen_n: 1         # From .best_params.widen_n
    cool_down: 10      # From .best_params.cool_down
```

### Automated Write-Back

```bash
python scripts/write_back_params.py \
  --input reports/tuning/orb_nifty_walkforward.json \
  --config configs/app.yaml \
  --strategy orb

# Dry run first
python scripts/write_back_params.py \
  --input reports/tuning/orb_nifty_walkforward.json \
  --config configs/app.yaml \
  --strategy orb \
  --dry-run
```

## 4. Mirror to Canary Config

After updating `configs/app.yaml`, copy the same params to `configs/canary_live.yaml`:

```yaml
strategies:
  orb:
    session_or: "15m"
    atr_len: 14
    atr_mult: 1.0      # Same as app.yaml
    confirm_candles: 1
    vol_z: 0.5
    widen_n: 1
    cool_down: 10
```

## Common Issues

### Missing Dependencies
```bash
pip install structlog pandas numpy pyyaml
```

### No Trades in Some Folds
- This is OK - the script handles empty results
- If too many empty folds, reduce filters in grid:
  - Lower `vol_z` threshold
  - Reduce `confirm_candles`
  - Increase `widen_n` tolerance

### Date Parsing Issues
- Ensure dates are in `YYYY-MM-DD` format
- Check that historical data exists for the date range

## Next Steps After PASS

1. ✅ Write back params to `configs/app.yaml`
2. ✅ Mirror to `configs/canary_live.yaml`
3. ⏭️ Run BANKNIFTY ORB validation
4. ⏭️ Extend to TrendPullback
5. ⏭️ Extend to OptionsRanker


