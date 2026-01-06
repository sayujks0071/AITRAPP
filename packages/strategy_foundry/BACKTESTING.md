# Backtesting Methodology

## Data
- Sources: Yahoo Finance (Research), Core/Broker (Live/Paper).
- Caching: CSV in `data/cache/`.
- Timeframes: 5m, 15m (Primary), 1D (Sanity).

## Engine Assumptions
- **Execution**: Signal at Close -> Trade at Open of NEXT bar.
- **Session**: Mandatory flat by 15:25 IST.
- **Costs**: 3bps + 2bps slippage per side. Spread guard penalty for entries.

## Evaluation
- **Walk-Forward**: 4 Folds (default). OOS performance determines rank.
- **Sanity**:
  - Daily robustness check (must not crash on 1D).
  - Intraday turnover check (no overtrading).

## Ranking
- **Blended Score**: Sharpe (25%), Calmar (25%), CAGR (20%), Stability (15%).
- **Promotion**: Beat current champion by 10% score OR 5% less drawdown.
