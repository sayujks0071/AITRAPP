# Strategy Foundry

An automated lab for generating, backtesting, and selecting intraday trading strategies.

## Overview

The Strategy Foundry runs hourly to:
1. Fetch latest data (Yahoo Finance Proxy for Intraday Indices).
2. Generate random strategy candidates based on a grammar (Breakout, Trend, Mean Reversion).
3. Backtest candidates on 5m and 15m timeframes (Walk-Forward Analysis).
4. Validate top candidates on Daily (1D) data for sanity.
5. Rank and promote a "Champion" strategy.
6. Publish `live_signal.json` if the champion is eligible and market is open.

## Directory Structure

- `configs/`: Instrument maps.
- `data/`: Data loaders and caching (CSV).
- `factory/`: Strategy grammar and generation logic.
- `backtest/`: Engine, metrics, and walk-forward analysis.
- `selection/`: Ranking and champion storage.
- `live/`: Signal publishing.
- `results/`: Run artifacts and live signals.

## Usage

### Run Manually

```bash
# Fast Mode (fewer candidates, fewer folds)
python -m packages.strategy_foundry.run_hourly --fast

# Full Mode
python -m packages.strategy_foundry.run_hourly
```

### Outputs

- `packages/strategy_foundry/results/runs/<timestamp>/leaderboard.csv`: Ranking of candidates.
- `packages/strategy_foundry/results/champions/current.json`: The current reigning champion.
- `packages/strategy_foundry/results/live_signal.json`: The latest actionable signal (or status SKIPPED).

## Live Trading

By default, this system **DOES NOT** place orders. It only produces `live_signal.json`.
To enable live execution, an external system must consume this JSON and explicit approvals (`approvals/ALLOW_LIVE.txt`) must be present.
