# Docker Quick Start

Get AITRAPP up and running in minutes with Docker!

## Prerequisites

- Docker & Docker Compose installed
- Kite API credentials from https://kite.trade/

## 3-Step Setup

### 1. Configure

```bash
# Copy environment template
cp env.example .env

# Edit .env and add your credentials
nano .env  # or vim, or your favorite editor
```

Add your Kite API credentials:
```bash
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
```

### 2. Start Services

```bash
# Make start script executable (first time only)
chmod +x docker-start.sh

# Start everything!
./docker-start.sh
```

### 3. Login to Kite

```bash
# Login to get access token
python kite_trader.py --login-only
```

That's it! 🎉

## What Gets Started

- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ Trading API server
- ✅ All necessary services

## Access Points

Once running:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Common Commands

```bash
# View logs
docker-compose -f docker-compose.trading.yml logs -f trading-api

# Check status
docker-compose -f docker-compose.trading.yml ps

# Stop services
docker-compose -f docker-compose.trading.yml down

# Restart
docker-compose -f docker-compose.trading.yml restart trading-api
```

## Full Guide

For complete documentation, see:
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Complete Docker guide
- **[KITE_TRADER_GUIDE.md](KITE_TRADER_GUIDE.md)** - Kite login & trading guide

## Troubleshooting

**Services won't start?**
```bash
# Check Docker is running
docker ps

# Check logs
docker-compose -f docker-compose.trading.yml logs
```

**Need to re-login?**
```bash
python kite_trader.py --login-only
docker-compose -f docker-compose.trading.yml restart trading-api
```

**Want to test first?**

The system starts in PAPER mode by default (simulated trading, no real money). Perfect for testing!

---

**Ready for LIVE?** See the [full deployment guide](DOCKER_DEPLOYMENT.md) for production setup.
