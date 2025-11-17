# Starting the Trader for Dashboard Testing

## Quick Start Options

### Option A: Kite PAPER Mode (Safe for Testing)

```bash
# 1. Start infrastructure
docker compose up -d postgres redis

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies (if needed)
pip install -r requirements.txt

# 4. Copy config
cp configs/kite_canary_live.yaml configs/app.yaml

# 5. Set environment variables
export APP_MODE=PAPER
export APP_TIMEZONE=Asia/Kolkata
export PYTHONPATH=.

# 6. Start API
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Option B: Binance CRYPTO_PAPER Mode

```bash
# 1. Start infrastructure
docker compose up -d postgres redis

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies (if needed)
pip install -r requirements.txt

# 4. Copy config
cp configs/crypto_paper.yaml configs/app.yaml

# 5. Set environment variables
export APP_MODE=CRYPTO_PAPER
export APP_TIMEZONE=UTC
export PYTHONPATH=.

# 6. Set Binance API keys (if needed)
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# 7. Start API
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

## Expected Dashboard Behavior

Once the trader starts:

✅ **Mode badge**: Shows `PAPER` or `CRYPTO_PAPER` with green leader dot  
✅ **Heartbeat tiles**: All < 5s (green)  
✅ **Leader status**: Green "Leader" badge  
✅ **`/ready` endpoint**: Returns 200 (instead of 500/503)  
✅ **Metrics updating**: Real-time updates every 1.5s  

## Quick Health Check

```bash
# Check if trader is running
curl -s http://localhost:8000/ready | jq

# Check leader status
curl -s http://localhost:8000/metrics | grep trader_is_leader

# Check heartbeats
curl -s http://localhost:8000/metrics | grep heartbeat_seconds
```

## Troubleshooting

**High heartbeat values (> 5s):**
- Trader orchestrator may not be fully started
- Wait 10-30 seconds after API starts
- Check API logs for orchestrator initialization

**`/ready` returns 503:**
- Normal if trader isn't started yet
- Should return 200 once orchestrator acquires leader lock

**Leader dot stays red:**
- Check `trader_is_leader` metric: `curl -s http://localhost:8000/metrics | grep trader_is_leader`
- Should be `1` when trader is running
- May take a few seconds after API starts



