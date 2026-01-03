# Aggressive Intraday Strategy Foundry

This module is an autonomous lab that generates, backtests, and selects intraday trading strategies.

## Directory Structure

- `configs/`: Configuration files (instrument maps, etc.)
- `data/`: Data loading and caching.
- `adapters/`: Adapters to core system.
- `factory/`: Strategy generation logic.
- `backtest/`: Backtest engine and metrics.
- `selection/`: Ranking and selection logic.
- `live/`: Live signal publishing.
- `results/`: Output artifacts.

## Usage

Run the hourly process:

```bash
python -m packages.strategy_foundry.run_hourly
```

## Configuration

Modify `configs/instrument_map.yaml` to map symbols to your broker or data source.
