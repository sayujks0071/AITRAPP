#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"
ACK_P95_MS_MAX="${ACK_P95_MS_MAX:-500}"
HEARTBEAT_MAX="${HEARTBEAT_MAX:-5}" # seconds
LEADER_REQUIRED="${LEADER_REQUIRED:-1}"

fail() { 
    echo "❌ PRELIVE GATE FAIL: $1" >&2
    exit 1
}

pass() {
    echo "✅ $1"
}

# Extract metrics
leader=$(curl -s "$API/metrics" 2>/dev/null | awk -F' ' '/^trader_is_leader[^_]/ {print $2; exit}' || echo "0")
mkt=$(curl -s "$API/metrics" 2>/dev/null | awk -F' ' '/^trader_marketdata_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
ord=$(curl -s "$API/metrics" 2>/dev/null | awk -F' ' '/^trader_order_stream_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")

# Dry flatten test
if command -v gdate >/dev/null 2>&1; then
    t0=$(gdate +%s%3N)
    t1_cmd="gdate +%s%3N"
else
    t0=$(python3 -c "import time; print(int(time.time() * 1000))" 2>/dev/null || echo "$(date +%s)000")
    t1_cmd='python3 -c "import time; print(int(time.time() * 1000))"'
fi

curl -s -X POST "$API/flatten" -H "Content-Type: application/json" -d '{"reason":"prelive_gate"}' >/dev/null || fail "Flatten endpoint failed"
sleep 2
open=$(curl -s "$API/positions" 2>/dev/null | jq -r '.count // . | length' 2>/dev/null || echo "0")
t1=$(eval "$t1_cmd" 2>/dev/null || echo "$(date +%s)000")
flat_ms=$((t1 - t0))

# Check open orders
open_orders=$(curl -s "$API/orders" 2>/dev/null | jq -r '. | length' 2>/dev/null || echo "0")

# Validate checks
PASS=1
[[ "${leader:-0}" == "$LEADER_REQUIRED" ]] || PASS=0
awk "BEGIN{exit !(${mkt:-999} < $HEARTBEAT_MAX && ${ord:-999} < $HEARTBEAT_MAX)}" || PASS=0
[[ "$open" -eq 0 ]] || PASS=0
[[ $flat_ms -le 2000 ]] || PASS=0
[[ "$open_orders" -eq 0 ]] || PASS=0

# 6) Scan heartbeat must be fresh
echo "Checking scan heartbeat..."
SCAN=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_scan_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
if awk "BEGIN{exit !(${SCAN:-999} < $HEARTBEAT_MAX)}"; then
    pass "Scan heartbeat OK (${SCAN}s, max=${HEARTBEAT_MAX}s)"
else
    PASS=0
    echo "❌ PRELIVE GATE FAIL: Stale scan heartbeat (${SCAN}s, max=${HEARTBEAT_MAX}s)" >&2
fi
    
# 7) Schema gate: details column exists and action is enum type
echo "Checking audit_logs schema..."
if command -v psql >/dev/null 2>&1 && [ -n "${DATABASE_URL:-}" ]; then
    DB_CONN="${DATABASE_URL#postgresql+psycopg2://}"
    SCHEMA_OK=$(psql "$DB_CONN" -tAc "
        SELECT (SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name='audit_logs' AND column_name='details')=1
           AND (SELECT typname FROM pg_type 
                WHERE oid=(SELECT atttypid FROM pg_attribute 
                           WHERE attrelid='audit_logs'::regclass AND attname='action'))='auditactionenum';
    " 2>/dev/null | grep -qx 't' && echo 't' || echo 'f')
    
    if [[ "$SCHEMA_OK" == "t" ]]; then
        pass "audit_logs schema aligned (details column + enum action)"
    else
        PASS=0
        fail "audit_logs schema not aligned (details/enum check failed)"
    fi
else
    echo "⚠️  Schema check skipped (psql not available or DATABASE_URL not set)"
fi

# Output JSON summary
jq -n \
  --arg leader "${leader:-0}" \
  --arg mkt "${mkt:-999}" \
  --arg ord "${ord:-999}" \
  --argjson flat_ms "$flat_ms" \
  --argjson positions_open "$open" \
  --argjson orders_open "$open_orders" \
  --arg status "$( [[ $PASS -eq 1 ]] && echo "PASS" || echo "FAIL" )" \
  '{
    status: $status,
    leader: ($leader | tonumber),
    heartbeats: {
      market: ($mkt | tonumber),
      orders: ($ord | tonumber),
      scan: ($SCAN | tonumber)
    },
    flatten_ms: $flat_ms,
    positions_open: $positions_open,
    orders_open: $orders_open
  }'

# Human-readable output
if [[ $PASS -eq 1 ]]; then
    echo ""
    echo "✅ PRELIVE GATE PASS - System ready for LIVE switch"
    exit 0
else
    echo ""
    # Explicit gate: fail immediately if leader == 0 (prevents Redis compatibility regression)
    [[ "${leader:-0}" == "$LEADER_REQUIRED" ]] || fail "Leader lock not held (trader_is_leader=${leader:-0}, expected $LEADER_REQUIRED) - Redis compatibility regression?"
    awk "BEGIN{exit !(${mkt:-999} < $HEARTBEAT_MAX && ${ord:-999} < $HEARTBEAT_MAX)}" || fail "Stale heartbeats (marketdata=${mkt}s, order_stream=${ord}s, max=${HEARTBEAT_MAX}s)"
    [[ "$open" -eq 0 ]] || fail "Positions not flat after flatten (count=$open)"
    [[ $flat_ms -le 2000 ]] || fail "Flatten exceeded 2s: ${flat_ms}ms"
    [[ "$open_orders" -eq 0 ]] || fail "Found $open_orders open orders"
    exit 1
fi
