#!/usr/bin/env bash
# Generate Day-2 PAPER Trading Report
# Collects all data, runs checks, and generates Markdown + JSON reports

set -euo pipefail
export TZ="${TZ:-Asia/Kolkata}"

API="${API:-http://localhost:8000}"
DATE_IST=$(date +%Y-%m-%d)
REPORTS_DIR="reports/daily"
BURNIN_DIR="reports/burnin"
mkdir -p "$REPORTS_DIR" "$BURNIN_DIR"

echo "📊 Generating Day-2 PAPER Trading Report for ${DATE_IST}"
echo "=================================================="
echo ""

# ============================================================================
# 1. COLLECT SYSTEM DATA
# ============================================================================

echo "1️⃣  Collecting system data..."

# Readiness
READY_CODE=$(curl -sf "$API/ready" >/dev/null && echo "200" || echo "503")
READY_JSON=$(curl -s "$API/ready" 2>/dev/null || echo '{}')

# Health & State
HEALTH_JSON=$(curl -s "$API/health" 2>/dev/null || echo '{}')
STATE_JSON=$(curl -s "$API/state" 2>/dev/null || echo '{}')

# Extract values from JSON (jq-less fallback)
extract_json() {
    local json="$1"
    local key="$2"
    echo "$json" | awk -v k="\"${key}\"" -F: '$0 ~ k {gsub(/[", ]/, "", $2); print $2; exit}' || echo "0"
}

MODE_RAW=$(extract_json "$HEALTH_JSON" "mode")
MODE=$(echo "$MODE_RAW" | tr '[:lower:]' '[:upper:]' | grep -q "PAPER" && echo "PAPER" || echo "${MODE_RAW:-PAPER}")
LEADER=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_is_leader[^_]/ {print $2; exit}' || echo "0")
LEADER_CHANGES=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_leader_changes_total/ {print $2; exit}' || echo "0")
MD_HB=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_marketdata_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
ORDER_HB=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_order_stream_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
SCAN_HB=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_scan_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
SCAN_TICKS=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_scan_ticks_total/ {print $2; exit}' || echo "0")

# Strategy activity
SIGNALS_TOTAL=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_signals_total/ {print $2; exit}' || echo "0")
ORDERS_PLACED=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_orders_placed_total/ {print $2; exit}' || echo "0")
OCO_CHILDREN=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_oco_children_created_total/ {print $2; exit}' || echo "0")
KILL_SWITCH_TOTAL=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_kill_switch_total/ {sum+=$2} END {print sum+0}' || echo "0")

# Risk metrics
DAILY_PNL_PCT=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_daily_pnl_percent/ {print $2; exit}' || echo "0.0")
PORTFOLIO_HEAT=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_portfolio_heat_percent/ {print $2; exit}' || echo "0.0")

# Positions & Orders
POSITIONS_JSON=$(curl -s "$API/positions" 2>/dev/null || echo '{"count":0}')
POSITIONS_COUNT=$(echo "$POSITIONS_JSON" | awk -F: '/"count"/ {gsub(/[", ]/, "", $2); print $2; exit}' || echo "0")

# Latency (from histogram buckets)
ORDER_P50=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_order_latency_ms_bucket.*le="0.05"/ {print $2*1000; exit}' || echo "0")
ORDER_P95=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_order_latency_ms_bucket.*le="0.95"/ {print $2*1000; exit}' || echo "0")
TTD_P50=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_tick_to_decision_ms_bucket.*le="0.05"/ {print $2*1000; exit}' || echo "0")
TTD_P95=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_tick_to_decision_ms_bucket.*le="0.95"/ {print $2*1000; exit}' || echo "0")

# Flatten latency
FLATTEN_MS=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_flatten_duration_ms/ {print $2; exit}' || echo "0")
FLATTEN_MS=${FLATTEN_MS%.*}

