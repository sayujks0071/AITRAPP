# Strategy Foundry

An automated lab for generating, backtesting, and selecting intraday trading strategies for Indian markets.

## Structure

- `configs/`: Configuration files (`foundry.yaml`, `instrument_map.yaml`).
- `data/`: Data loading and caching.
- `factory/`: Strategy grammar and generation.
- `backtest/`: Vectorized backtesting engine.
- `selection/`: Ranking and champion promotion logic.
- `live/`: Signal publishing.

## Usage

### Run Manually

```bash
# Fast mode (fewer candidates, faster)
python -m packages.strategy_foundry.run_hourly --fast

# Full mode
python -m packages.strategy_foundry.run_hourly
```

### Outputs

Results are stored in `packages/strategy_foundry/results/`:
- `runs/`: Execution logs and candidate metrics.
- `champions/`: JSON definitions of selected strategies.
- `live_signal.json`: The latest trading signal (if market is open).

## Live Trading

Live trading is **OFF** by default. To enable:
1. Set `ENABLE_LIVE=true` environment variable.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Verify core kill-switches are inactive.

Even then, this module only produces a JSON signal. The core execution system must consume it.
