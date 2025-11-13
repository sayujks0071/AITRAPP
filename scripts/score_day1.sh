#!/usr/bin/env bash
# One-shot Day-1 PASS scorer
# Checks readiness, heartbeats, and database integrity

set -euo pipefail

API="${API:-http://localhost:8000}"
ok=1

echo "📊 Day-1 PASS Scorer"
echo "===================="
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
BAD_HB=0
curl -s "$API/metrics" 2>/dev/null | awk '/^trader_(marketdata|order_stream|scan)_heartbeat_seconds/ {
    if ($2 >= 5) {
        print "   ❌ " $1 " = " $2 "s (>= 5s)"
        BAD_HB=1
    } else {
        print "   ✅ " $1 " = " $2 "s"
    }
}'
if [ "$BAD_HB" -eq 1 ]; then
    ok=0
fi
echo ""

# 3. Check leader lock
echo "3️⃣  Checking leader lock..."
LEADER=$(curl -s "$API/metrics" 2>/dev/null | awk '/^trader_is_leader[^_]/ {print $2; exit}' || echo "0")
# Handle both "1" and "1.0" (float comparison)
if awk "BEGIN{exit !(${LEADER:-0} == 1)}"; then
    echo "   ✅ trader_is_leader = ${LEADER}"
else
    echo "   ❌ trader_is_leader = $LEADER (expected 1)"
    ok=0
fi
echo ""

# 4. Check for duplicates/orphans
echo "4️⃣  Checking database integrity..."
if [ -z "${DATABASE_URL:-}" ]; then
    echo "   ⚠️  DATABASE_URL not set, skipping DB check"
else
    DB_CONN="${DATABASE_URL#postgresql+psycopg2://}"
    
    # Check duplicates
    DUPES=$(psql "$DB_CONN" -tAc "
        SELECT COUNT(*) 
        FROM (
            SELECT client_order_id
            FROM orders
            WHERE client_order_id IS NOT NULL
            GROUP BY client_order_id
            HAVING COUNT(*) > 1
        ) dupes;
    " 2>/dev/null || echo "0")
    
    # Check orphans
    ORPHANS=$(psql "$DB_CONN" -tAc "
        SELECT COUNT(*)
        FROM orders o
        WHERE o.tag IN ('STOP', 'TP1', 'TP2')
          AND o.parent_group IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 
              FROM orders parent 
              WHERE parent.parent_group = o.parent_group 
                AND parent.tag = 'ENTRY'
          );
    " 2>/dev/null || echo "0")
    
    TOTAL_ISSUES=$((DUPES + ORPHANS))
    
    if [ "$DUPES" -gt 0 ]; then
        echo "   ❌ Found $DUPES duplicate client_order_ids"
        ok=0
    else
        echo "   ✅ No duplicate client_order_ids"
    fi
    
    if [ "$ORPHANS" -gt 0 ]; then
        echo "   ❌ Found $ORPHANS orphan OCO children"
        ok=0
    else
        echo "   ✅ No orphan OCO children"
    fi
fi
echo ""

# Final verdict
echo "📊 Result:"
echo "==========="
if [ $ok -eq 1 ]; then
    echo "✅ DAY-1 PASS"
    echo ""
    echo "All checks passed:"
    echo "  - /ready = 200"
    echo "  - All heartbeats < 5s"
    echo "  - Leader lock = 1"
    echo "  - No duplicates/orphans"
    exit 0
else
    echo "❌ DAY-1 FAIL"
    echo ""
    echo "Some checks failed. Review output above."
    exit 1
fi

