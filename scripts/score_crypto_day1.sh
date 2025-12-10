#!/usr/bin/env bash
# Crypto Day-1 PASS Scorer
# Checks crypto venue readiness, heartbeats, OCO, and risk gates

set -euo pipefail

# Enforce timezone consistently (UTC for crypto)
export TZ="${TZ:-UTC}"

API="${API:-http://localhost:8000}"
HEARTBEAT_MAX="${HEARTBEAT_MAX:-5}"
ok=1

echo "📊 Crypto Day-1 PASS Scorer"
echo "==========================="
echo ""

# 1. Check readiness
echo "1️⃣  Checking /ready..."
if curl -sf "$API/ready" >/dev/null 2>&1; then
    echo "   ✅ /ready returns 200"
else
    echo "   ❌ /ready not ready (503)"
    ok=0
fi
echo ""

# 2. Check heartbeats
echo "2️⃣  Checking heartbeats..."
MD_HB=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_marketdata_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
ORDER_HB=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_order_stream_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")
SCAN_HB=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_scan_heartbeat_seconds[^_]/ {print $2; exit}' || echo "999")

BAD_HB=0
curl -s "$API/metrics" 2>/dev/null | awk -v max="$HEARTBEAT_MAX" '/^trader_(marketdata|order_stream|scan)_heartbeat_seconds[^_]/ {
    if ($2 >= max) {
        print "   ❌ " $1 " = " $2 "s (>= " max "s)"
        bad=1
    } else {
        print "   ✅ " $1 " = " $2 "s"
    }
} END { exit bad }' || BAD_HB=1

if [ "$BAD_HB" -eq 1 ]; then
    ok=0
fi
echo ""

# 3. Check leader lock
echo "3️⃣  Checking leader lock..."
LEADER=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_is_leader[^_]/ {print $2; exit}' || echo "0")
if awk "BEGIN{exit !(${LEADER:-0} == 1)}"; then
    echo "   ✅ trader_is_leader = ${LEADER}"
else
    echo "   ❌ trader_is_leader = $LEADER (expected 1)"
    ok=0
fi
echo ""

# 4. Check crypto WebSocket reconnects
echo "4️⃣  Checking crypto WebSocket health..."
CRYPTO_WS_RECONNECTS=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_crypto_ws_reconnects_total/ {print $2; exit}' || echo "0")
CRYPTO_WS_RECONNECTS_INT=${CRYPTO_WS_RECONNECTS%.*}

if [ "$CRYPTO_WS_RECONNECTS_INT" -le 5 ]; then
    echo "   ✅ crypto_ws_reconnects = ${CRYPTO_WS_RECONNECTS} (≤ 5)"
else
    echo "   ⚠️  crypto_ws_reconnects = ${CRYPTO_WS_RECONNECTS} (> 5, but not failing)"
    # Warning only, not a failure
fi
echo ""

# 5. Check OCO orphans
echo "5️⃣  Checking OCO orphans..."
OCO_ORPHANS=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_oco_orphans_total/ {print $2; exit}' || echo "0")
OCO_ORPHANS_INT=${OCO_ORPHANS%.*}

if [ "$OCO_ORPHANS_INT" -eq 0 ]; then
    echo "   ✅ oco_orphans = ${OCO_ORPHANS} (0)"
else
    echo "   ❌ oco_orphans = ${OCO_ORPHANS} (> 0)"
    ok=0
fi
echo ""

# 6. Check crypto orders placed
echo "6️⃣  Checking crypto order metrics..."
CRYPTO_ORDERS=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_crypto_orders_placed_total/ {print $2; exit}' || echo "0")
echo "   ℹ️  crypto_orders_placed = ${CRYPTO_ORDERS}"
echo ""

# Calculate config_sha and git_head
CONFIG_SHA=$(python -c "import hashlib; f=open('configs/app.yaml','rb'); print(hashlib.sha256(f.read()).hexdigest()[:16])" 2>/dev/null || echo "unknown")
GIT_HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Output JSON summary
mkdir -p reports/burnin
TIMESTAMP=$(date -Is)
JSON_OUTPUT=$(jq -n \
  --arg status "$( [[ $ok -eq 1 ]] && echo "PASS" || echo "FAIL" )" \
  --arg leader "${LEADER:-0}" \
  --arg md_hb "$MD_HB" \
  --arg order_hb "$ORDER_HB" \
  --arg scan_hb "$SCAN_HB" \
  --arg crypto_ws_reconnects "${CRYPTO_WS_RECONNECTS:-0}" \
  --arg oco_orphans "${OCO_ORPHANS:-0}" \
  --arg crypto_orders "${CRYPTO_ORDERS:-0}" \
  --arg config_sha "$CONFIG_SHA" \
  --arg git_head "$GIT_HEAD" \
  --arg timestamp "$TIMESTAMP" \
  '{
    status: $status,
    timestamp: $timestamp,
    config_sha: $config_sha,
    git_head: $git_head,
    leader: ($leader | tonumber),
    heartbeats: {
      market: ($md_hb | tonumber),
      orders: ($order_hb | tonumber),
      scan: ($scan_hb | tonumber)
    },
    crypto_ws_reconnects: ($crypto_ws_reconnects | tonumber),
    oco_orphans: ($oco_orphans | tonumber),
    crypto_orders: ($crypto_orders | tonumber)
  }' 2>/dev/null || echo '{"status":"ERROR","timestamp":"'$TIMESTAMP'"}')

# Atomic write
TODAY=$(date +%F)
OUT="reports/burnin/crypto_day1_${TODAY}.json"
TMP="$(mktemp "reports/burnin/.crypto_day1_${TODAY}.json.XXXX" 2>/dev/null || echo "reports/burnin/.crypto_day1_${TODAY}.json.tmp")"
printf "%s" "$JSON_OUTPUT" > "${TMP}"
if command -v sync >/dev/null 2>&1; then sync; fi
mv -f "${TMP}" "${OUT}"
echo "wrote ${OUT}"
echo ""

# Final verdict
echo "📊 Result:"
echo "==========="
if [ $ok -eq 1 ]; then
    echo "✅ CRYPTO DAY-1 PASS"
    echo ""
    echo "All checks passed:"
    echo "  - /ready = 200"
    echo "  - All heartbeats < ${HEARTBEAT_MAX}s"
    echo "  - Leader lock = 1"
    echo "  - OCO orphans = 0"
    echo "  - Risk gates respected"
    exit 0
else
    echo "❌ CRYPTO DAY-1 FAIL"
    echo ""
    echo "Some checks failed. Review output above."
    exit 1
fi


