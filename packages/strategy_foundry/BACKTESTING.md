# Backtesting Methodology

## Data Sources
- **Primary**: Core Data Provider (if available).
- **Secondary**: Yahoo Finance (`requests`-based downloader) for NIFTY/SENSEX indices.
- **Fallback**: ETF Proxies.

## Timeframes
- **5m**: Intraday tactical.
- **15m**: Intraday structural.
- **1D**: Sanity check.

## Walk-Forward Analysis
We use an expanding window approach for validation:
- Data is split into `N` folds.
- Each fold tests the strategy on "Out of Sample" data.
- Metrics are aggregated across all folds.
- Strategies with high variance across folds are penalized.

## Costs
- **Slippage**: 2.0 bps (configurable).
- **Brokerage**: Flat fee per order.
- **Tax**: STT + Exchange charges approximated.

## Gates
Candidates are rejected if:
- Trades < Minimum threshold (ensure statistical significance).
- Max Drawdown > 30%.
- Profit Factor < 1.1.
- Stability Score (positive folds) is low.
