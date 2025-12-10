#!/usr/bin/env bash
# Crypto report generator - aggregates last 24h scorer JSONs
set -euo pipefail

export TZ="${TZ:-UTC}"

REPORTS_DIR="reports/burnin"
OUTPUT_DIR="reports/crypto"
mkdir -p "$OUTPUT_DIR"

TODAY=$(date +%F)
YESTERDAY=$(date -v-1d +%F 2>/dev/null || date -d "1 day ago" +%F 2>/dev/null || echo "")

echo "📊 Crypto Report Generator"
echo "========================="
echo ""

# Find crypto Day-1 JSONs from last 24h
FILES=()
if [ -d "$REPORTS_DIR" ]; then
    # Find files from today and yesterday
    for file in "$REPORTS_DIR"/crypto_day1_*.json; do
        if [ -f "$file" ]; then
            # Check if file is from last 24h
            file_date=$(basename "$file" | sed 's/crypto_day1_\(.*\)\.json/\1/')
            if [ "$file_date" = "$TODAY" ] || [ "$file_date" = "$YESTERDAY" ]; then
                FILES+=("$file")
            fi
        fi
    done
fi

if [ ${#FILES[@]} -eq 0 ]; then
    echo "⚠️  No crypto Day-1 JSONs found in last 24h"
    echo "   Run: make score-crypto-day1"
    exit 0
fi

echo "Found ${#FILES[@]} report(s) from last 24h"
echo ""

# Aggregate stats
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_ORPHANS=0
TOTAL_WS_RECONNECTS=0
TOTAL_ORDERS=0
LATEST_STATUS="UNKNOWN"

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    status=$(jq -r '.status // "UNKNOWN"' "$file" 2>/dev/null || echo "UNKNOWN")
    if [ "$status" = "PASS" ]; then
        TOTAL_PASS=$((TOTAL_PASS + 1))
    else
        TOTAL_FAIL=$((TOTAL_FAIL + 1))
    fi
    
    orphans=$(jq -r '.oco_orphans // 0' "$file" 2>/dev/null || echo "0")
    ws_reconnects=$(jq -r '.crypto_ws_reconnects // 0' "$file" 2>/dev/null || echo "0")
    orders=$(jq -r '.crypto_orders // 0' "$file" 2>/dev/null || echo "0")
    
    TOTAL_ORPHANS=$((TOTAL_ORPHANS + orphans))
    TOTAL_WS_RECONNECTS=$((TOTAL_WS_RECONNECTS + ws_reconnects))
    TOTAL_ORDERS=$((TOTAL_ORDERS + orders))
    
    # Get latest status
    if [ -z "$LATEST_STATUS" ] || [ "$LATEST_STATUS" = "UNKNOWN" ]; then
        LATEST_STATUS="$status"
    fi
done

# Generate markdown report
REPORT_FILE="$OUTPUT_DIR/crypto_report_${TODAY}.md"
{
    echo "# Crypto Trading Report - ${TODAY}"
    echo ""
    echo "**Generated:** $(date -Is)"
    echo "**Mode:** CRYPTO_PAPER"
    echo ""
    echo "## Summary"
    echo ""
    echo "| Metric | Value |"
    echo "|--------|-------|"
    echo "| **Status** | ${LATEST_STATUS} |"
    echo "| **Reports (24h)** | ${#FILES[@]} |"
    echo "| **PASS** | ${TOTAL_PASS} |"
    echo "| **FAIL** | ${TOTAL_FAIL} |"
    echo "| **OCO Orphans (total)** | ${TOTAL_ORPHANS} |"
    echo "| **WS Reconnects (total)** | ${TOTAL_WS_RECONNECTS} |"
    echo "| **Orders Placed (total)** | ${TOTAL_ORDERS} |"
    echo ""
    echo "## Recent Reports"
    echo ""
    
    # Sort files by date (newest first)
    printf '%s\n' "${FILES[@]}" | sort -r | while read -r file; do
        if [ ! -f "$file" ]; then
            continue
        fi
        
        file_date=$(basename "$file" | sed 's/crypto_day1_\(.*\)\.json/\1/')
        status=$(jq -r '.status // "UNKNOWN"' "$file" 2>/dev/null || echo "UNKNOWN")
        leader=$(jq -r '.leader // 0' "$file" 2>/dev/null || echo "0")
        md_hb=$(jq -r '.heartbeats.market // 999' "$file" 2>/dev/null || echo "999")
        order_hb=$(jq -r '.heartbeats.orders // 999' "$file" 2>/dev/null || echo "999")
        scan_hb=$(jq -r '.heartbeats.scan // 999' "$file" 2>/dev/null || echo "999")
        orphans=$(jq -r '.oco_orphans // 0' "$file" 2>/dev/null || echo "0")
        ws_reconnects=$(jq -r '.crypto_ws_reconnects // 0' "$file" 2>/dev/null || echo "0")
        
        echo "### ${file_date}"
        echo ""
        echo "- **Status:** ${status}"
        echo "- **Leader:** ${leader}"
        echo "- **Heartbeats:** Market=${md_hb}s, Orders=${order_hb}s, Scan=${scan_hb}s"
        echo "- **OCO Orphans:** ${orphans}"
        echo "- **WS Reconnects:** ${ws_reconnects}"
        echo ""
    done
    
    echo "## Health Status"
    echo ""
    if [ "$LATEST_STATUS" = "PASS" ] && [ "$TOTAL_ORPHANS" -eq 0 ] && [ "$TOTAL_WS_RECONNECTS" -le 5 ]; then
        echo "✅ **HEALTHY** - All checks passing, no orphans, low reconnect rate"
    elif [ "$LATEST_STATUS" = "PASS" ]; then
        echo "⚠️  **PASSING** - Some metrics need attention (orphans or reconnects)"
    else
        echo "❌ **UNHEALTHY** - Recent failures detected"
    fi
    echo ""
    
} > "$REPORT_FILE"

echo "✅ Report generated: $REPORT_FILE"
echo ""
cat "$REPORT_FILE"


