# Strategy Foundry

Autonomous Quant Research & Deployment Agent.

## Overview
Strategy Foundry runs an hourly loop to:
1. Generate candidate trading strategies from a safe grammar.
2. Backtest them on NIFTY/SENSEX history.
3. Validate them using Walk-Forward Analysis.
4. Select a "Champion" strategy.
5. Publish live signals if the champion passes strict promotion gates.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the hourly loop
python -m packages.strategy_foundry.run_hourly
```

## Structure
- `factory/`: Strategy generation logic (grammar, parameters).
- `backtest/`: Backtesting engine and metrics.
- `selection/`: Ranking and promotion logic.
- `live/`: Signal publishing.
- `data/`: Data loading (Yahoo Finance) and caching.
- `adapters/`: Adapters to Core system components.

## Configuration
See `packages/strategy_foundry/configs/backtest.yaml` for parameters.
