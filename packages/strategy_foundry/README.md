# Strategy Foundry

Automated research lab for generating, backtesting, and ranking trading strategies for NIFTY/SENSEX.

## Overview
This module runs hourly to:
1. Fetch latest Daily (1D) data (falling back to Yahoo Finance).
2. Generate random strategy candidates based on a defined grammar.
3. Backtest candidates using a vectorized engine with Walk-Forward Evaluation.
4. Rank candidates based on OOS Sharpe, Calmar, Stability, and Turnover.
5. Promote a "Champion" strategy if it beats the incumbent.
6. Publish a `live_signal.json` artifact for potential execution.

## Usage

### Run Manually
```bash
# Full Mode
python -m packages.strategy_foundry.run_hourly

# Fast Mode (fewer candidates, fewer folds)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

### Outputs
Results are stored in `results/`:
- `runs/<timestamp>/`: Contains `metrics.csv`, candidates, and run logs.
- `champions/current.json`: The current reigning champion strategy.
- `live_signal.json`: The latest trading signal (only generated during market hours if eligible).
- `leaderboard.md`: Current top strategies.

## Architecture
- **Data**: `data/loader.py` (Yahoo Finance + Cache).
- **Factory**: `factory/generator.py` (Strategy Grammar).
- **Backtest**: `backtest/engine.py` (Vectorized, Hybrid Loop, 1D).
- **Selection**: `selection/ranker.py` (OOS Scoring).
- **Live**: `live/signal_publisher.py` (Signal Generation).
