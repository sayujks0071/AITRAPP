# Strategy Foundry

## Overview
Self-generating intraday strategy lab. Generates, backtests, ranks, and publishes signals.

## Schedule
Runs hourly via GitHub Actions.

## Output
Results are stored in `packages/strategy_foundry/results/`.
- `live_signal.json`: The current actionable signal (if market open and eligible).
- `runs/`: Historical run data.
- `champions/`: Best strategies.

## Usage
Run manually (Fast Mode):
```bash
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

## Configuration
See `packages/strategy_foundry/configs/foundry.yaml`.
