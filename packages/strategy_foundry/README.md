# Strategy Foundry

A self-generating strategy lab that runs hourly to discover, backtest, and select trading strategies for NIFTY and SENSEX.

## Architecture

- **Hybrid Model**: Reuses `packages/core` for indicators and market logic via adapters.
- **Autonomous**: Generates strategies, tests them, and promotes champions without human intervention.
- **Safe**: No live execution. Publishes `live_signal.json` artifacts only.

## Directory Structure

- `data/`: Data loading and caching (CSV).
- `factory/`: Strategy grammar and generation.
- `backtest/`: Vectorized backtest engine.
- `selection/`: Ranking and champion storage.
- `live/`: Signal publishing.

## Usage

Run manually:
```bash
export PYTHONPATH=.
python packages/strategy_foundry/run_hourly.py
```

Fast mode (fewer candidates/folds):
```bash
export FAST_MODE=1
python packages/strategy_foundry/run_hourly.py
```

## CI/CD

Runs hourly via GitHub Actions. Artifacts are uploaded for inspection.
