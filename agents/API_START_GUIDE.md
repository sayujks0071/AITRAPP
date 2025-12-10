# Binance Crypto Paper API - Start Guide

## Current Status

✅ **Keys are set** in your current shell session  
✅ **Infra is running** (Postgres + Redis)  
✅ **Config is ready** (crypto_paper.yaml)  
⚠️ **Dependencies need installation**

## Quick Start (All-in-One)

```bash
# 1. Set keys (already done in this shell)
export BINANCE_API_KEY="sGxx4Ew7NpskzfhmgRhWWaBwGRQlgPNLGyZTdlGLTqoomBaJ1T01gS4ImLn9MdK9"
export BINANCE_API_SECRET="CGgUGCTfbg3TXN7AycyxFd7YFFy1YYEjK8O2dKg7PBg3d1RmcxiD4BmLtBwzauZC"

# 2. Setup venv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install uvicorn fastapi structlog httpx websockets pyyaml pandas numpy psycopg2-binary redis prometheus-client kiteconnect pydantic pytz

# 3. Config
cp configs/crypto_paper.yaml configs/app.yaml
export APP_MODE=CRYPTO_PAPER APP_TIMEZONE=UTC PYTHONPATH=.

# 4. Start API
source .venv/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &

# 5. Wait and check
sleep 20
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/ready | jq

# 6. Watch metrics (in new terminal)
make watch-crypto

# 7. Test OCO
make crypto-oco-drill
```

## Using Makefile (Recommended)

Once dependencies are installed:

```bash
# Set keys
export BINANCE_API_KEY="sGxx4Ew7NpskzfhmgRhWWaBwGRQlgPNLGyZTdlGLTqoomBaJ1T01gS4ImLn9MdK9"
export BINANCE_API_SECRET="CGgUGCTfbg3TXN7AycyxFd7YFFy1YYEjK8O2dKg7PBg3d1RmcxiD4BmLtBwzauZC"

# Config
cp configs/crypto_paper.yaml configs/app.yaml
export APP_MODE=CRYPTO_PAPER APP_TIMEZONE=UTC PYTHONPATH=.

# Start
make crypto-paper &

# Monitor
make watch-crypto
```

## Troubleshooting

### Missing Dependencies
```bash
source .venv/bin/activate
pip install <missing_package>
```

### API Won't Start
```bash
# Check logs
tail -f /tmp/aitrapp_crypto.log

# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f uvicorn
```

### Keys Not Found
```bash
# Re-export in current shell
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
```

## Next Steps After API Starts

1. ✅ Verify `/health` shows `crypto_venue: "BINANCE_SPOT"`
2. ✅ Check `/ready` returns 200
3. ✅ Monitor metrics with `make watch-crypto`
4. ✅ Run OCO drill: `make crypto-oco-drill`
5. ✅ Score Day-1: `make score-crypto-day1`

---

**Your keys are ready. Install dependencies and start the API!**

