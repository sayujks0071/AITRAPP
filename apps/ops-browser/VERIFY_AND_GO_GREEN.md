# Verify & Go Green Checklist

## 1) Restart API in PAPER Mode

### Option A: Kite PAPER

```bash
# Start infrastructure
docker compose up -d postgres redis

# Activate environment
source .venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Copy config
cp configs/kite_canary_live.yaml configs/app.yaml

# Set environment
export APP_MODE=PAPER
export APP_TIMEZONE=Asia/Kolkata
export PYTHONPATH=.

# Start API
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Option B: Binance CRYPTO_PAPER

```bash
# Start infrastructure
docker compose up -d postgres redis

# Activate environment
source .venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Copy config
cp configs/crypto_paper.yaml configs/app.yaml

# Set environment
export APP_MODE=CRYPTO_PAPER
export APP_TIMEZONE=UTC
export PYTHONPATH=.

# Set Binance API keys (if needed)
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# Start API
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

## 2) Quick CORS Sanity Check

Run the verification script:

```bash
apps/ops-browser/scripts/verify_cors.sh
```

Or manually:

```bash
# Success path should be 200 and include ACAO
curl -s -i -H 'Origin: http://localhost:3000' http://localhost:8000/health | \
  grep -E 'HTTP/|Access-Control-Allow-Origin|Content-Type'

# 404 path should ALSO include ACAO (middleware covers it)
curl -s -i -H 'Origin: http://localhost:3000' http://localhost:8000/does-not-exist | \
  grep -E 'HTTP/|Access-Control-Allow-Origin|Content-Type'
```

**Expected:** `Access-Control-Allow-Origin: http://localhost:3000` in both responses.

## 3) Open Dashboard

1. Open `http://localhost:3000`
2. Refresh once (Cmd/Ctrl+Shift+R)
3. Wait 10-30 seconds for orchestrator to start

**Expected Green State:**
- ✅ Leader dot turns green (`leader = 1`)
- ✅ All heartbeat tiles < 5s (green)
- ✅ `/ready` returns 200 (instead of 503)
- ✅ Mode badge shows `PAPER` or `CRYPTO_PAPER`
- ✅ No CORS errors in console

## 4) Production Hardening

### Set Exact Origins (Not Wildcard)

In `apps/api/main.py`, update CORS origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ops-ui.yourdomain.com"],  # Exact origin, not wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Ensure CORS Middleware Order

CORS middleware must be added **before** any routes/mounts:

```python
# ✅ Correct order
app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)  # First
app.mount("/metrics", ...)  # Then mounts
app.include_router(...)  # Then routes
```

### `/ready` Response Format

The `/ready` endpoint now returns a UI-friendly format:

**When ready:**
```json
{
  "ok": true,
  "ready": true,
  "status": "ready",
  "mode": "PAPER",
  "leader": 1,
  "marketdata_heartbeat": 0.5,
  "order_stream_heartbeat": 1.2,
  "scan_heartbeat": 2.3
}
```

**When not ready:**
```json
{
  "ok": false,
  "ready": false,
  "status": "not_ready",
  "mode": "PAPER",
  "leader": 0,
  "marketdata_heartbeat": 999.0,
  ...
}
```

## Troubleshooting

**CORS headers missing:**
- Check middleware is added before routes
- Verify `allow_origins` includes your UI origin
- Restart API after changes

**Dashboard still shows high heartbeats:**
- Wait 10-30 seconds after API starts
- Check orchestrator logs for initialization
- Verify `trader_is_leader` metric: `curl -s http://localhost:8000/metrics | grep trader_is_leader`

**`/ready` still returns 500:**
- Check API logs for exceptions
- Verify Prometheus metrics are initialized
- Ensure trader orchestrator is starting

## Quick Health Check

```bash
# Check if ready
curl -s http://localhost:8000/ready | jq

# Check leader status
curl -s http://localhost:8000/metrics | grep trader_is_leader

# Check heartbeats
curl -s http://localhost:8000/metrics | grep heartbeat_seconds
```






