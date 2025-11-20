#!/bin/bash
# Express Login & Deployment Workflow
# ===================================
# Automated daily authentication and strategy rollout for AITRAPP
#
# Usage:
#   ./go_live.sh              # Full workflow with authentication
#   ./go_live.sh --skip-login # Skip authentication (use existing token)
#
# This script:
# 1. Runs express login to refresh Kite token (unless --skip-login)
# 2. Sets production environment variables
# 3. Launches the trading engine

set -e  # Exit on any error

# Parse arguments
SKIP_LOGIN=false
if [[ "$1" == "--skip-login" ]]; then
    SKIP_LOGIN=true
fi

# Colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and repo root
# go_live.sh is in the repo root, so REPO_ROOT = SCRIPT_DIR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

# Change to repo root
cd "$REPO_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   AITRAPP - EXPRESS LOGIN & DEPLOY    ${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if .env file exists
if [ ! -f "$REPO_ROOT/.env" ]; then
    echo -e "\n${RED}❌ Error: .env file not found at $REPO_ROOT/.env${NC}"
    echo -e "${YELLOW}Please create .env file with:${NC}"
    echo -e "  KITE_API_KEY=your_api_key"
    echo -e "  KITE_API_SECRET=your_api_secret"
    exit 1
fi

# Load .env file to make variables available
if [ -f "$REPO_ROOT/.env" ]; then
    set -a  # Automatically export all variables
    source "$REPO_ROOT/.env"
    set +a
fi

# Step 1: Check if authentication is needed
echo -e "\n${GREEN}[1/2] Checking Authentication...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if token exists and is recent (within last 20 hours)
TOKEN_EXISTS=false
if [ -n "$KITE_ACCESS_TOKEN" ]; then
    TOKEN_EXISTS=true
    echo -e "${GREEN}✅ KITE_ACCESS_TOKEN found in environment${NC}"
fi

# Check token refresh timestamp
TOKEN_FRESH=false
if [ -f "$REPO_ROOT/.env" ]; then
    REFRESHED_AT=$(grep "KITE_TOKEN_REFRESHED_AT" "$REPO_ROOT/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    if [ -n "$REFRESHED_AT" ]; then
        # Check if token was refreshed in last 20 hours (tokens expire in 24h)
        REFRESH_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${REFRESHED_AT%.*}" "+%s" 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        AGE_HOURS=$(( (NOW_EPOCH - REFRESH_EPOCH) / 3600 ))
        
        if [ "$AGE_HOURS" -lt 20 ] && [ "$REFRESH_EPOCH" -gt 0 ]; then
            TOKEN_FRESH=true
            echo -e "${GREEN}✅ Token refreshed ${AGE_HOURS} hours ago (still valid)${NC}"
        else
            echo -e "${YELLOW}⚠️  Token is ${AGE_HOURS} hours old (may need refresh)${NC}"
        fi
    fi
fi

# Only run login if token is missing or stale, or if --skip-login not set
if [ "$SKIP_LOGIN" = true ]; then
    echo -e "${GREEN}✅ Authentication skipped (--skip-login flag)${NC}"
    # Ensure token is loaded from .env
    if [ -z "$KITE_ACCESS_TOKEN" ]; then
        set -a
        source "$REPO_ROOT/.env"
        set +a
    fi
elif [ "$TOKEN_FRESH" = false ] || [ "$TOKEN_EXISTS" = false ]; then
    echo -e "${YELLOW}🔄 Running authentication...${NC}"
    if ! python3 "$REPO_ROOT/scripts/express_login.py"; then
        echo -e "\n${RED}❌ Authentication failed!${NC}"
        echo -e "${YELLOW}Login script exited with error. Aborting deployment.${NC}"
        exit 1
    fi
    # Reload .env after login
    set -a
    source "$REPO_ROOT/.env"
    set +a
else
    echo -e "${GREEN}✅ Authentication skipped - token is fresh${NC}"
fi

# Verify that token was updated
if [ -z "$KITE_ACCESS_TOKEN" ]; then
    # Reload .env to get updated token
    set -a
    source "$REPO_ROOT/.env"
    set +a
fi

if [ -z "$KITE_ACCESS_TOKEN" ]; then
    echo -e "\n${RED}❌ Error: KITE_ACCESS_TOKEN not found after login${NC}"
    echo -e "${YELLOW}Please check .env file and try again.${NC}"
    exit 1
fi

# Step 2: Set Production Environment Variables
echo -e "\n${GREEN}[2/2] Setting Production Environment...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

export APP_MODE=LIVE
export APP_CONFIG=configs/kite_day1_live.yaml
export MAX_TOKENS_PER_SCAN=80

echo -e "${GREEN}✅ Environment Variables Set:${NC}"
echo -e "   APP_MODE=${APP_MODE}"
echo -e "   APP_CONFIG=${APP_CONFIG}"
echo -e "   MAX_TOKENS_PER_SCAN=${MAX_TOKENS_PER_SCAN}"

# Step 3: Launch Application
echo -e "\n${GREEN}[3/3] Launching Trading Engine...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Starting uvicorn on 0.0.0.0:8000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"

# Launch uvicorn
python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

