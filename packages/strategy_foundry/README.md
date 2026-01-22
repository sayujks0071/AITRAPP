# Aggressive Intraday StrategyFoundry

This package implements an automated strategy research lab ("Foundry") that:
1.  Generates intraday trading strategies (grammar-based).
2.  Backtests them on 5m and 15m data with strict OOS (Out-of-Sample) validation.
3.  Ranks them to find robust "Champions".
4.  Publishes a `live_signal.json` artifact for potential execution.

## Directory Structure

- `configs/`: Configuration files.
- `data/`: Data loading and caching (Yahoo-style fetcher).
- `adapters/`: Interfaces to `packages.core`.
- `factory/`: Strategy generation grammar and logic.
- `backtest/`: Engine, metrics, walk-forward validation.
- `selection/`: Ranking and champion management.
- `live/`: Signal publishing.
- `results/`: Run artifacts and champion stores.

## Usage

**Run Hourly (via Cron/CI):**
```bash
python3 -m packages.strategy_foundry.run_hourly
```

**Fast Mode (for CI testing):**
```bash
FAST_MODE=1 python3 -m packages.strategy_foundry.run_hourly
```

## Outputs

- `results/runs/<timestamp>/`: Contains candidates, metrics, and logs for a run.
- `results/champions/`: Contains the current best strategies per instrument.
- `results/live_signal.json`: The latest actionable signal (if eligible).
