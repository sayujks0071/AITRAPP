# Morning-of Sticky (LIVE Canary, NIFTY Debit Spread)

**Copy this next to your terminal** | Ultra-minimal reference

---

## 08:55 — Token + Gate (≤90s)

```bash
# Token (opens OAuth, prints exports)
export KITE_API_KEY="***"; export KITE_API_SECRET="***"
make kite-token-refresh

# paste the two exports it prints:
export KITE_ACCESS_TOKEN="***"; export KITE_USER_ID="***"

# Mode + IP lock
export APP_MODE=LIVE APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="$(curl -fsS https://api.ipify.org)"
make prelive-gate   # must PASS
```

---

## 09:00 — Launch + Watch

```bash
make kite-canary-launch     # readiness + watcher
make kite-canary-status     # quick snapshot in a 2nd tab
```

---

## 09:25 — Size Check (Pick Your Capital)

```bash
make kite-size CAPITAL=30000 RISK_PCT=0.30
make kite-size CAPITAL=50000 RISK_PCT=0.30
# choose strikes so net-debit/lot ≈ suggested value
```

---

## 09:30–10:30 — Entry Window (1 Attempt Only)

- NIFTY weekly **debit spread** only
- Risk **0.30%** per trade, heat **≤1.0%**, daily stop **−1.50%**
- Max **1–2** concurrent positions
- No re-entries if stopped → wait for tomorrow

---

## "Good" Dashboard (Keep These Green)

- `leader = 1`
- All heartbeats `< 5s`
- `scan_ticks_total` rising
- `leader_changes_total = 0`
- `oco_orphans = 0`

---

## Instant Controls (Memorize)

```bash
make kite-canary-status            # snapshot
curl -fsS -X POST :8000/flatten | jq   # emergency flatten
make kite-canary-stop              # flatten + stop API
```

---

## 🛑 Abort Triggers → Flatten Immediately

- Any heartbeat ≥ **5s** for >2–3 min
- `leader` not 1 or `leader_changes_total > 0`
- Any OCO orphan / repeated rejects
- Prelive gate re-check fails after token/IP refresh

---

## 15:25+ — Wrap

```bash
make kite-canary-stop
make burnin-report && make reconcile-db && make post-close
make score-day2
```

---

## Tiny Hygiene (Do Once)

- Mac "prevent sleep" on; NTP time synced
- `.env` remains git-ignored
- Never paste keys in chat/PRs

---

**You're ready. If any metric twitches, paste the snippet and we'll triage on the spot.**











