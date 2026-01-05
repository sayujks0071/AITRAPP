# Aggressive Intraday Strategy Foundry

Automated research lab that generates, backtests, and selects intraday trading strategies for Indian markets.

## Overview

The foundry runs hourly (during market hours) to:
1.  **Generate** random strategies based on a grammar of valid trading components.
2.  **Backtest** these strategies on 5m and 15m timeframes using Walk-Forward Optimization.
3.  **Rank** them based on risk-adjusted returns, stability, and robustness.
4.  **Promote** a "Champion" strategy if it beats the incumbent.
5.  **Publish** a live signal artifact (`live_signal.json`) if the champion signals an entry.

## Architecture

-   `adapters/`: Bridges to Core system (Indicators, Market Hours).
-   `data/`: Manages data loading and caching (Yahoo Finance).
-   `factory/`: Strategy grammar and random generation.
-   `backtest/`: Vectorized + Event-driven hybrid engine.
-   `selection/`: Ranking and promotion logic.
-   `live/`: Signal publication.

## Usage

### Run Manually

```bash
# Full mode
python packages/strategy_foundry/run_hourly.py

# Fast mode (fewer candidates, fewer folds)
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

### Outputs

-   **Run Artifacts**: `results/runs/<timestamp>/` (candidates, metrics, leaderboard).
-   **Live Signal**: `results/live_signal.json`.
-   **Champion**: `results/champions/current.json`.

## Configuration

-   `configs/foundry.yaml`: Foundry settings (thresholds, weights).
-   `configs/instrument_map.yaml`: Symbol mapping (Research -> Paper -> Live).
