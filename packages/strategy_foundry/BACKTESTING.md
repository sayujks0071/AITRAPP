# Backtesting Methodology

## Assumptions
- **Execution**: Signal on Close -> Execute on Next Open.
- **Slippage**: 5 bps per side (configurable).
- **Costs**: 5 bps per side (configurable, covers brokerage + taxes).
- **Data**: 5-minute and 15-minute OHLCV.
- **Session**: 09:15 to 15:30 IST.
- **Forced Exit**: All positions closed by 15:25 IST.

## Walk-Forward Evaluation
To prevent overfitting, we use Walk-Forward Evaluation (WFE) or Cross-Validation:
- Data is split into multiple folds (default 4).
- Strategy is evaluated on each fold as an "Out-of-Sample" (OOS) period.
- Ranking is based on the average OOS performance.

## Metrics
- **Sharpe Ratio**: Annualized (Risk-Free Rate = 0).
- **Calmar Ratio**: Annualized CAGR / Max Drawdown.
- **Stability**: Standard deviation of Sharpe across folds.
- **Turnover**: Average return per trade (Proxy for trade quality).

## Rejection Criteria
Strategies are rejected if:
- **Trades**: < 80 (5m) or < 40 (15m).
- **Drawdown**: > 30%.
- **Profit Factor**: < 1.1 (OOS).
- **Sanity Check**: > 50% of PnL comes from the last 30 minutes of the day ("Late Day Dependence").
- **Overtrading**: > 10 trades per day on average.
