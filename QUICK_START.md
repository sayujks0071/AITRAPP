# 🚀 AITRAPP Quick Start

**Level 12 Autonomous Trading System**

---

## ☀️ Morning Routine (2 Commands)

### 1. Pre-Flight Check (09:10 AM)
```bash
python3 scripts/verify_full_stack.py
```
✅ Should see: `SYSTEM READY FOR DEPLOYMENT`

### 2. Go Live (09:15 AM)
```bash
./go_live.sh
```
- Browser opens → Login to Kite
- Paste redirect URL → Engine starts

---

## 📊 What to Watch

| Level | Log Signature | Meaning |
|-------|---------------|---------|
| **PME** | `[PME] Scalar: 1.2x` | Volatility targeting active |
| **Reflex** | `[ReflexSystem] MAD-1 Online` | Crash detector scanning |
| **Execution** | `[LimitChase] Start SELL` | Sniper chasing prices |
| **Market Data** | `Market Data: ✅ CONNECTED` | WebSocket streaming |

---

## 🎯 End of Day (15:30 PM)

```bash
python3 scripts/run_evolution_cycle.py --use-cortex
```

---

## 🚨 Emergency

- **WebSocket down:** `curl -X POST http://localhost:8000/market-data/restart`
- **Token expired:** `python3 scripts/express_login.py`
- **System stuck:** Check `tail -f logs/trading.log`

---

**Full Guide:** See `docs/MORNING_LAUNCH_PROTOCOL.md`





