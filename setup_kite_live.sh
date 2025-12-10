#!/bin/bash
# Setup script for Kite login and live trading

set -e

cd "$(dirname "$0")"

echo "🚀 Kite Live Trading Setup"
echo "=========================="
echo ""

# Step 1: Check for credentials
echo "📋 Step 1: Checking for Kite API credentials..."
if [ -z "$KITE_API_KEY" ] || [ -z "$KITE_API_SECRET" ]; then
    echo "❌ KITE_API_KEY and/or KITE_API_SECRET not set"
    echo ""
    echo "Please set them using one of these methods:"
    echo ""
    echo "Option A: Export in current session"
    echo "  export KITE_API_KEY='your_api_key'"
    echo "  export KITE_API_SECRET='your_api_secret'"
    echo ""
    echo "Option B: Create/update .env file"
    echo "  Create a .env file with:"
    echo "  KITE_API_KEY=your_api_key"
    echo "  KITE_API_SECRET=your_api_secret"
    echo ""
    echo "Then source it: source .env"
    echo ""
    read -p "Press Enter after you've set the credentials, or Ctrl+C to cancel..."
fi

# Step 2: Refresh token
echo ""
echo "📋 Step 2: Refreshing Kite access token..."
echo "This will open a browser for you to login..."
make kite-token-refresh

# Step 3: Get the exported token
echo ""
echo "📋 Step 3: Please copy the export commands shown above"
echo "They should look like:"
echo "  export KITE_ACCESS_TOKEN=\"...\""
echo "  export KITE_USER_ID=\"...\""
echo ""
read -p "Press Enter after you've copied and pasted the export commands in this terminal..."

# Step 4: Set LIVE mode
echo ""
echo "📋 Step 4: Setting up LIVE mode environment..."
export APP_MODE=LIVE
export APP_TIMEZONE=Asia/Kolkata

# Get egress IP if needed
if [ -z "$EXPECTED_EGRESS_IP" ]; then
    echo "Getting your egress IP..."
    EXPECTED_EGRESS_IP=$(curl -fsS https://api.ipify.org 2>/dev/null || echo "")
    if [ -n "$EXPECTED_EGRESS_IP" ]; then
        export EXPECTED_EGRESS_IP="$EXPECTED_EGRESS_IP"
        echo "✅ Egress IP: $EXPECTED_EGRESS_IP"
    else
        echo "⚠️  Could not detect egress IP. Set EXPECTED_EGRESS_IP manually if needed."
    fi
fi

# Step 5: Check if API server is running
echo ""
echo "📋 Step 5: Checking if API server is running..."
if curl -fsS http://localhost:8000/ready >/dev/null 2>&1; then
    echo "✅ API server is already running"
else
    echo "❌ API server is not running"
    echo ""
    echo "Starting API server in LIVE mode..."
    echo "⚠️  This will run in the background. Use 'make kite-canary-stop' to stop it."
    echo ""
    # Start API server in background
    export APP_MODE=LIVE
    nohup python -m apps.api.main > /tmp/kite_api.log 2>&1 &
    API_PID=$!
    echo "API server started with PID: $API_PID"
    echo "Waiting for server to be ready..."
    
    # Wait up to 30 seconds for server to start
    for i in {1..30}; do
        if curl -fsS http://localhost:8000/ready >/dev/null 2>&1; then
            echo "✅ API server is ready!"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    if ! curl -fsS http://localhost:8000/ready >/dev/null 2>&1; then
        echo "❌ API server failed to start. Check /tmp/kite_api.log for errors."
        exit 1
    fi
fi

# Step 6: Run prelive gate
echo ""
echo "📋 Step 6: Running pre-flight gate checks..."
if make prelive-gate; then
    echo "✅ Pre-flight gate passed!"
else
    echo "❌ Pre-flight gate failed. Please fix the issues before proceeding."
    exit 1
fi

# Step 7: Launch canary
echo ""
echo "📋 Step 7: Launching Kite canary..."
echo "⚠️  This will start live trading monitoring."
echo "Press Ctrl+C to stop monitoring (use 'make kite-canary-stop' to fully stop)"
echo ""
read -p "Press Enter to launch, or Ctrl+C to cancel..."

make kite-canary-launch


