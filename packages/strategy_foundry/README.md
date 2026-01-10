# Strategy Foundry

## Overview
Autonomous intraday strategy research and signal generation lab.
Generates, backtests, ranks, and promotes trading strategies for NIFTY/SENSEX indices.
Produces live trading signals as JSON artifacts.

## Usage

### Run Manually
```bash
# Fast mode (fewer candidates, no promotion)
export FAST_MODE=1
python packages/strategy_foundry/run_hourly.py

# Full mode
export FAST_MODE=0
python packages/strategy_foundry/run_hourly.py
```

### Outputs
Results are stored in `packages/strategy_foundry/results/`:
- `runs/<timestamp>/`: Individual run artifacts (leaderboards, metrics)
- `champions/`: Promoted strategy configurations
- `live_signal.json`: Current live trading signal (if eligible)

## Configuration
- `configs/foundry.yaml`: Runtime settings (timeframes, folding, etc.)
- `configs/instrument_map.yaml`: Symbol mappings (Research -> Live)
