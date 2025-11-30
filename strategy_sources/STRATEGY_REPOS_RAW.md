# Strategy Repositories - Raw Reference List

This document catalogs high-quality open-source trading strategy repositories and frameworks that serve as design references for building India-market-ready strategies.

## Framework Repositories

### 1. bt - Backtesting Framework
- **Repository**: https://github.com/pmorissette/bt
- **Language**: Python
- **Focus**: Backtesting framework with strategy building blocks
- **Key Features**:
  - Mean reversion strategies
  - Momentum strategies
  - Portfolio allocation strategies
  - Risk management utilities
- **Use Cases**: Mean reversion, pairs trading, portfolio optimization

### 2. vectorbt - Vectorized Backtesting
- **Repository**: https://github.com/polakowo/vectorbt
- **Language**: Python
- **Focus**: Fast vectorized backtesting with NumPy/Pandas
- **Key Features**:
  - SMA/EMA crossover strategies
  - RSI-based strategies
  - Portfolio optimization
  - Performance analytics
- **Use Cases**: Technical indicator strategies, momentum trading

### 3. FinRL - Deep Reinforcement Learning
- **Repository**: https://github.com/AI4Finance-Foundation/FinRL
- **Language**: Python
- **Focus**: RL-based trading strategies
- **Key Features**:
  - DQN, PPO, A2C agents
  - Multi-asset portfolio optimization
  - Risk-aware trading
  - Paper trading integration
- **Use Cases**: Adaptive strategies, portfolio management

### 4. Freqtrade - Cryptocurrency Trading Bot
- **Repository**: https://github.com/freqtrade/freqtrade
- **Language**: Python
- **Focus**: Automated cryptocurrency trading
- **Key Features**:
  - Technical indicator strategies
  - Custom strategy framework
  - Backtesting engine
  - Paper trading mode
- **Use Cases**: Momentum strategies, breakout trading

### 5. NostalgiaForInfinity - Freqtrade Strategy
- **Repository**: https://github.com/iterativv/NostalgiaForInfinity
- **Language**: Python (Freqtrade)
- **Focus**: Advanced multi-timeframe strategy
- **Key Features**:
  - Multi-timeframe analysis
  - Dynamic stop-loss
  - Trend following
  - Risk management
- **Use Cases**: Trend following, multi-timeframe strategies

### 6. PyPortfolioOpt - Portfolio Optimization
- **Repository**: https://github.com/robertmartin8/PyPortfolioOpt
- **Language**: Python
- **Focus**: Modern portfolio theory
- **Key Features**:
  - Mean-variance optimization
  - Risk parity
  - Black-Litterman model
  - Efficient frontier
- **Use Cases**: Portfolio allocation, risk budgeting

## Strategy Examples

### Mean Reversion Strategies
- **bt**: Mean reversion on price deviations from moving averages
- **vectorbt**: RSI-based mean reversion
- **Freqtrade**: Bollinger Bands mean reversion

### Momentum Strategies
- **vectorbt**: SMA crossover momentum
- **Freqtrade**: MACD momentum
- **NostalgiaForInfinity**: Multi-timeframe momentum

### Portfolio Strategies
- **PyPortfolioOpt**: Risk-parity allocation
- **FinRL**: RL-based portfolio optimization
- **bt**: Equal-weight and risk-parity portfolios

## Important Notes

⚠️ **Performance Disclaimer**: All performance numbers mentioned in strategy repositories are:
- Author-reported backtest results
- NOT live or guaranteed performance
- Strictly for research and inspiration
- May not account for realistic transaction costs
- May not be applicable to Indian markets without adaptation

## India Market Adaptation Requirements

When adapting these strategies:
1. **Market Hours**: 09:15-15:30 IST (cash), check F&O timing
2. **Transaction Costs**: Include brokerage (₹20/order), STT, exchange charges, GST
3. **Slippage**: 5-10 bps for liquid instruments, higher for illiquid
4. **Lot Sizes**: Respect NSE lot sizes for futures/options
5. **No Overnight Leverage**: Indian brokers have strict margin requirements
6. **Impact Costs**: Higher than US markets, especially for large orders

