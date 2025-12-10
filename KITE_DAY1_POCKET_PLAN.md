# Day-1 LIVE Canary — Pocket Plan

**Ultra-tight reference** | Keep this on your phone/second screen

---

## 08:55 (Token + Gate)

```bash
export KITE_API_KEY="***"; export KITE_API_SECRET="***"
make kite-token-refresh     # paste the ACCESS_TOKEN + USER_ID from output

export APP_MODE=LIVE APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="x.x.x.x"   # your allow-listed public IP

make prelive-gate           # must PASS
```

---

## 09:00 (Monitor Up)

```bash
make kite-canary-launch     # readiness + watcher
make kite-canary-status     # quick snapshot in a 2nd tab
```

---

## Optional Sizing (20–50k)

```bash
# pick your capital, keep risk small (e.g., 0.30%)
make kite-size CAPITAL=30000 RISK_PCT=0.30
make kite-size CAPITAL=50000 RISK_PCT=0.30
```

Use the calculator's **net-debit/lot** output to pick a conservative NIFTY weekly **debit call spread**.

---

## 09:30–10:30 (Entry Window)

- One debit-spread attempt only
- Caps: **0.30% risk / 1.0% heat / −1.50% daily / max 1–2 positions**
- Respect exchange freeze quantities (bot auto-batches if needed)

---

## What "Good" Looks Like (Watch Pane)

- `leader = 1`
- All heartbeats `< 5s`
- `scan_ticks_total` rising
- `leader_changes_total = 0`
- `oco_orphans = 0`

---

## Fast Controls

```bash
make kite-canary-status      # status snapshot
curl -s -X POST :8000/flatten | jq   # emergency flatten
make kite-canary-stop        # flatten + stop API
```

---

## If Something Trips

- **Gate fails on IP** → set the correct `EXPECTED_EGRESS_IP`, rerun gate
- **Token issue** → rerun `make kite-token-refresh`, re-export token, continue
- **Heartbeats ≥ 5s or leader flips** → pause entries; if >2–3 min, `make kite-canary-stop`, relaunch

---

## 15:25+ (Wrap)

```bash
make kite-canary-stop
make burnin-report && make reconcile-db && make post-close
make score-day2
```

---

## Tiny Hygiene

- `.env` stays ignored (already set)
- System clock auto-sync on; drift should be tiny
- Keep the watch pane open for the first 10 minutes after launch

---

**You've got conservative sizing, tight guardrails, and clean rollback.**

If any output looks odd, drop the snippet and we'll triage fast.

---

## ⚡ 90-Second Preflight?

For the absolute fastest setup, see:
**`KITE_DAY1_TMINUS90.md`** — T-minus 90s preflight with crisp abort triggers!

