# FinRL - RL Equity Strategies Overview

## Source
- **Repository**: https://github.com/AI4Finance-Foundation/FinRL
- **Language**: Python
- **Type**: Deep reinforcement learning for trading

## Key Strategies

### 1. DQN (Deep Q-Network)
- **Logic**: Q-learning with deep neural networks
- **Use Case**: Single asset trading
- **Performance**: Author-reported backtests show adaptive behavior

### 2. PPO (Proximal Policy Optimization)
- **Logic**: Policy gradient method
- **Use Case**: Portfolio optimization
- **Performance**: Better risk-adjusted returns in some backtests

### 3. A2C (Advantage Actor-Critic)
- **Logic**: Actor-critic method
- **Use Case**: Multi-asset trading
- **Performance**: Adaptive to market conditions

## India Market Adaptation Notes

### Challenges
- Requires significant retraining on Indian market data
- Transaction costs must be included in reward function
- Market microstructure differences (Indian markets have different patterns)
- Data requirements (need historical tick/bar data)

### Adaptation Approach
1. Retrain models on NSE historical data
2. Include transaction costs (brokerage, STT, slippage) in reward
3. Adapt to Indian market hours and constraints
4. Use paper trading mode for validation

## Status
⚠️ **Research Phase**: RL strategies require significant adaptation and are not ready for immediate implementation.

## Performance Disclaimer
⚠️ All performance numbers are author-reported backtests, NOT live performance. Use for research and inspiration only.

