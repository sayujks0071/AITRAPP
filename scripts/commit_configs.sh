#!/bin/bash
# Commit config changes with standard message format
# Usage: ./scripts/commit_configs.sh "tune: R1 bands + T1 NIFTY term structure thresholds"

set -e

CONFIG_DIR="configs"
MESSAGE="${1:-tune: config adjustments}"

# Check if there are any changes in configs/
if ! git diff --quiet "$CONFIG_DIR" && ! git diff --cached --quiet "$CONFIG_DIR"; then
    echo "📝 Staging config changes..."
    git add "$CONFIG_DIR"/*.yaml
    
    echo "💾 Committing: $MESSAGE"
    git commit -m "$MESSAGE"
    
    echo "✅ Configs committed"
else
    echo "ℹ️  No config changes to commit"
fi

