# AITRAPP - Docker Deployment Guide

Complete guide for deploying AITRAPP trading system using Docker.

## 📋 Prerequisites

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)
- **Kite API Credentials** from https://kite.trade/
- **Internet Access** to api.kite.trade (required for authentication and trading)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AITRAPP
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp env.example .env
```

Edit `.env` and add your Kite API credentials:

```bash
# Required: Your Kite API credentials
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here

# Optional: Will be set automatically after login
KITE_ACCESS_TOKEN=your_access_token_here
KITE_USER_ID=your_user_id_here

# Trading mode (PAPER for testing, LIVE for real trading)
APP_MODE=PAPER
```

### 3. Start the Services

```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose.trading.yml up -d postgres redis

# Wait for services to be healthy (about 10-15 seconds)
docker-compose -f docker-compose.trading.yml ps
```

### 4. Login to Kite

Use the Kite Trader CLI to authenticate:

```bash
# Run the login script
python kite_trader.py --login-only
```

This will:
1. Show you a Kite login URL
2. You login via browser
3. Copy the `request_token` from the redirect URL
4. Paste it when prompted
5. Access token is saved to `.env` automatically

### 5. Start Trading System

```bash
# Start the trading API
docker-compose -f docker-compose.trading.yml up -d trading-api

# Check logs
docker-compose -f docker-compose.trading.yml logs -f trading-api
```

## 🎯 Alternative: All-in-One Start

Use the helper script:

```bash
# Make script executable
chmod +x docker-start.sh

# Start everything
./docker-start.sh
```

This will:
- ✅ Check if `.env` exists
- ✅ Start all services
- ✅ Show service status
- ✅ Display useful commands

## 📊 Accessing the System

Once running, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| Trading API | http://localhost:8000 | Main trading API |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Health Check | http://localhost:8000/health | System health status |
| Metrics | http://localhost:8000/metrics | Prometheus metrics |
| PostgreSQL | localhost:5432 | Database (user: aitrapp, pass: aitrapp) |
| Redis | localhost:6379 | Cache & message broker |

## 🔧 Common Operations

### Check Service Status

```bash
docker-compose -f docker-compose.trading.yml ps
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.trading.yml logs -f

# Trading API only
docker-compose -f docker-compose.trading.yml logs -f trading-api

# Last 100 lines
docker-compose -f docker-compose.trading.yml logs --tail=100 trading-api
```

### Stop Services

```bash
# Stop all services
docker-compose -f docker-compose.trading.yml down

# Stop and remove volumes (WARNING: deletes data)
docker-compose -f docker-compose.trading.yml down -v
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.trading.yml restart

# Restart trading API only
docker-compose -f docker-compose.trading.yml restart trading-api
```

### Update Code and Rebuild

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.trading.yml up -d --build trading-api
```

## 🐛 Troubleshooting

### Issue: "Cannot connect to database"

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.trading.yml ps postgres

# Check PostgreSQL logs
docker-compose -f docker-compose.trading.yml logs postgres

# Restart PostgreSQL
docker-compose -f docker-compose.trading.yml restart postgres
```

### Issue: "Redis connection failed"

**Solution:**
```bash
# Check if Redis is running
docker-compose -f docker-compose.trading.yml ps redis

# Test Redis connection
docker exec -it aitrapp-redis redis-cli ping
# Should respond: PONG

# Restart Redis
docker-compose -f docker-compose.trading.yml restart redis
```

### Issue: "Access token expired"

**Solution:**
```bash
# Re-login using kite_trader.py
python kite_trader.py --login-only

# Restart trading API to pick up new token
docker-compose -f docker-compose.trading.yml restart trading-api
```

### Issue: "Network proxy errors when authenticating"

**Cause:** The environment blocks external HTTPS connections.

**Solution:** Run on a machine with direct internet access to `api.kite.trade`.

### Issue: "Port already in use"

**Solution:**
```bash
# Check what's using the port
lsof -i :8000  # or :5432 for postgres, :6379 for redis

# Change port in .env
echo "API_PORT=8001" >> .env

# Restart
docker-compose -f docker-compose.trading.yml up -d
```

## 🔒 Security Best Practices

### 1. Protect Your Credentials

```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Set proper permissions
chmod 600 .env

# Never commit API keys to git
git status  # .env should not appear
```

### 2. Use Secrets for Production

For production deployments, use Docker secrets:

```bash
# Create secrets
echo "your_api_key" | docker secret create kite_api_key -
echo "your_api_secret" | docker secret create kite_api_secret -

