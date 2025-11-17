# AITRAPP System Overview

## Multi-Venue Trading Platform

AITRAPP is a **unified trading platform** that supports **both Indian markets AND crypto markets**.

---

## 🏛️ Indian Markets (Original/Base System)

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
- **OptionsRanker**

### Configuration
- `configs/app.yaml` - Main config for Indian markets
- `configs/canary_live.yaml` - Canary live trading config

---

## 🪙 Crypto Markets (Recently Added)

### Supported Venues
- **BINANCE_SPOT** (Primary - just switched from Kraken)
- **KRAKEN_SPOT** (Still supported)

### Trading Modes
- `CRYPTO_PAPER` - Paper trading (simulation)
- `CRYPTO_LIVE` - Live trading
- `CRYPTO_CANARY_LIVE` - Canary live (limited symbols/risk)

### Asset Types
- **CRYPTO** - Spot trading only (no leverage)

### API Integration
- **Binance Spot API** (REST + WebSocket)
- **Kraken Spot API** (REST + WebSocket)
- Native OCO support (Binance)
- Client-side OCO emulation (Kraken)

### Market Hours
- **24/7** - No market hours restrictions
- Continuous trading

### Strategies
- Reuses same strategies (ORB, etc.)
- Adapted for crypto symbol format

### Configuration
- `configs/crypto_paper.yaml` - Crypto paper trading
- `configs/crypto_live.yaml` - Crypto live trading
- `configs/crypto_canary_live.yaml` - Crypto canary (BTCUSDT only)

---

## 🔀 How It Works

### Mode-Based Routing

The system routes to the appropriate venue based on `APP_MODE`:

```python
# Indian Markets
APP_MODE=PAPER   → Uses KiteConnect, NSE/BSE
APP_MODE=LIVE    → Uses KiteConnect, NSE/BSE

# Crypto Markets
APP_MODE=CRYPTO_PAPER  → Uses Binance/Kraken (paper mode)
APP_MODE=CRYPTO_LIVE   → Uses Binance/Kraken (live mode)
```

### Orchestrator Logic

```python
# In orchestrator.start()
if settings.app_mode.value in ("CRYPTO_PAPER", "CRYPTO_LIVE"):
    # Initialize crypto router
    await self.crypto_router.connect_ws()
    # Subscribe to crypto symbols
else:
    # Initialize equity market data stream
    self.market_data_stream.start()
    # Subscribe to NSE/BSE instruments
```

---

## 📊 Key Differences

| Feature | Indian Markets | Crypto Markets |
|---------|---------------|----------------|
| **Venues** | NSE, BSE | Binance, Kraken |
| **API** | KiteConnect | Binance/Kraken REST+WS |
| **Hours** | 9:15 AM - 3:25 PM IST | 24/7 |
| **Assets** | Equity, Futures, Options | Spot Crypto |
| **OCO** | Native (Kite) | Native (Binance), Emulated (Kraken) |
| **Timezone** | Asia/Kolkata | UTC |
| **Risk** | Margin-based | Balance-based (spot) |

---

## 🚀 Usage Examples

### Indian Markets (PAPER)
```bash
cp configs/app.yaml configs/app.yaml  # Already configured
export APP_MODE=PAPER
make paper
```

### Indian Markets (LIVE)
```bash
cp configs/canary_live.yaml configs/app.yaml
export APP_MODE=LIVE
make live
```

### Crypto Markets (PAPER)
```bash
cp configs/crypto_paper.yaml configs/app.yaml
export APP_MODE=CRYPTO_PAPER
export BINANCE_API_KEY="..."
export BINANCE_API_SECRET="..."
make crypto-paper
```

### Crypto Markets (LIVE)
```bash
cp configs/crypto_canary_live.yaml configs/app.yaml
export APP_MODE=CRYPTO_LIVE
export BINANCE_API_KEY="..."
export BINANCE_API_SECRET="..."
make crypto-canary-launch
```

---

## 🎯 Summary

**AITRAPP is a unified platform that handles:**
- ✅ **Indian Markets** (NSE/BSE) - Equities, Futures, Options
- ✅ **Crypto Markets** (Binance/Kraken) - Spot trading

**You can run either:**
- Indian markets only (PAPER/LIVE)
- Crypto markets only (CRYPTO_PAPER/CRYPTO_LIVE)
- **But NOT both simultaneously** (single APP_MODE at a time)

The recent work has been focused on **adding crypto support** to the existing Indian markets platform, making it a true multi-venue system.


