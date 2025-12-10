# Strategy Catalog - Ranked by India Market Suitability

This document ranks open-source strategies by their suitability for adaptation to Indian markets (NSE cash + F&O, indices).

## Ranking Criteria

1. **Adaptability**: How easily can it be adapted to Indian markets?
2. **Cost Sensitivity**: How well does it handle high transaction costs?
3. **Liquidity Requirements**: Can it work with Indian market liquidity?
4. **Regulatory Fit**: Does it respect Indian market constraints?
5. **Complexity**: Implementation complexity vs. benefit

## Tier 1: High Priority (Easy Adaptation, Cost-Effective)

### 1. SMA/EMA Crossover Momentum (vectorbt)
- **Source**: vectorbt examples
- **Type**: Momentum
- **Markets**: NSE cash, NIFTY/BANKNIFTY futures
- **Why**: Simple, cost-effective, works well with liquid indices
- **Adaptation**: 
  - Use 5s/1m bars for intraday
  - Add Indian market hours filter
  - Include realistic slippage (5-10 bps)
- **Expected Costs**: Low (fewer trades, liquid instruments)

### 2. Mean Reversion (bt framework)
- **Source**: bt framework examples
- **Type**: Mean reversion
- **Markets**: NSE cash (large/mid-cap), index futures
- **Why**: Works well in range-bound markets, cost-effective
- **Adaptation**:
  - Use ATR-based bands instead of fixed percentages
  - Filter by volatility regime
  - Respect Indian market hours
- **Expected Costs**: Low-medium (more trades but smaller size)

### 3. Trend Pullback (Freqtrade-inspired)
- **Source**: Freqtrade strategies
- **Type**: Trend following with pullbacks
- **Markets**: NSE cash, NIFTY/BANKNIFTY
- **Why**: Good risk-reward, fewer trades
- **Adaptation**:
  - EMA-based trend identification
  - ATR-based pullback zones
  - Indian market hours + EOD square-off
- **Expected Costs**: Low (selective entries)

## Tier 2: Medium Priority (Moderate Adaptation, Good Potential)

### 4. Portfolio Optimization (PyPortfolioOpt)
- **Source**: PyPortfolioOpt library
- **Type**: Portfolio allocation
- **Markets**: Multi-instrument (NIFTY components, sector indices)
- **Why**: Risk-parity allocation works well for Indian markets
- **Adaptation**:
  - Use Indian market covariance estimates
  - Include transaction costs in optimization
  - Respect lot sizes and margin requirements
- **Expected Costs**: Medium (rebalancing frequency)

### 5. RSI Mean Reversion (vectorbt)
- **Source**: vectorbt examples
- **Type**: Mean reversion (indicator-based)
- **Markets**: NSE cash, liquid stocks
- **Why**: Well-tested, works in range-bound conditions
- **Adaptation**:
  - Adjust RSI periods for Indian market characteristics
  - Add volume confirmation
  - Filter by liquidity
- **Expected Costs**: Medium (more frequent trades)

### 6. Opening Range Breakout (ORB) - Already Implemented
- **Status**: ✅ Already in AITRAPP
- **Markets**: NIFTY/BANKNIFTY futures
- **Note**: Good foundation, can be enhanced

## Tier 3: Lower Priority (Complex Adaptation, Research Phase)

### 7. Deep RL Strategies (FinRL)
- **Source**: FinRL library
- **Type**: Reinforcement learning
- **Markets**: Research phase
- **Why**: Requires significant adaptation, data requirements
- **Adaptation**:
  - Retrain on Indian market data
  - Include transaction costs in reward function
  - Adapt to Indian market microstructure
- **Expected Costs**: High (research phase)

### 8. Multi-Timeframe Momentum (NostalgiaForInfinity-inspired)
- **Source**: NostalgiaForInfinity Freqtrade strategy
- **Type**: Multi-timeframe trend following
- **Markets**: NIFTY/BANKNIFTY futures
- **Why**: Complex, but powerful if adapted correctly
- **Adaptation**:
  - Use Indian market timeframes (5s, 1m, 5m, 15m)
  - Adapt to Indian market hours
  - Include realistic costs
- **Expected Costs**: Medium (selective but complex)

## Implementation Priority

### Phase 1 (Immediate)
1. ✅ ORB (already implemented)
2. ✅ Trend Pullback (already implemented)
3. **SMA Momentum** (vectorbt-inspired) - NEW
4. **Mean Reversion** (bt-inspired) - NEW

### Phase 2 (Next)
5. **Portfolio Optimization** (PyPortfolioOpt-inspired) - NEW
6. **RSI Mean Reversion** (vectorbt-inspired) - NEW

### Phase 3 (Research)
7. Multi-timeframe strategies
8. RL-based strategies

## Cost Model Assumptions

All strategies must use realistic Indian market costs:
- **Brokerage**: ₹20 per order (equity), ₹20 per order (F&O)
- **STT**: 0.025% on equity delivery, 0.05% on options
- **Exchange Charges**: ~0.00325% (equity), ~0.002% (F&O)
- **GST**: 18% on brokerage + exchange charges
- **Slippage**: 5-10 bps (liquid), 10-20 bps (less liquid)
- **Impact Cost**: 5-15 bps for larger orders

**Total Round-Trip Cost**: ~12-15 bps for liquid instruments, 20-30 bps for less liquid.

## Market Hours

- **Cash Market**: 09:15 - 15:30 IST
- **F&O Market**: 09:15 - 15:30 IST
- **EOD Square-Off**: 15:25 IST (all positions flat)
- **Premarket Sync**: 08:55 IST

## Lot Sizes

- **NIFTY Futures**: 25
- **BANKNIFTY Futures**: 15
- **FINNIFTY Futures**: 40
- **Options**: Varies by strike (typically 25 for NIFTY, 15 for BANKNIFTY)

