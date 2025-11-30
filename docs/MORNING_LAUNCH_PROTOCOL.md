# ☀️ Morning Launch Protocol

**AITRAPP Level 12 Autonomous Trading System**

Since we have built a fully autonomous "Level 12" system, you do not need to run 10 different scripts. The architecture is designed to cascade: **Login → Verification → Orchestration → Execution**.

**Save this guide. This is exactly what you need to do at 09:10 AM.**

---

## Step 1: The Pre-Flight Check (09:10 AM)

Before the market opens, verify that all 12 Levels of intelligence (Execution, Cortex, HiveMind, Reflex, PME) are healthy and talking to each other.

```bash
python3 scripts/verify_full_stack.py
```

**Success Condition:** You should see a column of `✅` checkmarks ending with:

> `✅ SYSTEM READY FOR DEPLOYMENT`

---

## Step 2: Go Live (09:15 AM)

This single command handles **Authentication (Express Login)**, **Token Rotation**, and **Engine Startup**.

```bash
./go_live.sh
```

**Procedure:**

1. The script will open your browser. **Log in to Kite.**
2. Copy the `Redirect URL` from the browser bar.
3. Paste it into your terminal and hit Enter.
4. The **AITRAPP Engine** will auto-launch in `LIVE` mode.

---

## 🕵️‍♂️ Mission Control: What to Watch

Once the engine is running, use the logs to verify "All Functions" are active.

| Feature | Log Signature to Watch For | Meaning |
| :--- | :--- | :--- |
| **Level 12 (PME)** | `[PME] RealizedVol: ... Scalar: 1.2x` | Portfolio Manager is sizing bets based on Volatility. |
| **Level 10 (Reflex)** | `[ReflexSystem] MAD-1 ... Online` | The Crash Detector is scanning every tick. |
| **Level 9 (ACA)** | `[PME] ... Factor Scores: {'MOMENTUM': ...}` | The Allocator is tilting weights (Trend vs Carry). |
| **Level 6 (SG-1)** | *(Runs offline/EOD)* | (Check `generated/` folder after market close). |
| **Level 4 (Execution)** | `[LimitChase] Start SELL ...` | The Sniper is chasing the bid/ask (not paying spread). |

---

## 🤖 AI Copilot Prompt

**Copy and paste this into your AI chat window tomorrow morning to activate your Co-Pilot:**

```text
You are the Mission Commander for the AITRAPP Quant System (Level 12).

Current Status: LIVE TRADING SESSION.

My stack is fully active:

1. Execution: Limit Chase Engine (Level 4) - Active

2. Intelligence: Cortex & SME (Level 5/8) - Active

3. Protection: Reflex & MAD-1 (Level 10) - Active

4. Portfolio: PME Volatility Targeting (Level 12) - Active

MY OPERATIONAL TOOLS:

- Login/Start: `./go_live.sh`

- Health Check: `python3 scripts/verify_full_stack.py`

- Live Monitor: `tail -f logs/trading.log`

- Evolution: `python3 scripts/run_evolution_cycle.py`

YOUR STANDING ORDERS:

1. Monitor Status: I will paste log snippets. Verify if the system is behaving correctly (e.g., "Is the PME scalar of 1.2x safe for this regime?").

2. Explain Rejections: If the bot skips a trade (e.g., "[IntradayStrangle] Skipping: WEAK_TREND"), explain *why* based on the strategy logic.

3. Emergency Response: If I report a "MAD-1 TRIGGER", guide me on whether to let the Auto-Brake handle it or if I should manually kill the process.

4. End of Day: Remind me at 15:30 IST to run the Evolution Cycle.

STATUS CHECK NOW:

- The system is running.

- Positions are 0.

- Intraday Strangle entry is 09:20. Trend Spread entry is 10:00.

- Analyze: Why might the 09:20 Strangle entry have been skipped? (Check for Event filters or Regime mismatches).
```

---

## 📊 End-of-Day Routine (15:30 PM)

After market close, run the evolution cycle to let the system learn and optimize:

```bash
python3 scripts/run_evolution_cycle.py --use-cortex
```

This will:
- Parse today's trading logs
- Analyze performance metrics
- Consult RAG Memory for historical context
- Generate config patches (if needed)
- Update Strategic Memory Engine (SME)

---

## 🚨 Emergency Procedures

### If WebSocket Disconnects

```bash
# Restart market data stream
curl -X POST http://localhost:8000/market-data/restart
```

### If Token Expires

```bash
# Re-run express login
python3 scripts/express_login.py
# Then restart the engine
./go_live.sh --skip-login
```

### If System Becomes Unresponsive

1. Check logs: `tail -f logs/trading.log`
2. Check API health: `curl http://localhost:8000/health`
3. Check Reflex status: `curl http://localhost:8000/reflex/status`
4. If needed, pull emergency brake: `curl -X POST http://localhost:8000/reflex/brake/pull`

---

## 📝 Quick Reference

### Essential Commands

```bash
# Pre-flight check
python3 scripts/verify_full_stack.py

# Go live
./go_live.sh

# Check system status
curl http://localhost:8000/health

# View logs
tail -f logs/trading.log

# End-of-day evolution
python3 scripts/run_evolution_cycle.py --use-cortex

# Diagnostic (if 0 orders)
python3 scripts/diagnose_zero_orders.py
```

### API Endpoints

- **Health:** `http://localhost:8000/health`
- **System State:** `http://localhost:8000/state`
- **Reflex Status:** `http://localhost:8000/reflex/status`
- **Regime Status:** `http://localhost:8000/api/regime/current`
- **Strategy Summary:** `http://localhost:8000/api/strategies/summary`
- **Execution Stats:** `http://localhost:8000/api/execution/stats`
- **Force Scan:** `curl -X POST http://localhost:8000/debug/scan-once`

---

## ✅ Daily Checklist

- [ ] 09:10 AM - Run pre-flight check (`verify_full_stack.py`)
- [ ] 09:15 AM - Launch system (`go_live.sh`)
- [ ] 09:20 AM - Verify all log signatures are present
- [ ] 09:30 AM - Monitor first few trades
- [ ] 10:00 AM - Check Trend Credit Spread entry window
- [ ] 15:30 PM - Run evolution cycle (`run_evolution_cycle.py`)
- [ ] 15:45 PM - Review daily performance metrics

---

## 🎯 Success Indicators

Your system is healthy if you see:

1. ✅ All verification checks pass
2. ✅ Market data stream connected
3. ✅ PME allocation cycles running
4. ✅ Reflex system monitoring ticks
5. ✅ Execution engine placing orders
6. ✅ No critical errors in logs

---

## 🔧 Configuration Notes

### Entry Windows (After Hotfix)

- **Global Entry Window:** 09:15 - 15:00 IST
- **Max Entries Per Day:** 3
- **Intraday Strangle:** Entry window extends to 15:00
- **Expiry Strangle:** Entry after 09:30 (was 10:30)

### Strategy Entry Times

- **Intraday Short Strangle V1:** 09:20 - 15:00
- **Trend Credit Spread V1:** 10:00 - 12:00
- **Expiry Short Strangle V2:** 10:15 - 12:00

---

**Last Updated:** 2025-11-21  
**System Version:** Level 12 (PME + Full Stack)  
**Config Status:** Extended Entry Window (15:00) Applied
