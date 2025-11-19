#!/bin/bash
# 60-sec token script smoke test
# Verifies script loads, CLI works, and export formatting without contacting Kite

set -e

echo "🧪 Kite Token Refresh - Smoke Test"
echo "=================================="
echo ""

# 1) Check script loads
echo "1️⃣  Checking script loads..."
python3 scripts/kite_token_refresh.py --help > /dev/null 2>&1
echo "   ✅ Script loads and CLI works"
echo ""

# 2) Test export formatting (no secrets)
echo "2️⃣  Testing export formatting (dry run, no secrets)..."
EXPORT_OUTPUT=$(python3 -c "from scripts.kite_token_refresh import _emit_exports; print(_emit_exports('FAKE_ACCESS', 'AB1234'))")
echo "$EXPORT_OUTPUT"
echo ""

# 3) Verify .env is in .gitignore
echo "3️⃣  Checking .env is in .gitignore..."
if git check-ignore -v .env > /dev/null 2>&1; then
    echo "   ✅ .env is properly ignored by git"
else
    echo "   ⚠️  .env is NOT in .gitignore - add it for security"
fi
echo ""

# 4) Check kiteconnect is installed
echo "4️⃣  Checking dependencies..."
if python3 -c "import kiteconnect" 2>/dev/null; then
    echo "   ✅ kiteconnect is installed"
else
    echo "   ❌ kiteconnect not installed - run: pip install kiteconnect"
    exit 1
fi
echo ""

echo "✅ Smoke test complete - script is ready for use!"
echo ""
echo "Next steps:"
echo "  1. Set KITE_API_KEY and KITE_API_SECRET"
echo "  2. Run: make kite-token-refresh"
echo "  3. After getting token, verify with: make kite-token-check"






