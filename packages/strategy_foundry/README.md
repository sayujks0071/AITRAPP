# Aggressive Intraday Strategy Foundry

This module is an autonomous lab that generates, backtests, and selects intraday trading strategies for Indian markets (NIFTY/SENSEX).

## Features

- **Self-Generating Strategies**: Uses a grammar-based approach to compose entry/exit/risk blocks.
- **Intraday Focus**: Optimized for 5m and 15m timeframes with strict session boundaries (flat by 15:25).
- **Walk-Forward Validation**: Uses rolling OOS windows to prevent overfitting.
- **Sanity Checks**: Includes 1D daily sanity checks and "late-day dependence" penalties.
- **Live Signal Publishing**: Publishes a JSON signal artifact only when a champion meets strict criteria.

## Usage

### Hourly Run

The system is designed to run hourly via GitHub Actions or cron.

```bash
python packages/strategy_foundry/run_hourly.py
```

### Configuration

- `packages/strategy_foundry/configs/foundry.yaml`: Tuning parameters, weights, and thresholds.
- `packages/strategy_foundry/configs/instrument_map.yaml`: Symbol mapping for Research, Paper, and Live.

### Output

Results are stored in `packages/strategy_foundry/results/`:
- `runs/<timestamp>/`: Detailed metrics and candidates for each run.
- `champions/`: Persisted champion strategies.
- `live_signal.json`: The latest actionable signal (if eligible).

## Dependencies

Lightweight dependencies only:
- pandas, numpy
- requests (for Yahoo Finance data)
- structlog, pyyaml

## Live Trading

By default, this module **does not** place orders. It only writes `live_signal.json`.
To enable execution, an external bridge must consume this JSON, guarded by `ENABLE_LIVE=true` and `approvals/ALLOW_LIVE.txt`.
