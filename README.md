# AITRAPP - Autonomous Intelligent Trading Application

**Educational autonomous trading system for Indian markets using Zerodha Kite Connect**

⚠️ **EDUCATIONAL SOFTWARE ONLY** - This system is designed for learning algorithmic trading concepts. 
Always comply with SEBI regulations and broker Terms of Service.

## Features

- 🔴 **Paper Mode by Default** - Safe simulation environment
- 🛡️ **Comprehensive Risk Management** - Multi-layered protection
- 🎯 **Multiple Strategies** - ORB, VWAP Reversion, Trend Pullback, Options strategies
- 📊 **Real-time Dashboard** - Live monitoring and control
- 🔌 **WebSocket Market Data** - Low-latency tick streaming
- 📝 **Audit-Grade Logging** - Full decision trail
- 🚨 **Kill Switch** - Instant position flatten and pause
- 📈 **Backtesting Engine** - Test strategies on historical NSE options data

## Architecture

```
apps/
  api/          - FastAPI execution engine
  web/          - Next.js dashboard
packages/
  core/         - Signals, ranking, risk management
  storage/      - Database models and migrations
  infra/        - Docker and deployment configs
configs/
  strategies/   - Strategy YAML configurations
  app.yaml      - Global application config
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd AITRAPP

# Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your Kite API credentials

# Start infrastructure
make dev

# Run in Paper Mode (default)
make paper
```

### Environment Variables

Required variables in `.env`:

```
# Kite Connect
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token
KITE_USER_ID=your_user_id

# Infrastructure
DATABASE_URL=postgresql://user:pass@localhost:5432/aitrapp
REDIS_URL=redis://localhost:6379/0

# Application
APP_MODE=PAPER
APP_TIMEZONE=Asia/Kolkata

# Optional: Alerts
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Safety Features

### Default Risk Limits

- **Per-trade risk**: 0.50% of net liquid capital
- **Portfolio heat**: Max 2.0% aggregate risk
- **Daily loss stop**: -2.5% hard stop
- **EOD square-off**: 15:25 IST automatic flatten

### Kill Switch

Press the kill switch in the dashboard or call:

```bash
curl -X POST http://localhost:8000/pause
```

This will:
1. Cancel all pending orders
2. Close all positions (market orders)
3. Block new signal generation
4. Require manual resume

## Usage

### Paper Mode (Recommended)

```bash
make paper
```

Dashboard: http://localhost:3000

### Live Mode (⚠️ USE WITH EXTREME CAUTION)

```bash
# Requires explicit confirmation
make live
```

You will be prompted to type "CONFIRM LIVE TRADING" before the system activates.

## Strategy Configuration

Edit `configs/strategies/*.yaml` to tune parameters:

```yaml
# configs/strategies/orb.yaml
name: ORB
enabled: true
params:
  window_min: 15
  rr_min: 1.8
  max_positions: 2
  instruments: [NIFTY, BANKNIFTY]
```

## Backtesting

Test strategies on historical NSE options data before live trading:

### CLI Script

```bash
# Run backtest on NIFTY
python scripts/run_backtest.py \
    --symbol NIFTY \
    --start-date 2025-08-15 \
    --end-date 2025-11-10 \
    --capital 1000000 \
    --strategy all
```

### API Endpoint

```bash
curl -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY",
    "start_date": "2025-08-15",
    "end_date": "2025-11-10",
    "initial_capital": 1000000,
    "strategy": "all"
  }' | jq
```

**Historical Data**: Includes NIFTY and BANKNIFTY options data (Aug-Nov 2025) in `docs/NSE OPINONS DATA/`

See [docs/BACKTESTING.md](docs/BACKTESTING.md) for detailed guide.

## Monitoring

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Logs**: `logs/aitrapp.log`

## Testing

```bash
# Unit tests
make test

# Integration tests
make test-integration

# Replay historical data
make test-replay
```

## Documentation

- [Security & Compliance](docs/SECURITY.md)
- [Operational Runbook](docs/RUNBOOK.md)
- [Strategy Development](docs/STRATEGIES.md)
- [API Reference](docs/API.md)

## Compliance & Legal

This software is provided for **educational purposes only**. Users must:

1. Comply with all SEBI regulations
2. Respect broker API rate limits and Terms of Service
3. Understand that algorithmic trading carries significant risk
4. Never risk capital they cannot afford to lose
5. Maintain proper audit trails for tax and regulatory purposes

**The authors assume NO LIABILITY for financial losses.**

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - See [LICENSE](LICENSE)

## Support

- GitHub Issues: Bug reports and feature requests
- Discussions: Strategy ideas and general questions

---

**⚠️ RISK WARNING**: Trading in derivatives and equities involves substantial risk of loss. 
Past performance does not guarantee future results. Use at your own risk.
