# Strategy Foundry

Self-generating strategy lab. Automates the research, backtesting, and selection of trading strategies.

## Overview
- **Hybrid Architecture**: Reuses `packages/core` for indicators/market hours but implements independent research stack.
- **Hourly Runner**: Generates, backtests, and ranks strategies every hour.
- **Walk-Forward Analysis**: Uses rigorous out-of-sample testing to prevent overfitting.
- **Live Signal**: Publishes `live_signal.json` for consumption by execution systems (no direct ordering).

## Architecture
- `data/`: Data loaders (Yahoo Finance) and caching.
- `factory/`: Strategy grammar and random generator.
- `backtest/`: Vectorized backtest engine and metrics.
- `selection/`: Ranking logic and Champion Store.
- `live/`: Signal publishing.

## Running Locally
1. Install dependencies:
   ```bash
   pip install pandas numpy requests structlog
   ```
2. Run hourly job:
   ```bash
   python packages/strategy_foundry/run_hourly.py --fast
   ```

## CI/CD
Runs hourly via GitHub Actions.
- PRs run in FAST_MODE (fewer candidates, fewer folds).
- Scheduled runs perform full analysis.

## Live Trading
By default, this module ONLY outputs JSON signals.
To enable live execution, `packages/core` must be configured to read `results/live_signal.json` AND `approvals/ALLOW_LIVE.txt` must exist.
