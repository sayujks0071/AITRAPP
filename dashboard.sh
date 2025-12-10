#!/bin/bash
# Mission Control Dashboard Launcher
# ===================================
# Launches the Level 12 Mission Control Dashboard

cd "$(dirname "$0")"

echo "🚀 Launching AITRAPP Mission Control Dashboard..."
echo ""

# Check if rich is installed
python3 -c "import rich" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  'rich' library not found. Installing..."
    pip3 install rich
fi

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Server not responding on localhost:8000"
    echo "   Make sure ./go_live.sh is running first"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Launch dashboard
python3 scripts/dashboard.py




