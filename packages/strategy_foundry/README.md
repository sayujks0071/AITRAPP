# Strategy Foundry

Aggressive Intraday StrategyFoundry that self-generates strategies, backtests them on 15m + 5m (primary) and 1D (sanity), ranks them with strong anti-overfit gates, and publishes a live signal JSON during market hours.

## Directory Structure

- `configs/`: Configuration files (`foundry.yaml`, `instrument_map.yaml`)
- `data/`: Data loading and caching
- `adapters/`: Adapters to Core components
- `factory/`: Strategy generation grammar
- `backtest/`: Vectorized backtest engine
- `selection/`: Ranking and promotion logic
- `live/`: Signal publishing
- `results/`: Output artifacts

## Usage

Run hourly:
```bash
python -m packages.strategy_foundry.run_hourly
```

## Configuration

Edit `configs/foundry.yaml` to adjust:
- Risk parameters (slippage, costs)
- Ranking weights
- Candidate generation counts

## Live Signals

Generated at `results/live_signal.json`.
Only published if Market is Open and a valid Champion exists.
