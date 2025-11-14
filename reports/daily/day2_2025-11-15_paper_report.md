# AITRAPP — Day-2 PAPER Trading Report (2025-11-15)

## Executive Summary

* Mode: PAPER | Leader: 1.0 | Readiness: 200
* Heartbeats: md 0.5014352920006786s / os 0.003972542002884438s / scan 0.689380458999949s (all < 5s: YES)
* OCO Drill: FAIL (flatten ms)
* Day-2 Gate: FAIL (JSON freshness 28.2h: YES)
* Incidents/Alerts: see below
* GO/NO-GO for Monday LIVE: **NO-GO** (System checks indicate issues requiring resolution before LIVE)

## System Stability

* Leader changes (total): 116.0
* Scan ticks trend: rising YES (with last value: 4426.0)
* Supervisor state: running NO

## Strategy Activity (Today)

* Enabled: ORB (NIFTY/BANKNIFTY), TrendPullback (EMA 34/89), OptionsRanker (DEBIT_SPREAD)
* Signals:  | Orders placed:  | Paper fills: 0
* OCO children created: 0.0 | Rejections/throttles: 0

## Risk & Guardrails

* Daily P&L: % | Portfolio heat: %
* Breaches: none
* Cutoffs enforced: entries ≤15:20, hard flat 15:25 (YES/NO - market closed during report)

## Latency & Reliability

* Order latency p50/p95: ms / ms
* Tick→Decision p50/p95: ms / ms
* API 5xx today: 0
0
* Top exceptions (if any): {"event"::1
  * {"event"::1
  * {"event"::1
  * {"event"::1
  * RuntimeWarning::1
  * 

## Pre-Live Gate Evidence (Day-2 JSON)

* Overall status: PASS
* Freshness: 28.2 hours (≤36h: YES)
* Leader=1: NO | Heartbeats <5s: true | Leader changes ≤2: true
* Duplicates:  | Orphans:  | Flatten ms ≤2000: YES
* File: reports/burnin/day2_2025-11-15.json

## Incidents / Alerts Timeline

* API 5xx errors: 0
0\n* Exceptions: {"event"::1;{"event"::1;{"event"::1;{"event"::1;RuntimeWarning::1;

## Recommendations for Monday LIVE

* Monitor leader lock stability (current changes: 116.0)
* Ensure all heartbeats remain < 5s during market hours
* Verify OCO drill completes within 2s target
* Review Day-2 JSON freshness before switch
* Confirm all gate checks PASS before proceeding

## Appendix

### Metrics Snapshot (Selected)

```
Leader: 1.0
Leader Changes: 116.0
Heartbeats: MD=0.5014352920006786s, OS=0.003972542002884438s, Scan=0.689380458999949s
Scan Ticks: 4426.0
Signals:  | Orders:  | OCO Children: 0.0
Kill Switch Total: 67
```

### Command Transcript

```
# Data collection
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/health
curl -s http://localhost:8000/state
curl -s http://localhost:8000/metrics | grep trader_

# Scoring
make score-day2
make prelive-gate
bash scripts/read_day2_pass.sh
```

### Versions

* Git SHA: de368ab
* Config SHA: unknown
* Report generated: 2025-11-15T00:58:22+0530

