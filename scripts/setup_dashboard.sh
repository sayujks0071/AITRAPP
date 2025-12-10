#!/bin/bash
# Setup script for aitrapp-dashboard
# Creates the folder structure and initializes Next.js if needed

set -e

DASHBOARD_DIR="aitrapp-dashboard"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "🚀 Setting up AITRAPP Dashboard"
echo "================================"
echo ""

# Check if folder exists
if [ -d "$DASHBOARD_DIR" ]; then
    echo "✅ Dashboard folder exists: $DASHBOARD_DIR"
    cd "$DASHBOARD_DIR"
    
    # Check if Next.js is initialized
    if [ -f "package.json" ]; then
        echo "✅ Next.js project already initialized"
        echo ""
        echo "📦 Installing dependencies..."
        npm install || pnpm install || yarn install
    else
        echo "📦 Initializing Next.js project..."
        npx create-next-app@latest . --typescript --tailwind --app --yes
    fi
else
    echo "📁 Creating dashboard folder..."
    mkdir -p "$DASHBOARD_DIR"
    cd "$DASHBOARD_DIR"
    
    echo "📦 Initializing Next.js project..."
    npx create-next-app@latest . --typescript --tailwind --app --yes
fi

echo ""
echo "✅ Dashboard setup complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Copy the setup guide: cat ../AITRAPP_DASHBOARD_SETUP.md"
echo "  2. Create .env.local with your Gemini API key"
echo "  3. Install additional dependencies: npm install @google/generative-ai @tanstack/react-query zustand recharts"
echo "  4. Start development: npm run dev"
echo ""



# Setup script for aitrapp-dashboard
# Creates the folder structure and initializes Next.js if needed

set -e

DASHBOARD_DIR="aitrapp-dashboard"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "🚀 Setting up AITRAPP Dashboard"
echo "================================"
echo ""

# Check if folder exists
if [ -d "$DASHBOARD_DIR" ]; then
    echo "✅ Dashboard folder exists: $DASHBOARD_DIR"
    cd "$DASHBOARD_DIR"
    
    # Check if Next.js is initialized
    if [ -f "package.json" ]; then
        echo "✅ Next.js project already initialized"
        echo ""
        echo "📦 Installing dependencies..."
        npm install || pnpm install || yarn install
    else
        echo "📦 Initializing Next.js project..."
        npx create-next-app@latest . --typescript --tailwind --app --yes
    fi
else
    echo "📁 Creating dashboard folder..."
    mkdir -p "$DASHBOARD_DIR"
    cd "$DASHBOARD_DIR"
    
    echo "📦 Initializing Next.js project..."
    npx create-next-app@latest . --typescript --tailwind --app --yes
fi

echo ""
echo "✅ Dashboard setup complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Copy the setup guide: cat ../AITRAPP_DASHBOARD_SETUP.md"
echo "  2. Create .env.local with your Gemini API key"
echo "  3. Install additional dependencies: npm install @google/generative-ai @tanstack/react-query zustand recharts"
echo "  4. Start development: npm run dev"
echo ""





