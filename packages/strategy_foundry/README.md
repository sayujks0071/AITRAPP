# Strategy Foundry

An aggressive intraday strategy research lab that self-generates, backtests, and selects trading strategies for NIFTY/SENSEX.

## Overview
- **Timeframes**: 5m, 15m (Primary), 1D (Sanity).
- **Generation**: Randomly composes Entry/Exit blocks (RSI, EMA, Donchian, etc.).
- **Validation**: Walk-forward analysis (k-fold on time series).
- **Output**: Live signal JSON artifact (no automated execution).

## Usage
Run manually (Full Mode):
```bash
python packages/strategy_foundry/run_hourly.py
```

Run Fast Mode (fewer candidates, fewer folds):
```bash
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

## Structure
- `adapters/`: Adapters to Core (Indicators, Market Hours).
- `backtest/`: Vectorized Engine + Metrics.
- `configs/`: YAML configs.
- `data/`: Yahoo Downloader + CSV Cache.
- `factory/`: Strategy Grammar + Generator.
- `live/`: Signal Publisher.
- `results/`: Artifacts (Runs, Champions, Signals).
- `selection/`: Ranking & Promotion Logic.
