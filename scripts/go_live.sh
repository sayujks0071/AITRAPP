#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}"
echo "=================================================="
echo "          🚨 GOING LIVE: REAL MONEY MODE 🚨"
echo "=================================================="
echo -e "${NC}"

# 1. Check for .env file
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please run: python3 scripts/kite_auth_bootstrap.py"
    exit 1
fi

# 2. Check for Token Freshness (Simple Timestamp Check if available, or just existence)
# We rely on the python script to actually validate connection, but we can warn here.
# Let's try to verify connection using a quick python snippet
echo "Checking connectivity..."
if ! python3 scripts/kite_auth_bootstrap.py --check; then
    echo -e "${RED}❌ Authentication failed or token expired.${NC}"
    echo -e "${YELLOW}Please run: python3 scripts/kite_auth_bootstrap.py${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Connection verified.${NC}"

# 3. Safety Confirmation
echo ""
echo -e "${RED}WARNING: This will execute REAL TRADES on your Zerodha account.${NC}"
echo "Strategies enabled: ORB (default)"
echo "Symbol: NIFTY (default)"
echo ""
read -p "Type 'LIVE' to confirm and start: " confirmation

if [ "$confirmation" != "LIVE" ]; then
    echo "❌ Confirmation failed. Aborting."
    exit 1
fi

# 4. Set Environment Variables
export TRADING_MODE=live
export I_UNDERSTAND_LIVE_TRADING=true
export APP_MODE=LIVE

# 5. Run the Runner
echo ""
echo -e "${GREEN}🚀 Starting Live Execution Engine...${NC}"
echo "Press Ctrl+C to stop."
echo ""

# We use 'python3 -m packages.core.runner' assuming PYTHONPATH includes current dir
export PYTHONPATH=$PYTHONPATH:.

python3 -m packages.core.runner live --strategy ORB --symbol NIFTY
