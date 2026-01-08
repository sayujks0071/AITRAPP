# Backtesting Methodology

## Data Sources

1. **Core**: If available, high-quality broker data.
2. **Yahoo Finance**: Fallback. 5m/15m data (last 60 days).

## Execution Model

- **Signals**: Generated on Bar Close.
- **Entry**: Next Bar Open.
- **Costs**: 5bps slippage + 2bps transaction cost per side.
- **Intraday**:
  - Entries allowed 09:15 - 15:20 IST.
  - Hard close at 15:25 IST.
  - No overnight positions.

## Walk-Forward Analysis

Strategies are evaluated on Out-of-Sample (OOS) data.
- **Fast Mode**: 2 folds.
- **Full Mode**: 4 folds.

## Sanity Checks

- **1D Sanity**: Top intraday candidates are checked on Daily data to ensure they aren't counter to major trends (fragility check).
- **Filters**:
  - Min Trades: 40
  - Min Sharpe: 1.0
  - Max Drawdown: 30%
