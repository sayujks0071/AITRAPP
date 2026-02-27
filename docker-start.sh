#!/bin/bash

# AITRAPP Docker Quick Start Script
# This script helps you start the AITRAPP trading system using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "======================================================================"
echo "    🚀 AITRAPP - Trading System Docker Launcher"
echo "======================================================================"
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

# Use either 'docker compose' or 'docker-compose'
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}✅ Docker is installed and running${NC}"
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Creating .env from env.example..."

    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${GREEN}✅ .env file created${NC}"
        echo
        echo -e "${YELLOW}📝 Please edit .env and add your Kite API credentials:${NC}"
        echo "   KITE_API_KEY=your_api_key_here"
        echo "   KITE_API_SECRET=your_api_secret_here"
        echo
        read -p "Press Enter after you've updated .env, or Ctrl+C to exit..."
    else
        echo -e "${RED}❌ env.example not found! Cannot create .env${NC}"
        exit 1
    fi
fi

# Check if Kite credentials are set
if grep -q "your_api_key_here" .env || grep -q "your_api_secret_here" .env; then
    echo -e "${YELLOW}⚠️  Kite API credentials not set in .env${NC}"
    echo "Please update .env with your actual credentials from https://kite.trade/"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}Starting AITRAPP services...${NC}"
echo

# Start services
echo "🔧 Starting PostgreSQL and Redis..."
$DOCKER_COMPOSE -f docker-compose.trading.yml up -d postgres redis

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
if $DOCKER_COMPOSE -f docker-compose.trading.yml ps | grep -q "unhealthy"; then
    echo -e "${RED}❌ Some services are unhealthy!${NC}"
    $DOCKER_COMPOSE -f docker-compose.trading.yml ps
    echo
    echo "Check logs with: $DOCKER_COMPOSE -f docker-compose.trading.yml logs"
    exit 1
fi

echo -e "${GREEN}✅ Database and cache are ready${NC}"
echo

# Check if logged in to Kite
LOGGED_IN=false
if [ -f .env ]; then
    if grep -q "KITE_ACCESS_TOKEN=" .env && ! grep -q "KITE_ACCESS_TOKEN=your_access_token_here" .env; then
        LOGGED_IN=true
    fi
fi

if [ "$LOGGED_IN" = false ]; then
    echo -e "${YELLOW}⚠️  You haven't logged in to Kite yet${NC}"
    echo
    echo "To login, run:"
    echo "  python kite_trader.py --login-only"
    echo
    echo "Or press Enter to start the trading API anyway (you can login later)"
    read -p "Press Enter to continue..."
else
    echo -e "${GREEN}✅ Kite login credentials found${NC}"
fi

echo
echo "🚀 Starting Trading API..."
$DOCKER_COMPOSE -f docker-compose.trading.yml up -d trading-api

echo
echo -e "${GREEN}✅ AITRAPP is starting!${NC}"
echo

# Wait a bit for startup
sleep 5

# Show status
echo "======================================================================"
echo "    📊 SERVICE STATUS"
echo "======================================================================"
$DOCKER_COMPOSE -f docker-compose.trading.yml ps
echo

# Check if API is responding
echo "🔍 Checking API health..."
sleep 3

if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Trading API is healthy!${NC}"

    # Get mode
    MODE=$(curl -s http://localhost:8000/health | grep -o '"mode":"[^"]*"' | cut -d'"' -f4 || echo "UNKNOWN")
    echo
    echo "📍 Trading Mode: $MODE"

    if [ "$MODE" = "LIVE" ]; then
        echo -e "${RED}⚠️  ⚠️  ⚠️  LIVE MODE - REAL MONEY TRADING ⚠️  ⚠️  ⚠️${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  API not responding yet (may still be starting up)${NC}"
    echo "Check logs with: $DOCKER_COMPOSE -f docker-compose.trading.yml logs -f trading-api"
fi

echo
echo "======================================================================"
echo "    🎯 QUICK COMMANDS"
echo "======================================================================"
echo
echo "📊 View logs:"
echo "  $DOCKER_COMPOSE -f docker-compose.trading.yml logs -f trading-api"
echo
echo "🔍 Check status:"
echo "  $DOCKER_COMPOSE -f docker-compose.trading.yml ps"
echo "  curl http://localhost:8000/health"
echo
echo "🛑 Stop services:"
echo "  $DOCKER_COMPOSE -f docker-compose.trading.yml down"
echo
echo "🔄 Restart:"
echo "  $DOCKER_COMPOSE -f docker-compose.trading.yml restart trading-api"
echo
echo "🔐 Login to Kite:"
echo "  python kite_trader.py --login-only"
echo
echo "======================================================================"
echo "    🌐 ACCESS POINTS"
echo "======================================================================"
echo
echo "API:          http://localhost:8000"
echo "API Docs:     http://localhost:8000/docs"
echo "Health:       http://localhost:8000/health"
echo "Metrics:      http://localhost:8000/metrics"
echo "PostgreSQL:   localhost:5432 (user: aitrapp, pass: aitrapp)"
echo "Redis:        localhost:6379"
echo
echo "======================================================================"
echo -e "${GREEN}🎉 AITRAPP is ready!${NC}"
echo "======================================================================"
echo
echo "For more information, see: DOCKER_DEPLOYMENT.md"
echo
