#!/bin/bash
# Production smoke test for API behind reverse proxy

set -e

API="${API:-https://ops-api.yourdomain.com}"
ORIGIN="${ORIGIN:-https://ops-ui.yourdomain.com}"

echo "🧪 Production Smoke Test (API behind proxy)"
echo "API: $API"
echo "Origin: $ORIGIN"
echo "=========================================="
echo ""

# 1) Ready OK
echo "1️⃣  Testing /ready endpoint"
READY_RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API/ready" 2>&1)
echo "$READY_RESPONSE" | sed -n '1p;/^Access-Control/p;/^Cache-Control/p;/^Vary/p'
if echo "$READY_RESPONSE" | grep -q "Access-Control-Allow-Origin: $ORIGIN"; then
    echo "   ✅ CORS headers present"
else
    echo "   ❌ CORS headers missing or incorrect"
    exit 1
fi
if echo "$READY_RESPONSE" | grep -q "Cache-Control: no-store"; then
    echo "   ✅ Cache control present"
else
    echo "   ⚠️  Cache control missing"
fi
if echo "$READY_RESPONSE" | grep -q "Vary: Origin"; then
    echo "   ✅ Vary header present"
else
    echo "   ⚠️  Vary header missing"
fi
echo ""

# 2) Preflight for POST /flatten
echo "2️⃣  Testing OPTIONS preflight for POST /flatten"
PREFLIGHT_RESPONSE=$(curl -s -i -X OPTIONS "$API/flatten" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization" \
  2>&1)
echo "$PREFLIGHT_RESPONSE" | sed -n '1p;/^Access-Control/p;/^Vary/p'
if echo "$PREFLIGHT_RESPONSE" | grep -qE "HTTP/1.1 (204|200)"; then
    echo "   ✅ Preflight status OK"
else
    echo "   ❌ Preflight status incorrect"
    exit 1
fi
if echo "$PREFLIGHT_RESPONSE" | grep -q "Access-Control-Allow-Origin: $ORIGIN"; then
    echo "   ✅ Preflight CORS headers present"
else
    echo "   ❌ Preflight CORS headers missing"
    exit 1
fi
if echo "$PREFLIGHT_RESPONSE" | grep -q "Access-Control-Max-Age: 600"; then
    echo "   ✅ Preflight max-age present"
else
    echo "   ⚠️  Preflight max-age missing"
fi
echo ""

# 3) Metrics headers
echo "3️⃣  Testing /metrics endpoint"
METRICS_RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API/metrics" 2>&1)
echo "$METRICS_RESPONSE" | sed -n '1p;/^Content-Type/p;/^Cache-Control/p'
if echo "$METRICS_RESPONSE" | grep -q "Content-Type: text/plain"; then
    echo "   ✅ Content-Type correct for Prometheus"
else
    echo "   ⚠️  Content-Type may be incorrect"
fi
if echo "$METRICS_RESPONSE" | grep -q "Cache-Control: no-store"; then
    echo "   ✅ Cache control present"
else
    echo "   ⚠️  Cache control missing"
fi
echo ""

# 4) Expose headers check
echo "4️⃣  Testing expose headers"
EXPOSE_RESPONSE=$(curl -s -i -H "Origin: $ORIGIN" "$API/ready" 2>&1)
if echo "$EXPOSE_RESPONSE" | grep -q "Access-Control-Expose-Headers"; then
    EXPOSED=$(echo "$EXPOSE_RESPONSE" | grep -i "Access-Control-Expose-Headers" | cut -d: -f2 | tr -d ' ')
    echo "   ✅ Expose headers present: $EXPOSED"
else
    echo "   ⚠️  Expose headers missing"
fi
echo ""

echo "✅ Production smoke test complete!"
echo ""
echo "Next steps:"
echo "  - Verify reverse proxy preserves CORS headers"
echo "  - Check that proxy doesn't override Cache-Control"
echo "  - Ensure Vary: Origin is passed through"



