# MCP Historical Data Integration Guide

**Automate Paper Trades, Backtests & Live Trading with Real Market Data**

---

## 🎯 Overview

This guide shows how to use **Kite MCP** to fetch real historical data and power:

1. **Backtesting** - Test strategies on real historical data
2. **Paper Trading Replay** - Simulate trading with today's market data
3. **Live Trading Context** - Enrich live trades with historical analysis

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AITRAPP Trading System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────────────────────┐    │
│  │  Strategies  │──────▶│  HistoricalDataMCPProvider  │    │
│  │              │      │                              │    │
│  │ - RSI Mean   │      │  - Fetch real OHLC data     │    │
│  │ - MACD       │      │  - Multiple timeframes      │    │
│  │ - Bollinger  │      │  - Options OI data          │    │
│  └──────────────┘      └──────────────┬───────────────┘    │
│                                        │                     │
│                                        ▼                     │
│                        ┌────────────────────────────┐       │
│                        │   KiteMCPAdapter           │       │
│                        └────────────────┬───────────┘       │
│                                         │                    │
└─────────────────────────────────────────┼────────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────┐
                        │   Kite MCP Server               │
                        │   (http://localhost:8080)       │
                        ├─────────────────────────────────┤
                        │ Tools:                          │
                        │ - get_historical_data           │
                        │ - search_instruments            │
                        │ - get_quotes                    │
                        │ - get_ohlc                      │
                        └─────────────────┬───────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────┐
                        │   Kite Connect API              │
                        │   (Real Market Data)            │
                        └─────────────────────────────────┘
```

---

## 📦 New Components

### 1. **HistoricalDataMCPProvider**
**File:** [`packages/core/historical_data_mcp.py`](packages/core/historical_data_mcp.py)

**Purpose:** Fetch real historical data from Kite Connect via MCP

**Features:**
- ✅ Real OHLC data (not synthetic)
- ✅ Multiple timeframes: 1min, 3min, 5min, 15min, 30min, 60min, day
- ✅ Option Open Interest (OI) data
- ✅ Continuous futures data
- ✅ Date range queries (up to 60 days for minute data)
- ✅ Instrument search integration

**Usage:**
```python
from packages.core.historical_data_mcp import HistoricalDataMCPProvider
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter

# Initialize
adapter = KiteMCPAdapter(mcp_client=mcp_client)
provider = HistoricalDataMCPProvider(kite_mcp_adapter=adapter)

# Fetch historical data
candles = provider.fetch_candles(
    instrument_token=256265,  # NIFTY 50
    from_date="2025-11-20 09:15:00",
    to_date="2025-11-26 15:30:00",
    interval="5minute"
)
```

### 2. **MCPBacktestRunner**
**File:** [`scripts/run_mcp_backtest.py`](scripts/run_mcp_backtest.py)

**Purpose:** Run backtests using real market data from MCP

**Features:**
- ✅ Strategy backtesting on real data
- ✅ Multiple strategy comparison
- ✅ Replay mode for paper trading simulation
- ✅ Performance metrics calculation
- ✅ JSON export for results

---

## 🚀 Quick Start

### Prerequisites

1. **Kite MCP Server Running:**
   ```bash
   cd kite-mcp-server
   ./kite-mcp-server
   # Should be accessible at http://localhost:8080
   ```

2. **Dependencies Installed:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Kite Access Token Set:**
   ```bash
   export KITE_API_KEY="your_api_key"
   export KITE_API_SECRET="your_api_secret"
   export KITE_ACCESS_TOKEN="your_access_token"
   ```

---

## 📊 Use Case 1: Backtest Strategies on Real Data

### Goal: Test if RSI Mean Reversion strategy would have worked last week

```bash
# Backtest RSI strategy for last 7 days
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 7 \
  --interval 5minute
```

**What happens:**
1. Fetches real 5-minute OHLC data from Kite for last 7 days
2. Replays data through RSIMeanReversion strategy
3. Generates signals based on RSI indicators
4. Simulates order execution
5. Calculates P&L and performance metrics

**Output:**
```json
{
  "total_signals": 24,
  "total_trades": 18,
  "signals_by_strategy": {
    "RSIMeanReversion": 24
  },
  "final_capital": 1023500,
  "win_rate": 0.67,
  "sharpe_ratio": 1.42
}
```

### Multiple Strategies Comparison

```bash
# Compare 3 strategies
python scripts/run_mcp_backtest.py \
  --strategy "RSIMeanReversion,MACD,BollingerBands" \
  --days 14 \
  --interval 5minute \
  --output results/backtest_comparison.json
```

---

## 🎬 Use Case 2: Paper Trading Replay Mode

### Goal: Simulate what would have happened if you traded today

```bash
# Replay today's market
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD" \
  --interval 1minute
```

**What happens:**
1. Fetches today's 1-minute data from 09:15 to current time
2. Replays tick-by-tick through strategies
3. Shows exactly when signals would have triggered
4. Calculates P&L as if you traded live

**Perfect for:**
- ✅ Testing strategies on today's market **after market close**
- ✅ Debugging why a strategy didn't trigger during live trading
- ✅ Paper trading simulation with real data
- ✅ Strategy validation before going live

---

## 🔄 Use Case 3: Automated Daily Backtesting

### Goal: Run nightly backtests on today's data to validate strategies

**Create a cron job:**
```bash
# Add to crontab (runs at 4 PM daily after market close)
0 16 * * 1-5 cd /Users/mac/CRYPTO/AITRAPP && \
  python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD,BollingerBands" \
  --interval 1minute \
  --output results/daily_backtest_$(date +\%Y\%m\%d).json
```

**Benefits:**
- ✅ Automatic strategy validation every day
- ✅ Catch strategy degradation early
- ✅ Build historical performance database
- ✅ Data-driven strategy selection

---

## 🎯 Use Case 4: Historical Context for Live Trading

### Goal: Enrich live trades with historical analysis

```python
from packages.core.historical_data_mcp import HistoricalDataMCPProvider

# During live trading
def should_enter_trade(instrument, current_price):
    """
    Use historical data to validate entry conditions.
    """
    # Fetch last 7 days of data
    historical = provider.fetch_date_range(
        instrument_token=instrument.token,
        days=7,
        interval="5minute"
    )

    # Calculate historical volatility
    closes = [c[4] for c in historical]  # Close prices
    volatility = calculate_volatility(closes)

    # Calculate support/resistance levels
    support = min(closes[-20:])  # 20-period support
    resistance = max(closes[-20:])  # 20-period resistance

    # Enhanced entry logic
    if current_price < support * 1.02 and volatility < threshold:
        return True  # Good entry - near support, low volatility

    return False
```

**Benefits:**
- ✅ Context-aware trade decisions
- ✅ Better risk assessment
- ✅ Support/resistance identification
- ✅ Volatility-adjusted sizing

---

## 📈 Use Case 5: Strategy Development Workflow

### Complete workflow from idea to live trading:

#### Step 1: Backtest on Historical Data (Weeks)
```bash
# Test strategy on last 30 days
python scripts/run_mcp_backtest.py \
  --strategy MyNewStrategy \
  --days 30 \
  --interval 5minute
```

#### Step 2: Replay Recent Days (Days)
```bash
# Validate on last 3 days at higher resolution
python scripts/run_mcp_backtest.py \
  --strategy MyNewStrategy \
  --days 3 \
  --interval 1minute
```

#### Step 3: Replay Today (Hours)
```bash
# Test on today's market (after close)
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy MyNewStrategy \
  --interval 1minute
```

#### Step 4: Paper Trade Tomorrow (Live)
```bash
# Enable in kite_paper.yaml and run live
export APP_MODE=PAPER
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

#### Step 5: Go Live (After validation)
```bash
# Only after 2-3 weeks of successful paper trading
export APP_MODE=LIVE
# ... careful live trading setup
```

---

## 🛠️ Advanced Usage

### Custom Date Range

```bash
# Backtest specific date range
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --from-date "2025-11-01" \
  --to-date "2025-11-26" \
  --interval 5minute
```

### Specific Underlying

```bash
# Backtest BANKNIFTY instead of NIFTY
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --underlying BANKNIFTY \
  --days 7
```

### Higher Resolution

```bash
# 1-minute data for tick-accurate replay
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 3 \
  --interval 1minute
```

### Different Capital

```bash
# Test with 5 lakh capital
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --capital 500000 \
  --days 7
```

---

## 📊 Data Availability & Limits

### Kite Connect Historical Data Limits:

| Interval    | Maximum History | Use Case                    |
|-------------|-----------------|------------------------------|
| 1 minute    | 60 days         | High-fidelity backtests     |
| 3 minute    | 100 days        | Intraday strategy testing   |
| 5 minute    | 100 days        | Standard backtesting        |
| 15 minute   | 200 days        | Swing strategy testing      |
| 30 minute   | 200 days        | Position strategy testing   |
| 60 minute   | 400 days        | Long-term analysis          |
| day         | 2000 days       | Multi-year backtests        |

### Recommendations:

- **Development:** Use 5-minute data for 7-30 days
- **Validation:** Use 1-minute data for 1-3 days (high fidelity)
- **Paper Trading Replay:** Use 1-minute data for today only
- **Live Context:** Use 5-15 minute data for last 7 days

---

## 🎯 Integration with Existing System

### Add to Orchestrator for Live Context

```python
# In packages/core/orchestrator.py

from packages.core.historical_data_mcp import HistoricalDataMCPProvider

class Orchestrator:
    def __init__(self, ...):
        # ... existing init
        self.historical_provider = HistoricalDataMCPProvider(
            kite_mcp_adapter=self.mcp_adapter
        )

    async def scan_cycle(self):
        # Before generating signals, fetch historical context
        for instrument in self.universe:
            # Get last 7 days of data
            historical = self.historical_provider.fetch_date_range(
                instrument_token=instrument.token,
                days=7,
                interval="5minute"
            )

            # Add to strategy context
            context.historical_data = historical

            # Now strategies have historical context for better decisions
            signal = strategy.scan(tick, context)
```

---

## 🚨 Important Notes

### 1. **MCP Server Must Be Running**
Always ensure `kite-mcp-server` is running before backtests:
```bash
# Check if running
curl http://localhost:8080/health

# Start if not running
cd kite-mcp-server && ./kite-mcp-server
```

### 2. **Rate Limits**
Kite API has rate limits:
- **Historical data:** 3 requests/second
- **Quotes:** 10 requests/second

The provider handles this automatically, but be patient with large backtests.

### 3. **Data Availability**
- Market holidays: No data available
- Weekends: No data available
- Pre-market/Post-market: Limited data

### 4. **Continuous Futures**
For futures backtesting, use `continuous=True`:
```python
candles = provider.fetch_candles(
    instrument_token=token,
    from_date="2025-11-01 09:15:00",
    to_date="2025-11-26 15:30:00",
    interval="5minute",
    continuous=True  # Get continuous futures data
)
```

---

## 🎉 Benefits Summary

### vs Synthetic Data:
- ✅ **Real market conditions** - actual volatility, gaps, illiquidity
- ✅ **Real slippage** - see actual bid-ask spreads
- ✅ **Real events** - captures news events, expiry days, etc.
- ✅ **Accurate backtests** - no overfitting on synthetic patterns

### vs Manual Backtesting:
- ✅ **Automated** - set and forget
- ✅ **Reproducible** - same data, same results
- ✅ **Fast** - test months of data in minutes
- ✅ **Comprehensive** - test multiple strategies simultaneously

### For Paper Trading:
- ✅ **Replay today's market** - understand what happened
- ✅ **Debug strategies** - see why signals didn't trigger
- ✅ **Risk-free validation** - test before live trading
- ✅ **Build confidence** - see strategies work on real data

### For Live Trading:
- ✅ **Historical context** - better entry/exit decisions
- ✅ **Support/resistance** - data-driven levels
- ✅ **Volatility analysis** - dynamic position sizing
- ✅ **Market regime detection** - adapt to conditions

---

## 🔮 Future Enhancements

Potential additions to the system:

1. **Walk-forward optimization** - rolling backtests with parameter optimization
2. **Monte Carlo simulation** - stress testing with randomized scenarios
3. **Multi-timeframe analysis** - combine 1min, 5min, 15min data
4. **Options Greeks calculation** - from historical IV data
5. **Event detection** - identify earnings, policy announcements
6. **Market microstructure** - order flow analysis from historical depth
7. **Regime classification** - ML-based market state detection
8. **Risk attribution** - which signals contributed to P&L

---

## 📚 Related Documentation

- [Kite MCP Server README](kite-mcp-server/README.md)
- [HiveMind MCP Integration](HIVEMIND_MCP_INTEGRATION.md)
- [Paper Trading Status](PAPER_TRADING_LIVE_STATUS.md)
- [Backtest Implementation](BACKTEST_MODE_IMPLEMENTATION.md)

---

## ✅ Quick Checklist

Before running your first backtest:

- [ ] Kite MCP server running (`http://localhost:8080`)
- [ ] Kite API credentials set in environment
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Understand data limits (60 days for 1-minute data)
- [ ] Choose appropriate interval for your use case
- [ ] Start with small date range (7 days) to test

---

## 🎯 Example: Complete Workflow

```bash
# 1. Start MCP server (if not running)
cd kite-mcp-server && ./kite-mcp-server &

# 2. Run quick backtest (last 7 days, 5-minute data)
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 7 \
  --interval 5minute

# 3. If results look good, test at higher resolution (1-minute)
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 3 \
  --interval 1minute

# 4. Replay today's market (after market close)
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy RSIMeanReversion \
  --interval 1minute \
  --output results/today_replay.json

# 5. If all tests pass, enable for paper trading
# Edit configs/kite_paper.yaml - add RSIMeanReversion to strategies
# Restart paper trading system

# 6. Monitor for 3-5 days in paper mode

# 7. If paper trading successful, carefully consider live trading
```

---

**Ready to backtest with real data? Start with the Quick Start guide above!** 🚀
