# PyPortfolioOpt - Portfolio Optimization Overview

## Source
- **Repository**: https://github.com/robertmartin8/PyPortfolioOpt
- **Language**: Python
- **Type**: Modern portfolio theory optimization

## Key Strategies

### 1. Mean-Variance Optimization
- **Logic**: Maximize Sharpe ratio or minimize volatility
- **Use Case**: Multi-asset portfolios
- **Performance**: Author-reported backtests show improved risk-adjusted returns

### 2. Risk Parity
- **Logic**: Equal risk contribution from each asset
- **Use Case**: Balanced portfolios
- **Performance**: More stable returns in some backtests

### 3. Black-Litterman Model
- **Logic**: Combine market views with historical data
- **Use Case**: Portfolio allocation with views
- **Performance**: Better alignment with market expectations

## India Market Adaptation Notes

### Mean-Variance Optimization Adaptation
- Use Indian market covariance estimates (NIFTY components, sector indices)
- Include transaction costs in optimization
- Respect lot sizes and margin requirements
- Rebalance frequency: Daily or weekly
- Include realistic costs (12-15 bps per rebalance)

### Risk Parity Adaptation
- Use Indian market risk estimates
- Include transaction costs
- Respect margin requirements
- Filter by liquidity

## Use Cases for Indian Markets
1. **NIFTY Component Allocation**: Allocate across NIFTY 50 stocks
2. **Sector Rotation**: Allocate across sector indices
3. **Index + Options**: Combine index futures with options for hedging

## Performance Disclaimer
⚠️ All performance numbers are author-reported backtests, NOT live performance. Use for research and inspiration only.

