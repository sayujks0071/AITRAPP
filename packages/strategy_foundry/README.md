# Strategy Foundry

Autonomous Intraday Strategy Research Lab.

## Overview
This module automatically generates, backtests, ranks, and promotes intraday trading strategies for NIFTY and SENSEX.

## Features
- **Generation**: Creates strategies using a grammar of Entry (Breakout, Trend, MeanRev), Exit (ATR, Time), and Filters.
- **Backtesting**: Runs on 5m and 15m data with realistic costs and slippage.
- **Validation**: Uses Walk-Forward validation (folds) and 1D Sanity checks.
- **Ranking**: Scores based on Sharpe, Calmar, CAGR, Stability, and Turnover.
- **Live Signal**: Publishes `live_signal.json` during market hours if a champion exists.

## Directory Structure
- `configs/`: YAML configurations.
- `data/`: Data loading and caching.
- `factory/`: Strategy grammar and generation.
- `backtest/`: Engine and metrics.
- `selection/`: Ranking and promotion logic.
- `live/`: Signal publishing.
- `results/`: Run artifacts and champions.

## Usage
Run manually (Fast Mode):
```bash
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

Run full (Production):
```bash
python packages/strategy_foundry/run_hourly.py
```
