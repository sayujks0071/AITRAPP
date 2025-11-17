# Kite Day-1 LIVE Canary — T-minus 10 Checklist

**Ultra-lean copy/paste reference** | Keep this open tomorrow morning

---

## ⏰ 08:55 — Token + Gate

```bash
export KITE_API_KEY="***"; export KITE_API_SECRET="***"
make kite-token-refresh     # paste the exported ACCESS_TOKEN + USER_ID it prints

export APP_MODE=LIVE APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="x.x.x.x"   # must match broker allowlist

make prelive-gate           # PASS required
```

---

## ⏰ 09:00 — Monitor Up

```bash
make kite-canary-launch     # starts watcher + readiness checks
make kite-canary-status     # quick sanity in a second tab
```

**Optional sizing sanity:**
```bash
make kite-size CAPITAL=30000 RISK_PCT=0.30
```

---

## 📊 What "Good" Looks Like

- `leader = 1`
- All heartbeats `< 5s`
- `scan_ticks` rising, `leader_changes = 0`
- `oco_orphans = 0`

---

## ⏰ Entry Window (09:30–10:30 IST)

- One **debit spread** attempt, NIFTY weekly
- Caps: 0.30% risk / 1.0% heat / −1.50% daily / max 1–2 positions
- Hard flat 15:25

---

## 🛑 Fast Controls (Memorize)

```bash
make kite-canary-status     # snapshot
make kite-canary-stop       # flatten + stop API
curl -s -X POST :8000/flatten | jq   # emergency flatten
```

---

## ⚠️ If Something Trips

- **Heartbeats ≥ 5s** or **leader flips** → pause entries; if >2–3 min, `make kite-canary-stop`, relaunch
- **Gate blocks on IP** → update `EXPECTED_EGRESS_IP` to your allow-listed public IP, rerun gate
- **Token issue** → rerun `make kite-token-refresh`; if 2FA delay, keep monitor running in PAPER until token ready

---

## ⏰ Post-Close (15:25+)

```bash
make kite-canary-stop
make burnin-report && make reconcile-db && make post-close
make score-day2
```

---

## 💡 Tiny Hardeners

- ✅ `.env` in `.gitignore` (already set)
- ✅ System clock in IST ±2s (mac auto time sync on)
- ✅ Keep watch pane open first 10 minutes after launch

---

**You're set. Tomorrow should be smooth—conservative risk, tight guardrails, quick exits.**

If anything looks off, drop the snippet/output and we'll triage fast.

---

## 📱 Even Leaner?

For an ultra-tight pocket reference, see:
**`KITE_DAY1_POCKET_PLAN.md`** — Perfect for phone/second screen!