# Reference in docker-compose.yml
# See: https://docs.docker.com/engine/swarm/secrets/
```

### 3. Network Security

```bash
# By default, services are on an isolated network
# Only expose necessary ports
# API: 8000 (change if needed)
# Database & Redis: Keep internal (remove ports: section)
```

### 4. Regular Updates

```bash
# Update base images regularly
docker-compose -f docker-compose.trading.yml pull
docker-compose -f docker-compose.trading.yml up -d --build
```

## 📦 Data Persistence

Data is persisted in Docker volumes:

### Volumes

| Volume | Contents | Backup Command |
|--------|----------|----------------|
| `postgres_data` | Trading database | `docker exec aitrapp-postgres pg_dump -U aitrapp aitrapp > backup.sql` |
| `redis_data` | Cache & queues | `docker exec aitrapp-redis redis-cli BGSAVE` |
| `./reports` | Backtest reports | Already on host filesystem |
| `./logs` | Application logs | Already on host filesystem |
| `./data` | Market data | Already on host filesystem |

### Backup Database

```bash
# Create backup
docker exec aitrapp-postgres pg_dump -U aitrapp aitrapp > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_20260116.sql | docker exec -i aitrapp-postgres psql -U aitrapp aitrapp
```

### Backup Redis

```bash
# Trigger save
docker exec aitrapp-redis redis-cli SAVE

# Copy RDB file
docker cp aitrapp-redis:/data/dump.rdb redis_backup_$(date +%Y%m%d).rdb
```

## 🔍 Monitoring

### Health Checks

```bash
# Check all services health
docker-compose -f docker-compose.trading.yml ps

# Manual health check
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Resource Usage

```bash
# Real-time stats
docker stats

# Specific container
docker stats aitrapp-trading-api
```

### Prometheus Metrics

```bash
# View metrics
curl http://localhost:8000/metrics

# Or use Prometheus/Grafana stack (see below)
```

## 📈 Production Deployment

### 1. Environment-Specific Configs

```bash
# Development
docker-compose -f docker-compose.trading.yml up -d

# Production (use docker-compose.prod.yml)
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Add Monitoring Stack

Create `docker-compose.monitoring.yml`:

```yaml
version: "3.9"
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - trading-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - trading-network
```

### 3. Use Kubernetes (Advanced)

For large-scale deployments, convert to Kubernetes:

```bash
# Convert compose to k8s (using kompose)
kompose convert -f docker-compose.trading.yml
```

## 🧪 Testing in Docker

### Run Tests

```bash
# Run unit tests
docker-compose -f docker-compose.trading.yml exec trading-api pytest tests/unit

# Run integration tests
docker-compose -f docker-compose.trading.yml exec trading-api pytest tests/integration

# Run end-to-end tests
docker-compose -f docker-compose.trading.yml exec trading-api python scripts/paper_e2e.py
```

### Paper Trading Test

```bash
# Start in PAPER mode (default)
docker-compose -f docker-compose.trading.yml up -d

# Check it's in PAPER mode
curl http://localhost:8000/health
# Should show: "mode": "PAPER"

# Run paper trading test
docker-compose -f docker-compose.trading.yml exec trading-api python scripts/paper_e2e.py
```

## 🌐 Deployment Options

### Option 1: Local Machine (Development)

```bash
docker-compose -f docker-compose.trading.yml up -d
```

### Option 2: VPS/Cloud Server (Production)

```bash
# SSH to server
ssh user@your-server.com

# Clone and setup
git clone <repo>
cd AITRAPP
cp env.example .env
# Edit .env with credentials

# Start services
docker-compose -f docker-compose.trading.yml up -d

# Setup reverse proxy (nginx/caddy) for HTTPS
```

### Option 3: Docker Swarm (Multi-Node)

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.trading.yml aitrapp
```

### Option 4: Kubernetes (Enterprise)

```bash
# Convert and apply
kompose convert -f docker-compose.trading.yml
kubectl apply -f .
```

## 📚 Additional Resources

- **Main Guide**: `KITE_TRADER_GUIDE.md` - Using the kite_trader CLI
- **Authentication**: `docs/auth.md` - Detailed auth documentation
- **API Docs**: http://localhost:8000/docs (when running)
- **Docker Docs**: https://docs.docker.com/
- **Kite Connect**: https://kite.trade/docs/connect/v3/

## ❓ FAQ

**Q: Do I need to re-login every day?**
A: Yes, Kite access tokens expire daily. Run `python kite_trader.py --login-only` each morning.

**Q: Can I run this on Windows/Mac?**
A: Yes! Docker Desktop works on all platforms. The setup is identical.

**Q: How do I switch from PAPER to LIVE mode?**
A: Edit `.env` (change `APP_MODE=LIVE`), then restart: `docker-compose -f docker-compose.trading.yml restart trading-api`. **Warning:** LIVE mode uses real money!

**Q: Can I run multiple strategies?**
A: Yes, configure strategies in `configs/app.yaml` and restart the trading API.

**Q: How do I update to the latest code?**
A: `git pull && docker-compose -f docker-compose.trading.yml up -d --build`

**Q: Where are my trading logs?**
A: `./logs/` directory (mounted from container) and `docker-compose logs -f trading-api`

## 🆘 Getting Help

If you encounter issues:

1. Check the logs: `docker-compose -f docker-compose.trading.yml logs -f`
2. Check service health: `docker-compose -f docker-compose.trading.yml ps`
3. Verify `.env` configuration
4. Review this troubleshooting guide
5. Open an issue on GitHub

---

**Happy Trading!** 🚀📈

*Remember: Always test thoroughly in PAPER mode before going LIVE.*
