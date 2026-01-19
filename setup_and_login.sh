#!/bin/bash
# Quick setup and login script for AITRAPP

set -e

cd "$(dirname "$0")"

echo "🚀 AITRAPP Setup & Login"
echo "========================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    eval "$(/opt/homebrew/bin/brew shellenv)"
    /opt/homebrew/opt/python@3.11/bin/python3.11 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Check Python version
PYTHON_VERSION=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$(printf '%s\n' "3.10" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.10" ]; then
    echo "❌ Python 3.10+ required. Found: $(python --version)"
    exit 1
fi

echo "✅ Python: $(python --version)"

# Check services
echo ""
echo "Checking services..."

if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "⚠️  PostgreSQL not running. Starting..."
    eval "$(/opt/homebrew/bin/brew shellenv)"
    brew services start postgresql@16
    sleep 2
fi
echo "✅ PostgreSQL: Running"

if ! redis-cli ping >/dev/null 2>&1; then
    echo "⚠️  Redis not running. Starting..."
    eval "$(/opt/homebrew/bin/brew shellenv)"
    brew services start redis
    sleep 1
fi
echo "✅ Redis: Running"

# Check .env file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Creating from template..."
    cp env.example .env
    echo "⚠️  Please edit .env and add your Kite credentials"
fi

# Check if access token is set
if grep -q "KITE_ACCESS_TOKEN=your_access_token_here" .env || grep -q "KITE_ACCESS_TOKEN=$" .env; then
    echo ""
    echo "⚠️  Access token not configured in .env"
    echo ""
    echo "📝 To get your access token:"
    echo "   1. Run: python scripts/kite_auth_bootstrap.py"
    echo "   2. Or visit the login URL manually"
    echo ""
    read -p "Do you want to generate access token now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python scripts/kite_auth_bootstrap.py
    else
        echo "⚠️  Please configure KITE_ACCESS_TOKEN in .env before starting the app"
        exit 1
    fi
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# Setup database
echo ""
echo "Setting up database..."
if ! psql -h localhost -U $(whoami) -d aitrapp -c "SELECT 1;" >/dev/null 2>&1; then
    echo "Creating database..."
    createdb aitrapp 2>/dev/null || echo "Database might already exist"
fi

# Run migrations
if command -v alembic >/dev/null 2>&1; then
    echo "Running migrations..."
    alembic upgrade head
    echo "✅ Database migrations complete"
else
    echo "⚠️  Alembic not found. Skipping migrations."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the app:"
echo "   source venv/bin/activate"
echo "   make paper"
echo ""
echo "Or:"
echo "   source venv/bin/activate"
echo "   export APP_MODE=PAPER"
echo "   python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""

