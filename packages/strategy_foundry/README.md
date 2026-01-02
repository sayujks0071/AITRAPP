# Aggressive Intraday Strategy Foundry

Automated lab for generating, backtesting, and selecting intraday trading strategies for Indian markets (NIFTY/SENSEX).

## Features
- **Generative Strategy Factory**: Uses a grammar of Entry, Exit, and Filter blocks to compose strategies.
- **Intraday Backtesting**: Supports 5m and 15m timeframes with realistic costs, slippage, and time-based exits.
- **Walk-Forward Validation**: Uses Walk-Forward Analysis (WFA) with expanding windows to ensure Out-Of-Sample (OOS) robustness.
- **Live Signal Publishing**: Generates JSON signals (`live_signal.json`) during market hours for the top-performing "Champion" strategy.

## Usage
The system is designed to run hourly via GitHub Actions.

To run locally:
```bash
# Full mode
python -m packages.strategy_foundry.run_hourly

# Fast mode (fewer candidates, fewer folds)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

## Structure
- `adapters/`: Adapters for core system utilities (market hours, indicators).
- `backtest/`: Event-driven backtesting engine.
- `configs/`: YAML configurations.
- `data/`: Data loading and caching (Yahoo Finance).
- `factory/`: Strategy grammar and generator.
- `live/`: Signal publishing logic.
- `selection/`: Ranking and champion management.
- `results/`: Output artifacts (leaderboards, signals).

## Dependencies
- pandas, numpy, requests, structlog, pyyaml
- Reuses `packages.core` where possible.
