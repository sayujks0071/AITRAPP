# Strategy Foundry

A self-generating strategy lab that autonomously generates, backtests, and ranks trading strategies on a Daily (1D) timeframe.

## Overview

Strategy Foundry is designed to be a "Paper First" research lab. It does not execute trades directly. Instead, it generates a `live_signal.json` artifact that can be consumed by an execution engine if specific gates are passed.

### Key Features
- **Self-Generating**: Uses a grammar-based generator to create random strategies.
- **Walk-Forward Analysis**: Validates strategies using Out-Of-Sample (OOS) data.
- **Hourly Updates**: Designed to run hourly (via CI/CD or Cron) to update rankings and signals.
- **Safe by Default**: No live execution. Strictly file-based output.

## Directory Structure

- `data/`: Data loading and caching (Yahoo Finance).
- `factory/`: Strategy grammar, generator, and registry.
- `backtest/`: Vectorized backtest engine and WFA logic.
- `selection/`: Ranking and Champion promotion logic.
- `live/`: Live signal publishing logic.
- `results/`: Artifacts (Runs, Leaderboards, Champions).

## Usage

### Run Locally

```bash
# Full Mode (50 candidates, strict checks)
python3 -m packages.strategy_foundry.run_hourly

# Fast Mode (10 candidates, relaxed checks - good for dev/CI)
FAST_MODE=1 python3 -m packages.strategy_foundry.run_hourly
```

### Outputs

- `results/leaderboard.md`: Current top strategies.
- `results/champions/current.json`: The current reigning champion details.
- `results/live_signal.json`: The trading signal for the current market session (if eligible).

## Dependencies

- `pandas`, `numpy`, `requests`, `structlog`
- `packages.core` (Adapters for Indicators, Market Hours, Costs)
