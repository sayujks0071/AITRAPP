# Backtesting Methodology

## Assumptions

- **Execution**: Signal at Close[i] -> Execute at Open[i+1].
- **Intraday**: All positions flattened at 15:25 IST.
- **Costs**: 5 bps per side + 5 bps slippage (Total 10 bps per side).
- **Data**: Yahoo Finance Intraday (5m/15m) used as research proxy for NIFTY/SENSEX.
  - *Limitation*: Yahoo data may have gaps or delayed prints. Live execution must use broker ticks.
- **Timezone**: Asia/Kolkata (IST).

## Evaluation

### Walk-Forward Analysis
We use a time-series split (Walk-Forward) approach to validate strategies.
- 5m/15m data is split into 4 folds (Train/Test).
- Ranking relies ONLY on Out-of-Sample (Test) performance.

### Sanity Checks
- **1D Sanity**: Strategies are run on Daily bars to ensure they don't blow up on higher timeframes (though logic may differ).
- **Intraday Sanity**: Checks for "Late Day Dependence" (profits only in last 30 mins) to avoid closing-auction anomalies.

## Rejection Criteria
- Max Drawdown > 30%
- OOS Sharpe < 0.2
- Less than 3 profitable folds
- Catastrophic 1D performance
