#!/bin/bash
# Quick CORS sanity check (both success + error paths)
# Verifies CORS headers are present on all responses

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
ORIGIN="${ORIGIN:-http://localhost:3000}"

echo "🔍 CORS Verification"
echo "==================="
echo "API: $API_BASE"
echo "Origin: $ORIGIN"
echo ""

# 1. Success path (/ready or /health)
echo "1️⃣  Success Path Check"
echo "   Testing: GET $API_BASE/health"
RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API_BASE/health")
HTTP_STATUS=$(echo "$RESPONSE" | head -1 | awk '{print $2}')
CORS_HEADER=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "")

if [ -n "$CORS_HEADER" ]; then
    echo "   ✅ HTTP $HTTP_STATUS - CORS header present: $CORS_HEADER"
else
    echo "   ❌ HTTP $HTTP_STATUS - CORS header MISSING"
    exit 1
fi
echo ""

# 2. Error path (404)
echo "2️⃣  Error Path Check (404)"
echo "   Testing: GET $API_BASE/does-not-exist"
RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API_BASE/does-not-exist")
HTTP_STATUS=$(echo "$RESPONSE" | head -1 | awk '{print $2}')
CORS_HEADER=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "")

if [ -n "$CORS_HEADER" ]; then
    echo "   ✅ HTTP $HTTP_STATUS - CORS header present: $CORS_HEADER"
else
    echo "   ❌ HTTP $HTTP_STATUS - CORS header MISSING"
    exit 1
fi
echo ""

# 3. /ready endpoint (may be 503 if trader not started)
echo "3️⃣  /ready Endpoint Check"
echo "   Testing: GET $API_BASE/ready"
RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API_BASE/ready")
HTTP_STATUS=$(echo "$RESPONSE" | head -1 | awk '{print $2}')
CORS_HEADER=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "")
CONTENT_TYPE=$(echo "$RESPONSE" | grep -i "content-type" || echo "")

if [ -n "$CORS_HEADER" ]; then
    echo "   ✅ HTTP $HTTP_STATUS - CORS header present: $CORS_HEADER"
    if echo "$CONTENT_TYPE" | grep -q "application/json"; then
        echo "   ✅ Content-Type: application/json"
    fi
else
    echo "   ❌ HTTP $HTTP_STATUS - CORS header MISSING"
    exit 1
fi
echo ""

echo "✅ CORS verification complete!"
echo ""
echo "All endpoints return CORS headers correctly."



