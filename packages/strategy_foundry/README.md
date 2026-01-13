# Strategy Foundry

## Overview
An aggressive intraday strategy lab that self-generates, backtests, ranks, and publishes signals for NIFTY/Indices.

## Architecture
- **Factory**: Generates strategies using a defined grammar (Breakout, Trend, Mean Reversion).
- **Backtest**: Walk-forward analysis on 5m/15m data with 1D sanity checks.
- **Data**: Caches Yahoo Finance data (CSV).
- **Live**: Publishes `live_signal.json` during market hours (Signal only, no auto-execution).

## Usage

### Run Manually
```bash
export PYTHONPATH=.
python packages/strategy_foundry/run_hourly.py
```

### Fast Mode
```bash
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

## Outputs
- `results/runs/<ts>/leaderboard.csv`: Rankings
- `results/champions/current.json`: Current best strategy
- `results/live_signal.json`: Live trading signal (if eligible)

## Gating
Live signals are only published if:
1. Champion Sharpe > 1.2
2. Champion MaxDD < 20%
3. Market is Open
4. Data is fresh

## Dependencies
- pandas, numpy
- requests
- structlog
- pyyaml
