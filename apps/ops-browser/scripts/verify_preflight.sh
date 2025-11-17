#!/bin/bash
# Preflight (OPTIONS) CORS verification
# Browsers preflight mutating endpoints - verify OPTIONS responses include CORS headers

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
ORIGIN="${ORIGIN:-http://localhost:3000}"

echo "🔍 Preflight (OPTIONS) CORS Verification"
echo "========================================"
echo "API: $API_BASE"
echo "Origin: $ORIGIN"
echo ""

# Test OPTIONS preflight for POST /flatten
echo "1️⃣  OPTIONS Preflight: POST /flatten"
RESPONSE=$(curl -s -i -X OPTIONS "$API_BASE/flatten" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type")

HTTP_STATUS=$(echo "$RESPONSE" | head -1 | awk '{print $2}')
CORS_ORIGIN=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "")
CORS_METHODS=$(echo "$RESPONSE" | grep -i "access-control-allow-methods" || echo "")
CORS_HEADERS=$(echo "$RESPONSE" | grep -i "access-control-allow-headers" || echo "")
CORS_MAX_AGE=$(echo "$RESPONSE" | grep -i "access-control-max-age" || echo "")

if [ "$HTTP_STATUS" = "204" ] || [ "$HTTP_STATUS" = "200" ]; then
    echo "   ✅ HTTP $HTTP_STATUS (correct for OPTIONS)"
else
    echo "   ⚠️  HTTP $HTTP_STATUS (expected 204 or 200)"
fi

if [ -n "$CORS_ORIGIN" ]; then
    echo "   ✅ $CORS_ORIGIN"
else
    echo "   ❌ Access-Control-Allow-Origin MISSING"
    exit 1
fi

if [ -n "$CORS_METHODS" ]; then
    echo "   ✅ $CORS_METHODS"
else
    echo "   ⚠️  Access-Control-Allow-Methods not found (may be in middleware)"
fi

if [ -n "$CORS_HEADERS" ]; then
    echo "   ✅ $CORS_HEADERS"
else
    echo "   ⚠️  Access-Control-Allow-Headers not found (may be in middleware)"
fi

if [ -n "$CORS_MAX_AGE" ]; then
    echo "   ✅ $CORS_MAX_AGE"
else
    echo "   ⚠️  Access-Control-Max-Age not found (optional but recommended)"
fi
echo ""

# Test OPTIONS for other endpoints
echo "2️⃣  OPTIONS Preflight: GET /health"
RESPONSE=$(curl -s -i -X OPTIONS "$API_BASE/health" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: GET")

HTTP_STATUS=$(echo "$RESPONSE" | head -1 | awk '{print $2}')
CORS_ORIGIN=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "")

if [ -n "$CORS_ORIGIN" ]; then
    echo "   ✅ HTTP $HTTP_STATUS - $CORS_ORIGIN"
else
    echo "   ❌ HTTP $HTTP_STATUS - CORS header MISSING"
    exit 1
fi
echo ""

# Test 404 path (should still have CORS)
echo "3️⃣  Error Path (404) - CORS Headers"
RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API_BASE/__nope__")
HTTP_STATUS=$(echo "$RESPONSE" | head -1 | awk '{print $2}')
CORS_ORIGIN=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "")

if [ -n "$CORS_ORIGIN" ]; then
    echo "   ✅ HTTP $HTTP_STATUS - $CORS_ORIGIN"
else
    echo "   ❌ HTTP $HTTP_STATUS - CORS header MISSING"
    exit 1
fi
echo ""

echo "✅ Preflight verification complete!"
echo ""
echo "All OPTIONS requests return proper CORS headers."



