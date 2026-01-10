# Backtesting Methodology

## Assumptions

- **Timeframe**: Daily (1D).
- **Execution**: Market order at Open of next bar.
- **Costs**:
  - Slippage: 5 bps per side.
  - Brokerage: ₹20 flat per order.
  - Taxes: ~0.1% of turnover.

## Anti-Overfitting

We use **Walk-Forward Analysis (WFA)**:
1. Divide history into $N$ folds (default 3).
2. For each fold, we test on "Out-of-Sample" (OOS) data.
3. Strategy must perform well across multiple OOS periods.

**Sanity Checks**:
- Minimum 30 trades.
- Max Drawdown < 35%.
- Must be profitable in majority of folds.

## Ranking

Strategies are ranked by a composite score:
$$ Score = 0.3 \cdot Sharpe + 0.25 \cdot Calmar + 0.2 \cdot CAGR + 0.15 \cdot Stability $$

## Limitations

- **Daily Data**: Intraday volatility is not captured.
- **Vectorized**: Complex path-dependent logic (e.g. trailing stops) is approximated.
- **Survivorship Bias**: Index constituents are current; historical changes not modeled.
