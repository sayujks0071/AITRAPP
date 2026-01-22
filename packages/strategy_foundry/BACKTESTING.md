# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D).
- **Execution**: Signal on Close -> Execute on Next Open.
- **Slippage**: 5 bps per side (configurable).
- **Costs**: 3.5 bps per side (configurable, covers brokerage + taxes).
- **Data**: Daily OHLCV (NIFTY/SENSEX).
- **Session**: Standard Market Days.

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
- **Trades**: < 30 (Default).
- **Drawdown**: > 35%.
- **Profit Factor**: < 1.0 (OOS).
- **Sanity Check**: Basic data integrity and trade validation.

<!-- Verified -->