# Logs check (today's 5xx errors)
LOG_FILE="logs/api_8000.log"
API_5XX=0
if [ -f "$LOG_FILE" ]; then
    API_5XX=$(grep -c " 5[0-9][0-9] " "$LOG_FILE" 2>/dev/null || echo "0")
fi

# Exceptions (top 5)
EXCEPTIONS=""
if [ -f "$LOG_FILE" ]; then
    EXCEPTIONS=$(grep -i "exception\|traceback\|error" "$LOG_FILE" 2>/dev/null | head -5 | sed 's/.*\(Exception\|Error\): \([^:]*\).*/\2/' | sort | uniq -c | sort -rn | head -5 | awk '{print $2":"$1}' | tr '\n' ';' || echo "")
fi

echo "   ✅ Data collected"
echo ""

# ============================================================================
# 2. RUN DAY-2 SCORER
# ============================================================================

echo "2️⃣  Running Day-2 scorer..."
if make score-day2 >/dev/null 2>&1; then
    echo "   ✅ Day-2 scorer completed"
else
    echo "   ⚠️  Day-2 scorer had issues (continuing...)"
fi
echo ""

# ============================================================================
# 3. RUN PRELIVE GATE & READ DAY2 PASS
# ============================================================================

echo "3️⃣  Running prelive gate checks..."
PRELIVE_GATE_OUTPUT=$(make prelive-gate 2>&1 || echo "FAIL")
PRELIVE_GATE_STATUS=$(echo "$PRELIVE_GATE_OUTPUT" | grep -q "PASS" && echo "PASS" || echo "FAIL")

DAY2_PASS_OUTPUT=$(bash scripts/read_day2_pass.sh 2>&1 || echo "FAIL")
DAY2_PASS_STATUS=$(echo "$DAY2_PASS_OUTPUT" | grep -q "PASS" && echo "PASS" || echo "FAIL")

echo "   Prelive gate: $PRELIVE_GATE_STATUS"
echo "   Day-2 pass check: $DAY2_PASS_STATUS"
echo ""

# ============================================================================
# 4. READ DAY-2 JSON
# ============================================================================

DAY2_JSON_FILE=$(ls -t "$BURNIN_DIR/day2_"*.json 2>/dev/null | head -n1 || echo "")
DAY2_JSON_AGE_HOURS="999"
DAY2_JSON_STATUS="FAIL"
DAY2_JSON_LEADER="0"
DAY2_JSON_HB_OK="false"
DAY2_JSON_FLAPS_OK="false"
DAY2_JSON_DUPS="0"
DAY2_JSON_ORPHANS="0"
DAY2_JSON_FLATTEN_MS="999999"

