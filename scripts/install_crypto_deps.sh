#!/bin/bash
# Quick dependency installer for crypto paper trading

set -euo pipefail

echo "📦 Installing dependencies for crypto paper trading..."

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  No venv found. Creating .venv..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Upgrade pip
pip install -q --upgrade pip

# Core dependencies
echo "Installing core dependencies..."
pip install -q \
    uvicorn \
    fastapi \
    structlog \
    httpx \
    websockets \
    pyyaml \
    pandas \
    numpy \
    psycopg2-binary \
    redis \
    prometheus-client \
    pydantic \
    pydantic-settings \
    python-dotenv \
    sqlalchemy \
    alembic \
    kiteconnect

echo "✅ Dependencies installed!"
echo ""
echo "Next steps:"
echo "  1. Set your Binance keys:"
echo "     export BINANCE_API_KEY='your_key'"
echo "     export BINANCE_API_SECRET='your_secret'"
echo ""
echo "  2. Copy config:"
echo "     cp configs/crypto_paper.yaml configs/app.yaml"
echo ""
echo "  3. Start API:"
echo "     export APP_MODE=CRYPTO_PAPER APP_TIMEZONE=UTC PYTHONPATH=."
echo "     source .venv/bin/activate"
echo "     make crypto-paper &"

