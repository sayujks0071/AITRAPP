# Strategy Foundry

An autonomous lab that self-generates, backtests, ranks, and publishes intraday trading strategies for Indian indices.

## Overview
- **Timeframes**: 5m, 15m
- **Data**: Yahoo Finance (Proxies for NIFTY/SENSEX)
- **Engine**: Vectorized + Event-Driven Hybrid
- **Output**: `live_signal.json` (No auto-execution)

## Usage
Run manually:
```bash
python packages/strategy_foundry/run_hourly.py
```

Fast mode (for dev):
```bash
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

## Structure
- `factory/`: Strategy grammar and generator
- `backtest/`: Engine and metrics
- `data/`: Caching loader
- `results/`: Run artifacts

## Live Signals
The system publishes `results/live_signal.json` only when:
1. Market is Open
2. A robust champion is found
3. Live gating criteria are met
