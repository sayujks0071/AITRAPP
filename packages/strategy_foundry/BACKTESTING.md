# Backtesting Methodology

## Engine
- **Timeframe**: Daily (1D)
- **Execution**: Next-Bar Open. Signals generated at Close `i` are executed at Open `i+1`.
- **Costs**:
  - Slippage: 5 bps per side.
  - All-in Cost: 5 bps per side (Brokerage + STT + Impact).
- **Compounding**: Returns are compounded. Initial capital: 100,000.

## Walk-Forward Evaluation
To prevent overfitting, strategies are evaluated using a Walk-Forward approach:
1. Data is split into `K` segments (Folds).
2. Strategy is tested on each segment independently.
3. Ranking is based on aggregated Out-Of-Sample (OOS) metrics across all folds.
4. **Sanity Checks**:
   - Must have trades in at least 50% of folds.
   - Max Drawdown < 25%.
   - Sharpe > 1.0 (for promotion).

## Scoring
The composite score determines the ranking:
- **Sharpe Ratio**: 30% weight
- **Calmar Ratio**: 25% weight
- **CAGR**: 20% weight
- **Stability**: 15% weight (Inverse of rolling Sharpe dispersion)
- **Turnover Penalty**: -10% weight (Penalizes excessive trading)

## Strategy Grammar
Strategies are composed of:
- **Entry Rules**: AND combination of Trend (EMA, Supertrend) or Mean Reversion (RSI) blocks.
- **Exit Rules**: OR combination of technical exits (RSI Overbought).
- **Risk Overlay**:
  - Stop Loss (ATR based)
  - Take Profit (ATR based, optional)
  - Time Stop (Max bars)
  - Trailing Stop
