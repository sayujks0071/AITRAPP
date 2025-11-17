#!/bin/bash
# Setup alerting configuration

echo "🔔 Setting up Alerting Configuration"
echo "===================================="
echo ""

# Check for Telegram configuration
if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
    echo "✅ Telegram alerts configured"
    echo "   Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
    echo "   Chat ID: $TELEGRAM_CHAT_ID"
else
    echo "ℹ️  Telegram alerts not configured"
    echo "   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable"
fi

echo ""
echo "📋 Available Monitoring Scripts:"
echo "  1. Health Monitor: bash scripts/health_monitor.sh"
echo "  2. Leader Monitor: bash scripts/monitor_leader_changes.sh"
echo ""
echo "💡 To run continuous monitoring:"
echo "  watch -n 30 bash scripts/health_monitor.sh"
echo ""
echo "💡 To monitor leader changes:"
echo "  bash scripts/monitor_leader_changes.sh"
echo ""


