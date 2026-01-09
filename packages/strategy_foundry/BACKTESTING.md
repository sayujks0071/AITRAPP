# Backtesting Methodology

## Assumptions
- **Timeframe**: Daily (1D) bars.
- **Execution**: Next-Day Open. Signals generated on Close of Day T are executed at Open of Day T+1.
- **Costs**:
  - Slippage + Brokerage + Taxes approximated as 10bps (0.1%) per side on turnover.
  - This is conservative for NIFTY Index / Futures.

## Walk-Forward Analysis
To prevent overfitting, we use Walk-Forward Analysis (WFA) with an expanding window.
- **Folds**: 3 folds by default.
- **Training**: Uses data up to point K.
- **Testing**: Evaluated on unseen data from K to K+M.
- **Ranking**: Only Out-of-Sample (Testing) metrics are used for ranking.

## Metrics
- **CAGR**: Compound Annual Growth Rate.
- **Sharpe**: Annualized Sharpe Ratio (Risk-free rate = 5%).
- **MaxDD**: Maximum Drawdown.
- **Calmar**: CAGR / MaxDD.
- **Stability**: Inverse of Sharpe standard deviation across folds.

## Scoring
Composite Score =
- 30% Sharpe
- 25% Calmar
- 20% CAGR
- 15% Stability
- Turnover Penalty (implicit in net returns via costs, but explicit penalty can be added)
