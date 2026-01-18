# Strategy Foundry

Self-generating strategy lab that evolves trading strategies using `packages/core` primitives.

## Structure

- `data/`: Data loading and caching (Yahoo Finance).
- `adapters/`: Adapters to core (Indicators, Market Hours, Costs).
- `factory/`: Strategy generation grammar and random search.
- `backtest/`: Vectorized backtest engine.
- `selection/`: Ranking and champion promotion.
- `live/`: Signal publishing (JSON only).

## Usage

### Run Hourly
```bash
python -m packages.strategy_foundry.run_hourly
```

### Fast Mode (for CI)
```bash
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

## Output

Artifacts are stored in `packages/strategy_foundry/results/`.
- `runs/<timestamp>/`: Metrics and candidate details.
- `champions/`: Historical champions.
- `live_signal.json`: Latest trade signal (if market open).
