# Aggressive Intraday Strategy Foundry

Automated lab for generating, testing, and selecting intraday trading strategies (NIFTY/SENSEX).

## Overview

- **Timeframes**: 5m and 15m.
- **Generation**: Grammar-based (ORB, Breakout, Mean Reversion).
- **Validation**: Walk-Forward Analysis (OOS) + Daily Sanity Check.
- **Output**: Live signal JSON artifact (no automated execution).

## Directory Structure

- `adapters/`: Connectors to core system (Market Hours, Indicators, Costs).
- `backtest/`: Intraday engine, metrics, walk-forward analysis.
- `configs/`: Instrument maps and foundry settings.
- `data/`: Yahoo downloader and caching.
- `factory/`: Strategy grammar and generator.
- `live/`: Signal publishing logic.
- `results/`: Run artifacts, leaderboards, champions.
- `selection/`: Ranking and promotion logic.

## Running Locally

```bash
# Full Run
python -m packages.strategy_foundry.run_hourly

# Fast Mode (fewer candidates, fewer folds)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

## Live Signals

Signals are published to `results/live_signal.json` only when:
1. Market is Open.
2. A valid Champion exists.
3. Gates are passed.

## CI/CD

Runs hourly via GitHub Actions.
