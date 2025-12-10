# 🚀 Start Binance Crypto Paper Session NOW

## Your Keys Are Set (Current Shell Only)

The keys are exported in your current terminal session. They will persist until you close the terminal.

**To make them permanent**, add to your `~/.zshrc` or `~/.bashrc`:
```bash
export BINANCE_API_KEY="sGxx4Ew7NpskzfhmgRhWWaBwGRQlgPNLGyZTdlGLTqoomBaJ1T01gS4ImLn9MdK9"
export BINANCE_API_SECRET="CGgUGCTfbg3TXN7AycyxFd7YFFy1YYEjK8O2dKg7PBg3d1RmcxiD4BmLtBwzauZC"
```

---

## Quick Start (Copy-Paste)

```bash
# 1. Ensure keys are set (already done in this shell)
export BINANCE_API_KEY="sGxx4Ew7NpskzfhmgRhWWaBwGRQlgPNLGyZTdlGLTqoomBaJ1T01gS4ImLn9MdK9"
export BINANCE_API_SECRET="CGgUGCTfbg3TXN7AycyxFd7YFFy1YYEjK8O2dKg7PBg3d1RmcxiD4BmLtBwzauZC"

# 2. Start infra (if not running)
docker compose up -d postgres redis

# 3. Setup venv (if not done)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Config
cp configs/crypto_paper.yaml configs/app.yaml
export APP_MODE=CRYPTO_PAPER APP_TIMEZONE=UTC PYTHONPATH=.

# 5. Pre-flight check
make crypto-prelaunch-smoke

# 6. Launch (background)
make crypto-paper &

# 7. Wait for readiness
sleep 10 && curl -fsS http://localhost:8000/ready | jq

# 8. Watch metrics (in new terminal)
make watch-crypto

# 9. Test OCO
make crypto-oco-drill
```

---

## What to Watch

### Green State Indicators:
- `trader_is_leader = 1`
- All heartbeats < 5s
- `trader_oco_orphans_total = 0`
- `trader_binance_time_skew_ms < 1000`
- `trader_binance_used_weight_1m < 900`

### Red Flags:
- WS reconnects > 3/10min → investigate network
- OCO orphans > 0 → stop and check
- Time skew > 5000ms → check NTP
- Rate limit near cap → throttle activity

---

## Emergency Stop

```bash
make crypto-canary-stop
```

---

## End of Session

```bash
make score-crypto-day1
make crypto-report
make crypto-canary-stop
```

---

**You're ready to go!** Run the commands above to start your Binance paper session.

