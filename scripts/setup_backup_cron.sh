#!/usr/bin/env bash
# Setup automated database backups via cron
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Setting up automated database backups"
echo ""

# Check if running on macOS (use launchd) or Linux (use cron)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Detected macOS - Setting up launchd service"
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.aitrapp.daily-backup.plist"
    
    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aitrapp.daily-backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>bash</string>
        <string>$PROJECT_ROOT/scripts/daily_backup.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/backup.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/backup.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
    
    # Load the service
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"
    
    echo "✅ Daily backup scheduled via launchd (runs at 02:00 daily)"
    echo "   Plist: $PLIST_FILE"
    echo "   Logs: $PROJECT_ROOT/logs/backup.log"
    echo ""
    echo "To unload: launchctl unload $PLIST_FILE"
    
else
    echo "🐧 Detected Linux - Setting up cron job"
    
    CRON_CMD="0 2 * * * cd $PROJECT_ROOT && bash scripts/daily_backup.sh >> logs/backup.log 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "daily_backup.sh"; then
        echo "⚠️  Cron job already exists, skipping..."
    else
        (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
        echo "✅ Daily backup scheduled via cron (runs at 02:00 daily)"
    fi
    
    echo ""
    echo "Weekly backup (Sunday 03:00):"
    WEEKLY_CMD="0 3 * * 0 cd $PROJECT_ROOT && bash scripts/weekly_backup.sh >> logs/backup.log 2>&1"
    if crontab -l 2>/dev/null | grep -q "weekly_backup.sh"; then
        echo "⚠️  Weekly cron job already exists, skipping..."
    else
        (crontab -l 2>/dev/null; echo "$WEEKLY_CMD") | crontab -
        echo "✅ Weekly backup scheduled via cron (runs Sunday at 03:00)"
    fi
    
    echo ""
    echo "To view cron jobs: crontab -l"
    echo "To remove: crontab -e (then delete the lines)"
fi

echo ""
echo "✅ Backup automation setup complete!"
