#!/bin/bash
# Verify Access-Control-Expose-Headers on API endpoints

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
UI_ORIGIN="${UI_ORIGIN:-http://localhost:3000}"

echo "🧪 Verifying Access-Control-Expose-Headers for API: $API_BASE from UI Origin: $UI_ORIGIN"
echo "=================================================================================="
echo ""

# Expected exposed headers
EXPECTED_EXPOSE="X-Retry-After, X-Rate-Limit-Remaining, X-Time-Skew-Ms"

# Test /ready endpoint
echo "1️⃣  Testing /ready endpoint for expose headers"
READY_HEADERS=$(curl -s -i -H "Origin: $UI_ORIGIN" "$API_BASE/ready" | grep -E 'HTTP/|Access-Control-Expose-Headers|Access-Control-Allow-Origin')
echo "$READY_HEADERS"
if echo "$READY_HEADERS" | grep -q "Access-Control-Expose-Headers"; then
    EXPOSED=$(echo "$READY_HEADERS" | grep -i "Access-Control-Expose-Headers" | cut -d: -f2 | tr -d ' ')
    echo "   ✅ Expose headers present: $EXPOSED"
    # Check if expected headers are present
    if echo "$EXPOSED" | grep -q "X-Retry-After" && \
       echo "$EXPOSED" | grep -q "X-Rate-Limit-Remaining" && \
       echo "$EXPOSED" | grep -q "X-Time-Skew-Ms"; then
        echo "   ✅ All expected headers exposed"
    else
        echo "   ⚠️  Some expected headers missing (expected: $EXPECTED_EXPOSE)"
    fi
else
    echo "   ❌ Access-Control-Expose-Headers MISSING"
    exit 1
fi
echo ""

# Test /positions endpoint
echo "2️⃣  Testing /positions endpoint for expose headers"
POSITIONS_HEADERS=$(curl -s -i -H "Origin: $UI_ORIGIN" "$API_BASE/positions" | grep -E 'HTTP/|Access-Control-Expose-Headers|Access-Control-Allow-Origin')
echo "$POSITIONS_HEADERS"
if echo "$POSITIONS_HEADERS" | grep -q "Access-Control-Expose-Headers"; then
    echo "   ✅ Expose headers present on /positions"
else
    echo "   ⚠️  Expose headers missing on /positions (CORS middleware should add them)"
fi
echo ""

# Test /orders endpoint
echo "3️⃣  Testing /orders endpoint for expose headers"
ORDERS_HEADERS=$(curl -s -i -H "Origin: $UI_ORIGIN" "$API_BASE/orders" | grep -E 'HTTP/|Access-Control-Expose-Headers|Access-Control-Allow-Origin')
echo "$ORDERS_HEADERS"
if echo "$ORDERS_HEADERS" | grep -q "Access-Control-Expose-Headers"; then
    echo "   ✅ Expose headers present on /orders"
else
    echo "   ⚠️  Expose headers missing on /orders (CORS middleware should add them)"
fi
echo ""

echo "✅ Expose headers verification complete!"
echo ""
echo "Note: CORS middleware should automatically add expose headers to all responses."
echo "If missing, check that expose_headers is set in CORSMiddleware configuration."











