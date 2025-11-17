# Crypto Canary — GO Card (Ultra-Tight Final)

## T-30s Pre-Launch

```bash
export KRAKEN_API_KEY="your_key"
export KRAKEN_API_SECRET="your_secret"
make crypto-prelaunch-smoke
```

**Expect:** Keys ✓, UTC drift < ~2s, `/ready` OK (if API up), **GO/NO-GO = PASS**.

---

## Launch (One Command)

```bash
make crypto-canary-launch
```

---

## First 10 Minutes — Keep This Open

```bash
make watch-crypto
```

**Good =**
- ✅ `trader_is_leader = 1`
- ✅ Heartbeats `< 5s`
- ✅ `trader_oco_orphans_total = 0`
- ✅ `trader_crypto_ws_reconnects_total ≤ 1/10m`
- ✅ `crypto_flatten_duration_seconds` p95 `≤ 2s`
- ✅ Occasional spread-guard skips when spread > 50 bps (that's protection)

---

## Tripwires → Instant Action

### WS reconnects > 3/10m OR any orphan > 0
- **Action**: `make crypto-canary-stop` (flattens & stops) → relaunch once
- **If repeats**: Pause canary, investigate

### Flatten p95 > 2s OR any heartbeat ≥ 5s
- **Action**: Stop; investigate router/network; relaunch after fix
- **Check**: Router logs, network connectivity, exchange status

### Spread guard blocks ≥ 5m
- **Action**: Stay up (it's doing its job); don't force entries
- **Why**: Market protection working as designed

---

## Post-Canary Wrap (After 60–90 min)

```bash
make score-crypto-day1
make crypto-report
```

**Promote only if:**
- ✅ PASS
- ✅ orphans = 0
- ✅ reconnects low
- ✅ SLOs met

---

## Handy Status / Rollback

```bash
make crypto-canary-status   # quick health + key metrics
make crypto-canary-stop     # safe flatten + stop
```

---

## Tiny Hardeners (Quick Wins)

- ✅ IP-lock keys, trading-only, withdrawals disabled
- ✅ `export TZ=UTC` in the shell that runs the canary
- ✅ Keep **BTCUSDT only** for the first live hour (your canary config already enforces this)

---

## Complete Launch Sequence

```bash
# 1. Pre-launch (30 seconds)
export KRAKEN_API_KEY="your_key"
export KRAKEN_API_SECRET="your_secret"
make crypto-prelaunch-smoke

# 2. Launch (one command)
make crypto-canary-launch

# 3. Watch (first 10 minutes - keep this open)
make watch-crypto

# 4. Status check (anytime)
make crypto-canary-status

# 5. Stop if needed
make crypto-canary-stop

# 6. Post-canary wrap (after 60-90 min)
make score-crypto-day1
make crypto-report
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `make crypto-prelaunch-smoke` | 30s pre-launch check |
| `make crypto-canary-launch` | Launch canary |
| `make watch-crypto` | Watch metrics (keep open) |
| `make crypto-canary-status` | Quick health check |
| `make crypto-canary-stop` | Safe stop + flatten |
| `make score-crypto-day1` | Run Day-1 scorer |
| `make crypto-report` | Generate 24h report |

---

## Success Criteria (After 60-90 min)

- ✅ All heartbeats < 5s (stable)
- ✅ 0 orphans throughout
- ✅ WS reconnects ≤ 1/hr
- ✅ Spread guard working (rejects when spread > 50 bps)
- ✅ Flatten p95 < 2s
- ✅ Scorer JSON shows `"status":"PASS"`
- ✅ No precision/minNotional violations

---

## Emergency Rollback

```bash
# Immediate stop and flatten
make crypto-canary-stop

# Revert to PAPER if needed
export APP_MODE=CRYPTO_PAPER
make crypto-paper &
```

---

**You're good to go. Run `make crypto-prelaunch-smoke`, then `make crypto-canary-launch`, keep the watch pane open for 10 minutes, and use the tripwires above for fast decisions.**
