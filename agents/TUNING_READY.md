# Walk-Forward Tuning Pipeline - Ready for Validation

## ✅ Completed

1. **Tuning Engine** (`scripts/tune_walkforward.py`)
   - Walk-forward splits with expanding in-sample + fixed OOS windows
   - Bootstrap Probabilistic Sharpe with CI
   - PBO calculation
   - Cost model integration (YAML-based)
   - Slippage stress testing (+5 bps)
   - Acceptance criteria checking
   - Markdown report generation

2. **ORB Strategy Enhancements** (`packages/core/strategies/orb.py`)
   - Added `atr_mult` (ATR buffer for breakout threshold)
   - Added `vol_z` (Volume z-score filter)
   - Added `widen_n` (Range widening guard)
   - Added `cool_down` (Cooldown between signals)
   - Added `confirm_candles` (Confirmation candles)

3. **Grid & Cost Files**
   - `grids/orb_small.json` - Minimal ORB parameter grid
   - `configs/costs/india_equities.yaml` - Indian market cost model

## 🚀 Ready to Run

### Quick NIFTY ORB Validation

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

### Expected Output

- `reports/tuning/orb_nifty_walkforward.json` - Full results
- `reports/tuning/orb_nifty_walkforward.md` - Human-readable report
- Console output with acceptance criteria check

### Acceptance Criteria

**PASS if:**
- Sharpe ≥ 0.8 (deflated)
- MAR ≥ 0.5
- Win Rate ≥ 45%
- PBO ≤ 0.2
- Stress Sharpe (with +5 bps slippage) ≥ break-even

## 📋 Next Steps After Validation

1. **If PASS:**
   - Write back best params to `configs/app.yaml`
   - Run BANKNIFY ORB
   - Extend to TrendPullback
   - Extend to OptionsRanker

2. **If FAIL:**
   - Review metrics in report
   - Adjust parameter grid
   - Check data quality
   - Review cost model assumptions

## 🔧 Notes

- The grid file uses parameter names that map to strategy params (see `_map_grid_to_strategy_params`)
- Cost model includes all Indian market fees (brokerage, STT, GST, etc.)
- Walk-forward uses expanding in-sample windows (more realistic)
- PBO is a simplified approximation (full PBO requires permutation testing)

## 📊 Grid Size

The `orb_small.json` grid generates:
- `atr_len`: 3 values
- `atr_mult`: 5 values
- `confirm_candles`: 3 values
- `vol_z`: 3 values
- `widen_n`: 2 values
- `cool_down`: 2 values
- `session_or`: 1 value

**Total combinations**: 3 × 5 × 3 × 3 × 2 × 2 × 1 = **540 combinations**

With `--max-trials 256`, it will randomly sample 256 combinations.


