# Backtesting Methodology

## Engine
- **Type**: Vectorized Signal Generation + Iterative Execution.
- **Execution**:
  - Signals generated on Bar Close.
  - Entries executed at Next Bar Open.
  - Session Close logic: Mandatory flat at 15:25 IST.
- **Costs**:
  - Slippage: 5 bps per side.
  - Brokerage: 20 INR per order.
  - Tax: 3 bps on turnover.

## Validation Protocol
### Walk-Forward
- Data is split into K sequential folds (4 for Full, 2 for Fast).
- Strategy params are fixed (generated).
- We verify if the strategy performs consistently across folds.
- **Criterion**: Profit Factor > 1.0 in at least 75% of folds.

### Sanity Checks
- **Min Trades**: 30 (Full), 10 (Fast).
- **Max Drawdown**: < 30%.
- **Sharpe**: > 0.5.
- **Daily Overlay**: Best candidates are tested on 1D timeframe. Catastrophic failure on 1D (Sharpe < -0.2) triggers warning.

## Ranking
Score is a weighted blend:
- 25% Sharpe
- 25% Calmar
- 20% Net Return
- 15% Stability (Low variance of Sharpe across folds)
- 10% Low Turnover Bonus
- 5% Intraday Sanity Check
