# Backtesting Protocol

## Assumptions
- **Execution:** Next bar Open.
- **Slippage:** 5bps per side (configurable).
- **Tax:** 3bps (approx STT/GST).
- **Spread Guard:** 2bps penalty for entry (choppiness filter).

## Data
- **Source:** Yahoo Finance (Proxy if needed).
- **Timeframes:** 5m (Primary), 15m (Secondary), 1D (Sanity).
- **Timezone:** IST (Asia/Kolkata).

## Walk-Forward Analysis
- **Folds:** 4 (Default), 2 (Fast Mode).
- **Training:** Used to select params (simulated via random generation here).
- **OOS:** Used for Ranking. Only OOS metrics count.

## Rejection Criteria
- **Trades:** < 80 (5m) or < 40 (15m).
- **MaxDD:** > 30%.
- **Profit Factor:** < 1.1.
- **Sanity:** Daily Sharpe < -0.2 (Catastrophic failure check).

## Limitations
- Yahoo data may be delayed or incomplete for intraday.
- No real tick data; assumes OHLC limits.
- Costs are approximations.