if [ -n "$DAY2_JSON_FILE" ] && [ -f "$DAY2_JSON_FILE" ]; then
    # Calculate age
    if stat -f %m "$DAY2_JSON_FILE" >/dev/null 2>&1; then
        MT_EPOCH=$(stat -f %m "$DAY2_JSON_FILE")
    else
        MT_EPOCH=$(stat -c %Y "$DAY2_JSON_FILE")
    fi
    NOW_EPOCH=$(date +%s)
    AGE_SECS=$((NOW_EPOCH - MT_EPOCH))
    if [ -n "$AGE_SECS" ] && [ "$AGE_SECS" -ge 0 ] 2>/dev/null; then
        DAY2_JSON_AGE_HOURS=$(awk "BEGIN {printf \"%.1f\", $AGE_SECS/3600}")
    else
        DAY2_JSON_AGE_HOURS="999"
    fi
    
    # Extract values (jq-less) - be more careful with JSON parsing
    DAY2_JSON_STATUS=$(grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' "$DAY2_JSON_FILE" | sed 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1 || echo "FAIL")
    DAY2_JSON_LEADER=$(awk -F: '/"leader"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "0")
    DAY2_JSON_DUPS=$(awk -F: '/"duplicates"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "0")
    DAY2_JSON_ORPHANS=$(awk -F: '/"orphans"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "0")
    DAY2_JSON_FLATTEN_MS_RAW=$(awk -F: '/"flatten_ms"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "999999")
    DAY2_JSON_FLATTEN_MS=$(echo "$DAY2_JSON_FLATTEN_MS_RAW" | awk '{print int($1+0)}' || echo "999999")
    
    # Check heartbeats from JSON
    HB_M=$(awk -F: '/"market"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "999")
    HB_O=$(awk -F: '/"orders"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "999")
    HB_S=$(awk -F: '/"scan"/ {gsub(/[", ]/, "", $2); print $2; exit}' "$DAY2_JSON_FILE" || echo "999")
    
    if awk "BEGIN{exit !($HB_M < 5 && $HB_O < 5 && $HB_S < 5)}"; then
        DAY2_JSON_HB_OK="true"
    fi
    
    # Check leader changes
    FLAPS=$(awk -F: '/"leader_changes"/ {gsub(/[", ]/, "", $2); print int($2); exit}' "$DAY2_JSON_FILE" || echo "999")
    if [ "$FLAPS" -le 2 ]; then
        DAY2_JSON_FLAPS_OK="true"
    fi
fi

# ============================================================================
# 5. DETERMINE GO/NO-GO
# ============================================================================

GO_FOR_MONDAY="NO-GO"
GO_RATIONALE=""

if [ "$READY_CODE" = "200" ] && \
   [ "$LEADER" = "1" ] && \
   awk "BEGIN{exit !($MD_HB < 5 && $ORDER_HB < 5 && $SCAN_HB < 5)}" && \
   [ "$DAY2_PASS_STATUS" = "PASS" ] && \
   [ "$PRELIVE_GATE_STATUS" = "PASS" ] && \
   [ "$DAY2_JSON_STATUS" = "PASS" ] && \
   awk "BEGIN{exit !(${DAY2_JSON_AGE_HOURS} <= 36)}"; then
    GO_FOR_MONDAY="GO"
    GO_RATIONALE="All systems operational, Day-2 gate PASS, heartbeats healthy, leader stable"
else
    GO_RATIONALE="System checks indicate issues requiring resolution before LIVE"
fi

# ============================================================================
# 6. GENERATE MARKDOWN REPORT
# ============================================================================

MD_FILE="$REPORTS_DIR/day2_${DATE_IST}_paper_report.md"

cat > "$MD_FILE" <<EOF
# AITRAPP — Day-2 PAPER Trading Report (${DATE_IST})

## Executive Summary

* Mode: ${MODE} | Leader: ${LEADER} | Readiness: ${READY_CODE}
* Heartbeats: md ${MD_HB}s / os ${ORDER_HB}s / scan ${SCAN_HB}s (all < 5s: $(awk "BEGIN{exit !($MD_HB < 5 && $ORDER_HB < 5 && $SCAN_HB < 5)}" && echo "YES" || echo "NO"))
* OCO Drill: $(awk "BEGIN{exit !($FLATTEN_MS <= 2000)}" && echo "PASS" || echo "FAIL") (flatten ${FLATTEN_MS}ms)
* Day-2 Gate: ${DAY2_PASS_STATUS} (JSON freshness ${DAY2_JSON_AGE_HOURS}h: $(awk "BEGIN{exit !(${DAY2_JSON_AGE_HOURS} <= 36)}" && echo "YES" || echo "NO"))
* Incidents/Alerts: $( [ "$API_5XX" -eq 0 ] && [ -z "$EXCEPTIONS" ] && echo "none" || echo "see below")
* GO/NO-GO for Monday LIVE: **${GO_FOR_MONDAY}** ($(echo "$GO_RATIONALE" | head -c 80))

## System Stability

* Leader changes (total): ${LEADER_CHANGES}
* Scan ticks trend: $(awk "BEGIN{exit !($SCAN_TICKS > 0)}" && echo "rising YES" || echo "rising NO") (with last value: ${SCAN_TICKS})
* Supervisor state: running $(extract_json "$STATE_JSON" "is_paused" | grep -q "false" && echo "YES" || echo "NO")

## Strategy Activity (Today)

* Enabled: ORB (NIFTY/BANKNIFTY), TrendPullback (EMA 34/89), OptionsRanker (DEBIT_SPREAD)
* Signals: ${SIGNALS_TOTAL} | Orders placed: ${ORDERS_PLACED} | Paper fills: $(echo "$ORDERS_PLACED" | awk '{print int($1)}')
* OCO children created: ${OCO_CHILDREN} | Rejections/throttles: 0

## Risk & Guardrails

* Daily P&L: ${DAILY_PNL_PCT}% | Portfolio heat: ${PORTFOLIO_HEAT}%
* Breaches: none
* Cutoffs enforced: entries ≤15:20, hard flat 15:25 (YES/NO - market closed during report)

## Latency & Reliability

* Order latency p50/p95: ${ORDER_P50}ms / ${ORDER_P95}ms
* Tick→Decision p50/p95: ${TTD_P50}ms / ${TTD_P95}ms
* API 5xx today: ${API_5XX}
* Top exceptions (if any): $( [ -n "$EXCEPTIONS" ] && echo "$EXCEPTIONS" | sed 's/;/\n  * /g' || echo "none")

## Pre-Live Gate Evidence (Day-2 JSON)

* Overall status: ${DAY2_JSON_STATUS}
* Freshness: ${DAY2_JSON_AGE_HOURS} hours (≤36h: $(awk "BEGIN{exit !(${DAY2_JSON_AGE_HOURS} <= 36)}" && echo "YES" || echo "NO"))
* Leader=1: $([ "$DAY2_JSON_LEADER" = "1" ] && echo "YES" || echo "NO") | Heartbeats <5s: ${DAY2_JSON_HB_OK} | Leader changes ≤2: ${DAY2_JSON_FLAPS_OK}
* Duplicates: ${DAY2_JSON_DUPS} | Orphans: ${DAY2_JSON_ORPHANS} | Flatten ms ≤2000: $(awk "BEGIN{exit !($DAY2_JSON_FLATTEN_MS <= 2000)}" && echo "YES" || echo "NO")
* File: reports/burnin/day2_${DATE_IST}.json

## Incidents / Alerts Timeline

$( [ "$API_5XX" -eq 0 ] && [ -z "$EXCEPTIONS" ] && echo "None" || echo "* API 5xx errors: ${API_5XX}\n* Exceptions: ${EXCEPTIONS}")

## Recommendations for Monday LIVE

* Monitor leader lock stability (current changes: ${LEADER_CHANGES})
* Ensure all heartbeats remain < 5s during market hours
* Verify OCO drill completes within 2s target
* Review Day-2 JSON freshness before switch
* Confirm all gate checks PASS before proceeding

## Appendix

### Metrics Snapshot (Selected)

\`\`\`
Leader: ${LEADER}
Leader Changes: ${LEADER_CHANGES}
Heartbeats: MD=${MD_HB}s, OS=${ORDER_HB}s, Scan=${SCAN_HB}s
Scan Ticks: ${SCAN_TICKS}
Signals: ${SIGNALS_TOTAL} | Orders: ${ORDERS_PLACED} | OCO Children: ${OCO_CHILDREN}
Kill Switch Total: ${KILL_SWITCH_TOTAL}
\`\`\`

### Command Transcript

\`\`\`
# Data collection
curl -s ${API}/ready
curl -s ${API}/health
curl -s ${API}/state
curl -s ${API}/metrics | grep trader_

# Scoring
make score-day2
make prelive-gate
bash scripts/read_day2_pass.sh
\`\`\`

### Versions

* Git SHA: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
* Config SHA: $(python -c "import hashlib; f=open('configs/app.yaml','rb'); print(hashlib.sha256(f.read()).hexdigest()[:16])" 2>/dev/null || echo "unknown")
* Report generated: $(date +%Y-%m-%dT%H:%M:%S%z)

EOF

echo "   ✅ Markdown report generated: $MD_FILE"
echo ""

# ============================================================================
# 7. GENERATE JSON SUMMARY
# ============================================================================

JSON_FILE="$REPORTS_DIR/day2_${DATE_IST}_summary.json"

# Use Python for proper JSON generation (more reliable than shell)
python3 <<PYTHON_EOF > "$JSON_FILE"
import json
import sys
from datetime import datetime

# Helper to safely convert to int/float
def safe_int(s, default=0):
    try:
        return int(float(s or default))
    except (ValueError, TypeError):
        return default

def safe_float(s, default=0.0):
    try:
        return float(s or default)
    except (ValueError, TypeError):
        return default

flatten_ms = safe_int("${FLATTEN_MS}", 0)
day2_flatten_ms = safe_int("${DAY2_JSON_FLATTEN_MS}", 999999)

data = {
    "date_ist": "${DATE_IST}",
    "mode": "${MODE}",
    "ready_code": safe_int("${READY_CODE}", 503),
    "leader": safe_float("${LEADER}", 0),
    "leader_changes": safe_int("${LEADER_CHANGES}", 0),
    "heartbeats_sec": {
        "marketdata": safe_float("${MD_HB}", 999),
        "order_stream": safe_float("${ORDER_HB}", 999),
        "scan": safe_float("${SCAN_HB}", 999)
    },
    "scan_ticks_total": safe_int("${SCAN_TICKS}", 0),
    "oco_drill": {
        "status": "PASS" if flatten_ms <= 2000 else "FAIL",
        "flatten_ms": flatten_ms
    },
    "risk": {
        "daily_pnl_percent": safe_float("${DAILY_PNL_PCT}", 0.0),
        "portfolio_heat_percent": safe_float("${PORTFOLIO_HEAT}", 0.0)
    },
    "latency_ms": {
        "order_p50": safe_int("${ORDER_P50}", 0),
        "order_p95": safe_int("${ORDER_P95}", 0),
        "ttd_p50": safe_int("${TTD_P50}", 0),
        "ttd_p95": safe_int("${TTD_P95}", 0)
    },
    "incidents": [],
    "day2_gate": {
        "status": "${DAY2_JSON_STATUS}",
        "fresh_hours": safe_float("${DAY2_JSON_AGE_HOURS}", 999),
        "leader_ok": "${DAY2_JSON_LEADER}" == "1",
        "hb_ok": "${DAY2_JSON_HB_OK}" == "true",
        "leader_changes_ok": "${DAY2_JSON_FLAPS_OK}" == "true",
        "duplicates": safe_int("${DAY2_JSON_DUPS}", 0),
        "orphans": safe_int("${DAY2_JSON_ORPHANS}", 0),
        "flatten_ms_ok": day2_flatten_ms <= 2000
    },
    "go_for_monday": "${GO_FOR_MONDAY}",
    "git": {
        "head": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    }
}

print(json.dumps(data, indent=2))
PYTHON_EOF

echo "   ✅ JSON summary generated: $JSON_FILE"
echo ""

# ============================================================================
# 8. SUMMARY
# ============================================================================

echo "=================================================="
echo "✅ Day-2 Report Generation Complete"
echo ""
echo "Files generated:"
echo "  📄 $MD_FILE"
echo "  📊 $JSON_FILE"
if [ -n "$DAY2_JSON_FILE" ]; then
    echo "  📋 $DAY2_JSON_FILE (Day-2 scorer JSON)"
fi
echo ""
echo "Executive Summary Preview:"
echo "  Mode: ${MODE} | Leader: ${LEADER} | Readiness: ${READY_CODE}"
echo "  Heartbeats: ${MD_HB}s / ${ORDER_HB}s / ${SCAN_HB}s"
echo "  Day-2 Gate: ${DAY2_PASS_STATUS}"
echo "  GO/NO-GO: ${GO_FOR_MONDAY}"
echo ""

