# Regime-Switching Volatility Engine (R1)

## Overview

The Regime-Switching Volatility Engine (R1) is a **meta-strategy** that sits above your A-G strategies and routes trades based on volatility regimes. It doesn't replace your existing strategies—it intelligently selects which ones to activate based on current market conditions.

## How It Works

### 1. Feature Computation

On each scan cycle, R1 computes a feature vector for each underlying (NIFTY, BANKNIFTY):

- **IV Rank**: Implied volatility percentile (0-1)
- **IV Percentile**: Historical IV percentile
- **RV/IV Ratio**: Realized volatility / Implied volatility
- **ATR %**: Average True Range as percentage of spot price
- **Trend Strength**: EMA-based trend alignment (0-1)
- **VIX Rank**: VIX percentile (0-1)
- **VIX Slope**: Rate of change in VIX

### 2. Regime Classification

Based on computed features, R1 classifies the market into one of four regimes:

#### **LOW_MEAN_REVERT**
- Low IV, low ATR, choppy mean-reverting conditions
- **Action**: Iron Condor / Credit Spread
- **Capital**: 25% max
- **Trades**: 1 per day

#### **MEDIUM_TREND**
- Normal IV, healthy ATR, strong directional trend
- **Action**: Directional Credit Spread + Index Sniper
- **Capital**: 30% max
- **Trades**: 2 per day

#### **HIGH_EVENT**
- Elevated IV, VIX rising, event/gap risk
- **Action**: Long Straddle/Strangle or stay flat
- **Capital**: 15% max
- **Trades**: 1 per day

#### **CHAOTIC**
- Very high IV, extreme ATR, liquidity risk
- **Action**: Stay flat
- **Capital**: 0%
- **Trades**: 0

### 3. Strategy Routing

R1 maps each regime to appropriate A-G strategies:

| Regime | Primary Structure | Fallback |
|--------|------------------|----------|
| LOW_MEAN_REVERT | Iron Condor | Short Strangle |
| MEDIUM_TREND | Directional Credit Spread | Index Sniper |
| HIGH_EVENT | Long Straddle | Stay Flat |
| CHAOTIC | Stay Flat | - |

## Configuration

Edit `configs/regime_vol_engine.yaml` to customize:

- **Underlyings**: Which indices to monitor
- **Thresholds**: IV rank, ATR, RV/IV ratio boundaries
- **Regime Conditions**: Feature ranges for each regime
- **Actions**: Structures and capital limits per regime

## Integration

### Enable in Config

Add to your `configs/app.yaml`:

```yaml
strategies:
  - name: "RegimeVolEngine"
    enabled: true
    params: {}
```

The engine will automatically load from `configs/regime_vol_engine.yaml`.

### Strategy Registry

R1 requires access to your A-G strategies. It automatically builds a registry from enabled strategies:

- `IronCondor` → Iron Condor strategy
- `OptionsRanker` → Options Ranker (for spreads/strangles)
- `ORB` → Opening Range Breakout (Index Sniper)

## Metrics

R1 exposes Prometheus metrics:

- `trader_vol_regime{underlying, regime}` - Current regime (1 = active)
- `trader_vol_iv_rank{underlying}` - IV rank (0-1)
- `trader_vol_atr_pct{underlying}` - ATR as % of spot

## Example Dashboard Query

```promql
# Current regime for BANKNIFTY
trader_vol_regime{underlying="BANKNIFTY", regime="LOW_MEAN_REVERT"}

# IV rank over time
trader_vol_iv_rank{underlying="NIFTY"}
```

## Usage Flow

1. **R1 runs first** in the scan cycle (highest priority)
2. **Computes features** from market data
3. **Classifies regime** based on thresholds
4. **Routes to child strategies** based on regime
5. **Child strategies generate signals** as normal
6. **Signals tagged** with regime metadata

## Benefits

- **Adaptive**: Automatically adjusts to market conditions
- **Risk-Aware**: Reduces exposure in chaotic regimes
- **Capital Efficient**: Allocates capital based on regime quality
- **Non-Disruptive**: Works with existing A-G strategies

## Next Steps

1. **Tune Thresholds**: Adjust regime boundaries based on backtesting
2. **Add More Features**: Extend feature computation with VIX data, OI changes
3. **Custom Structures**: Map new structures to regimes
4. **Monitor Performance**: Track PnL per regime in Grafana


