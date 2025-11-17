# T-minus 90s Preflight

**Ultra-crisp reference** | 90-second setup → launch

---

## T-minus 90s Preflight

```bash
# 1) Token
export KITE_API_KEY="***"; export KITE_API_SECRET="***"
make kite-token-refresh  # paste ACCESS_TOKEN + USER_ID exports it prints

# 2) Mode + IP gate
export APP_MODE=LIVE APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="x.x.x.x"   # your allow-listed public IP
make prelive-gate        # must PASS

# 3) Launch + watch
make kite-canary-launch  # readiness + watcher
make kite-canary-status  # quick snapshot in a 2nd tab
```

---

## Entry Window (09:30–10:30 IST)

- 1 debit-spread attempt only (NIFTY weekly)
- Risk **0.30%**, heat ≤ **1.0%**, daily stop **−1.50%**, max **1–2** positions

**Use calculator right before entry:**
```bash
make kite-size CAPITAL=30000 RISK_PCT=0.30
make kite-size CAPITAL=50000 RISK_PCT=0.30
```

Pick strikes so **net-debit/lot** ≈ output; keep fills clean.

---

## What "Good" Looks Like (Watch Pane)

- `leader = 1`
- All heartbeats `< 5s`
- `scan_ticks_total` rising
- `leader_changes_total = 0`
- `oco_orphans = 0`

---

## Fast Controls (Memorize)

```bash
make kite-canary-status         # snapshot
curl -s -X POST :8000/flatten | jq   # emergency flatten
make kite-canary-stop           # flatten + stop API
```

---

## 🛑 Abort Triggers (Instant Flatten)

- **Gate fails** after token/IP recheck
- **Heartbeats ≥ 5s** for >2–3 minutes or **leader flips**
- **Any orphan OCO** or repeated reject/error loops

**Action:** `make kite-canary-stop` → diagnose → relaunch

---

## Post-Close (15:25+)

```bash
make kite-canary-stop
make burnin-report && make reconcile-db && make post-close
make score-day2
```

---

## Tiny Hygiene

- `.env` stays ignored (already configured)
- Don't paste secrets in chat/PRs
- Keep the watch pane open for the first 10 minutes after launch

---

**You're set. If anything looks the slightest bit weird, paste the snippet and we'll triage fast.**

---

## 📌 Sticky Note Version?

For a literal sticky note to copy next to your terminal, see:
**`KITE_DAY1_STICKY_NOTE.md`** — Ultra-minimal, copy-paste ready!

