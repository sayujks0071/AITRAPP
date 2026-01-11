# Strategy Foundry

Self-generating strategy lab for daily index strategies (NIFTY/SENSEX).

## Overview
- **Hybrid Architecture**: Reuses `packages/core` for indicators/market hours but maintains isolated research logic.
- **Hourly Runs**: Generates new strategies, backtests them, and ranks them.
- **Champion Model**: Promotes strategies that beat the incumbent on OOS metrics.
- **Live Signals**: Publishes `live_signal.json` (no execution).

## Directory Structure
- `data/`: Data loading and caching (Yahoo Finance).
- `adapters/`: Adapters to Core logic.
- `factory/`: Strategy grammar and generation.
- `backtest/`: Vectorized backtest engine.
- `selection/`: Ranking and promotion logic.
- `live/`: Signal publishing.

## How to Run
1. Install dependencies: `pip install -r requirements.txt` (or min: pandas, numpy, httpx, structlog).
2. Run: `python packages/strategy_foundry/run_hourly.py`

## Modes
- **FAST_MODE**: (Default in PRs) Generates 10 candidates, 2 folds.
- **PRODUCTION**: (Default in Cron) Generates 50 candidates, 3 folds.

## Signal Output
Located at `packages/strategy_foundry/results/live_signal.json`.
Format:
```json
{
  "timestamp_ist": "2023-10-27 10:00:00+05:30",
  "champion_id": "ab123...",
  "signal": 1,
  "status": "OK"
}
```
