# AITRAPP System Overview

## NSE Trading Platform

AITRAPP is a **trading platform focused on Indian markets (NSE)**.

---

## 🏛️ Indian Markets (NSE)

### Supported Venues
- **NSE** (National Stock Exchange) - Equities, Futures, Options
- **BSE** (Bombay Stock Exchange)

### Trading Modes
- `PAPER` - Paper trading (simulation)
- `LIVE` - Live trading with real money

### Asset Types
- **EQUITY** - Stocks (NIFTY, BANKNIFTY, FINNIFTY components)
- **DERIVATIVES** - Futures contracts
- **OPTIONS** - Call and Put options

### API Integration
- **KiteConnect** (Zerodha's API)
- Market data streaming
- Order placement and management
- Position tracking

### Market Hours
- **Trading Hours**: 9:15 AM - 3:20 PM IST (entries)
- **Hard Close**: 3:25 PM IST (all positions must be flat)
- **Holidays**: NSE trading calendar

### Strategies
- **ORB** (Opening Range Breakout)
- **TrendPullback**
- **SMAMomentum** (vectorbt-inspired)
- **MeanReversion** (bt-inspired)
- **RSIMeanReversion** (vectorbt-inspired)
- **OptionsRanker** (options strategies)

### Configuration
- `configs/app.yaml` - Default NSE paper trading config
- `configs/kite_paper.yaml` - NSE paper trading config
- `configs/kite_day1_live.yaml` - NSE live trading config
- `configs/kite_canary_live.yaml` - NSE canary live trading config

---

## 🔀 How It Works

### Mode-Based Configuration

The system uses `APP_MODE` environment variable:

```python
# Indian Markets
APP_MODE=PAPER   → Uses KiteConnect, NSE/BSE (paper trading)
APP_MODE=LIVE    → Uses KiteConnect, NSE/BSE (live trading)
```

### Orchestrator Logic

```python
# In orchestrator.start()
# Initialize equity market data stream
self.market_data_stream.start()
# Subscribe to NSE/BSE instruments
```

---

## 📊 Key Features

| Feature | Indian Markets |
|---------|---------------|
| **Venues** | NSE, BSE |
| **API** | KiteConnect |
| **Hours** | 9:15 AM - 3:25 PM IST |
| **Assets** | Equity, Futures, Options |
| **OCO** | Native (Kite) |
| **Timezone** | Asia/Kolkata |
| **Risk** | Margin-based |

---

## 🚀 Usage Examples

### NSE Paper Trading (Default)
```bash
# Default config is already set to PAPER mode
export APP_MODE=PAPER
make paper
```

### NSE Live Trading
```bash
cp configs/kite_day1_live.yaml configs/app.yaml
export APP_MODE=LIVE
make live
```

### NSE Canary Live Trading
```bash
cp configs/kite_canary_live.yaml configs/app.yaml
export APP_MODE=LIVE
make kite-canary-launch
```

---

## 🎯 Summary

**AITRAPP is a trading platform focused on:**
- **Indian Markets (NSE/BSE)** only
- **Paper Trading** by default (safe for research)
- **Live Trading** with proper safety gates
- **Multiple Strategies** for different market conditions
- **Risk Management** with position limits and daily stops

---

## 📝 Configuration Files

### Paper Trading
- `configs/app.yaml` - Default NSE paper trading (loaded by default)
- `configs/kite_paper.yaml` - NSE paper trading with all strategies

### Live Trading
- `configs/kite_day1_live.yaml` - Full NSE live trading config
- `configs/kite_canary_live.yaml` - Conservative canary live config

### Strategy-Specific
- `configs/regime_vol_engine.yaml` - Regime classification
- `configs/options/` - Options strategy configs
- `configs/strategies/` - Individual strategy configs

---

## 🔒 Safety Features

1. **Paper Trading Default**: System defaults to PAPER mode
2. **Live Mode Gates**: Multiple safety checks before allowing LIVE mode
3. **Risk Limits**: Position limits, portfolio heat, daily loss stops
4. **EOD Square-Off**: Automatic position flattening at 15:25 IST
5. **Market Hours Validation**: Strategies only trade during market hours

---

## 📚 Documentation

- `strategy_sources/` - Strategy design references
- `docs/` - System documentation
- `README.md` - Getting started guide
