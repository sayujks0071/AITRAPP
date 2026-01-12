# Strategy Foundry

A self-generating strategy lab that operates autonomously to find, backtest, and select trading strategies for NIFTY/SENSEX.

## Overview

- **Generates** strategies using a grammar of indicators (Trend, Mean Reversion, Volatility).
- **Backtests** using a daily vectorized engine with slippage and costs.
- **Validates** using Walk-Forward Analysis (Out-of-Sample).
- **Ranks** candidates using a composite score (Sharpe, Calmar, CAGR).
- **Publishes** a `live_signal.json` artifact (NO real orders placed).

## Directory Structure

- `data/`: Data loading and caching (Yahoo Finance).
- `factory/`: Strategy grammar and generation.
- `backtest/`: Vectorized backtesting engine.
- `selection/`: Ranking and champion promotion.
- `results/`: Output artifacts (candidates, signals, leaderboard).

## Usage

### Local Run

```bash
# Fast Mode (fewer candidates)
export FAST_MODE=1
python packages/strategy_foundry/run_hourly.py
```

### CI/CD

Runs hourly via GitHub Actions.

## Output

- `results/live_signal.json`: The latest trading signal (if eligible).
- `results/leaderboard.md`: Current top strategies.
- `results/runs/<timestamp>/`: Detailed run logs and candidates.
