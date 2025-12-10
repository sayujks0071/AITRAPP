#!/bin/bash
# Helper script to set Binance API keys securely
# Usage: source scripts/set_binance_keys.sh

# Check if keys are provided as arguments
if [ $# -eq 2 ]; then
    export BINANCE_API_KEY="$1"
    export BINANCE_API_SECRET="$2"
    echo "✅ Keys set from arguments"
elif [ -f .env ]; then
    # Load from .env file if it exists
    set -a
    source .env
    set +a
    echo "✅ Keys loaded from .env file"
else
    echo "⚠️  No keys provided and .env file not found"
    echo ""
    echo "Usage options:"
    echo "  1. source scripts/set_binance_keys.sh KEY SECRET"
    echo "  2. Create .env file with:"
    echo "     BINANCE_API_KEY=your_key"
    echo "     BINANCE_API_SECRET=your_secret"
    echo "     Then: source scripts/set_binance_keys.sh"
    echo ""
    echo "  3. Export directly:"
    echo "     export BINANCE_API_KEY='your_key'"
    echo "     export BINANCE_API_SECRET='your_secret'"
    exit 1
fi

# Verify keys are set
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo "❌ Keys not properly set"
    exit 1
fi

echo "✅ Binance API keys are set and ready"
echo "   Key prefix: ${BINANCE_API_KEY:0:10}..."
echo "   Secret prefix: ${BINANCE_API_SECRET:0:10}..."


