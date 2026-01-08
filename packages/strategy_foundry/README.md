# Aggressive Intraday Strategy Foundry

Automated research lab that generates, backtests, and selects intraday trading strategies (5m, 15m) for Indian markets (NIFTY/SENSEX).

## Overview

- **Generates** thousands of strategies using a grammar (Trend, Breakout, Mean Reversion).
- **Backtests** on 5m and 15m data (Yahoo Finance fallback).
- **Ranks** using Sharpe, Calmar, Stability, and Robustness.
- **Publishes** a JSON signal artifact for consumption.
- **Safe**: No live trading by default. Signal only.

## Usage

### Run Manually

```bash
export PYTHONPATH=.
python packages/strategy_foundry/run_hourly.py
```

### Configuration

- `configs/foundry.yaml`: Global settings (risk limits, timeframes).
- `configs/instrument_map.yaml`: Symbol mapping (Research -> Live).

### Output

Results are stored in `results/`:
- `live_signal.json`: Current trading signal.
- `champions/`: Saved champion strategies.
- `runs/`: Logs and leaderboards.

## Live Trading

Live trading is **OFF** by default.
To enable:
1. Set `ENABLE_LIVE=true` env var.
2. Create `approvals/ALLOW_LIVE.txt`.
3. Ensure core kill-switches are inactive.

## Data

Uses `requests` to fetch data from Yahoo Finance if Core data is unavailable. Caches to CSV.
