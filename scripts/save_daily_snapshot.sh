#!/bin/bash
# Save daily snapshot: report + sanity check output
# Usage: ./scripts/save_daily_snapshot.sh
# Run this post-close to archive the day's data

set -e

REPORTS_DIR="reports/daily"
DATE=$(date +%Y-%m-%d)
SNAPSHOT_DIR="$REPORTS_DIR/$DATE"

mkdir -p "$SNAPSHOT_DIR"

echo "📸 Saving daily snapshot for $DATE..."

# Generate daily report if not already done
if [ ! -f "$SNAPSHOT_DIR/${DATE}_report.md" ]; then
    echo "📊 Generating daily report..."
    make daily-report || echo "⚠️  Report generation failed (may need API running)"
fi

# Run sanity check and save output
echo "🔍 Running sanity check..."
python3 scripts/quick_sanity_check.py > "$SNAPSHOT_DIR/${DATE}_sanity_check.txt" 2>&1 || echo "⚠️  Sanity check failed (may need Prometheus running)"

# Save configs snapshot (for audit trail)
echo "📋 Saving configs snapshot..."
mkdir -p "$SNAPSHOT_DIR/configs"
cp configs/*.yaml "$SNAPSHOT_DIR/configs/" 2>/dev/null || echo "⚠️  No configs to copy"

echo "✅ Snapshot saved to: $SNAPSHOT_DIR"
echo ""
echo "📁 Contents:"
ls -lh "$SNAPSHOT_DIR"

