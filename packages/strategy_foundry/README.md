# Aggressive Intraday Strategy Foundry

Automated lab for generating, backtesting, and ranking intraday trading strategies on 5m and 15m timeframes.

## Structure

*   `configs/`: Configuration files (weights, instruments, thresholds).
*   `data/`: Data loading and caching (Yahoo Finance fallback).
*   `factory/`: Strategy grammar and generation logic.
*   `backtest/`: Vectorized backtest engine and metrics.
*   `selection/`: Ranking, promotion, and champion storage.
*   `live/`: Signal publishing (JSON artifacts only).

## Usage

### Run Locally

```bash
# Full Run
python -m packages.strategy_foundry.run_hourly

# Fast Mode (fewer candidates, fewer folds)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

### Outputs

Results are stored in `packages/strategy_foundry/results/`:

*   `runs/<timestamp>/`: Per-run artifacts (candidates, metrics, leaderboard).
*   `champions/`: Historical champions and `current.json`.
*   `live_signal.json`: Current live signal (generated only during market hours).

## Live Trading

Live trading is **OFF** by default. The system only publishes `live_signal.json`.
To enable execution, a separate bridge must be run with `ENABLE_LIVE=true` and explicit approvals.
