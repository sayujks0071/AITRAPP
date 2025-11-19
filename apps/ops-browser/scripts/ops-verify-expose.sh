#!/usr/bin/env bash

set -Eeuo pipefail

API="${API:-http://localhost:8000}"
ORIGIN="${ORIGIN:-http://localhost:3000}"
ENDPOINT="${ENDPOINT:-/ready}"          # Which endpoint to probe for expose list
STRICT="${STRICT:-true}"                # true => fail if missing exposes
TEST_ERROR_ENDPOINT="${TEST_ERROR_ENDPOINT:-}"  # Optional: an endpoint likely to return 4xx/5xx

EXPECTED=("x-retry-after" "x-rate-limit-remaining" "x-time-skew-ms")

hdrs() { curl -s -i -H "Origin: $ORIGIN" "$1" | tr -d '\r'; }

resp="$(hdrs "$API$ENDPOINT")"
status="$(sed -n '1 s/.* \([0-9][0-9][0-9]\).*/\1/p' <<<"$resp" || true)"
expose="$(grep -i '^Access-Control-Expose-Headers:' <<<"$resp" | cut -d: -f2- \
  | tr '[:upper:]' '[:lower:]' | tr -d ' ' || true)"

echo "API:      $API"
echo "Origin:   $ORIGIN"
echo "Endpoint: $ENDPOINT"
echo "HTTP:     ${status:-unknown}"
echo "Expose:   ${expose:-<none>}"
echo

if [[ -z "${expose:-}" ]]; then
  echo "❌ No Access-Control-Expose-Headers present."
  [[ "$STRICT" == "true" ]] && exit 1 || echo "⚠️  non-strict mode: continuing"
else
  ok=true
  for h in "${EXPECTED[@]}"; do
    if [[ ",$expose," != *",$h,"* ]]; then
      echo "❌ Missing '$h' in Access-Control-Expose-Headers"
      ok=false
    else
      echo "✅ '$h' exposed"
    fi
  done
  [[ "$ok" == "false" && "$STRICT" == "true" ]] && { echo "❌ Required headers not exposed."; exit 1; }
fi

if [[ -n "$TEST_ERROR_ENDPOINT" ]]; then
  echo
  echo "→ Probing error endpoint: $TEST_ERROR_ENDPOINT"
  err="$(hdrs "$API$TEST_ERROR_ENDPOINT")"
  retry_after="$(grep -i '^Retry-After:' <<<"$err" | awk -F': *' '{print $2}' || true)"
  if [[ -n "$retry_after" ]]; then
    echo "ℹ️  Retry-After present on $TEST_ERROR_ENDPOINT: $retry_after"
  else
    echo "ℹ️  No Retry-After header observed on $TEST_ERROR_ENDPOINT"
  fi
fi

echo
echo "✅ Expose-header CORS check complete."






