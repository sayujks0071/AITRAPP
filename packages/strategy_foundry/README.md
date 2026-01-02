# StrategyFoundry

An autonomous, self-generating strategy lab that runs hourly.
It generates trading strategies using a genetic-like process (currently random search), backtests them on daily NIFTY/SENSEX data using a walk-forward approach, ranks them, and publishes a "live signal" for the best performing champion.

**Important:** This module does NOT execute real orders. It only outputs a JSON signal.

## Structure

- `data/`: Data loading and caching (Yahoo Finance -> CSV).
- `factory/`: Strategy grammar and generation logic.
- `backtest/`: Vectorized/Event-driven hybrid backtest engine.
- `selection/`: Walk-forward evaluation and ranking.
- `live/`: Signal publishing (JSON artifact).
- `results/`: Output directory for runs and champions.

## Usage

### Run Locally

```bash
# Set FAST_MODE=1 for quicker test run
export FAST_MODE=1
python -m packages.strategy_foundry.run_hourly
```

### Artifacts

After a run, check `packages/strategy_foundry/results/`:
- `live_signal.json`: The current trading signal (if market open).
- `leaderboard.md`: Top strategies.
- `runs/<timestamp>/`: Detailed run outputs.

## CI/CD

Runs hourly via GitHub Actions: `.github/workflows/strategy_foundry_hourly.yml`.
PRs trigger a fast mode run to verify integrity.
