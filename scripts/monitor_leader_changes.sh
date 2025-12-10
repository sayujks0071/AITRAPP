#!/bin/bash
# Monitor leader changes and alert if excessive

API_BASE="${API_BASE:-http://localhost:8000}"
CHECK_INTERVAL="${CHECK_INTERVAL:-5}"
ALERT_THRESHOLD="${ALERT_THRESHOLD:-3}"

echo "🔍 Leader Change Monitor"
echo "========================"
echo "API: $API_BASE"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Alert threshold: ${ALERT_THRESHOLD} changes in 5 minutes"
echo ""

LAST_COUNT=0
CHANGE_COUNT=0
ALERT_SENT=false

while true; do
    # Get current leader status
    LEADER=$(curl -fsS "$API_BASE/metrics" 2>/dev/null | grep "^trader_is_leader" | awk '{print $2}')
    LEADER_CHANGES=$(curl -fsS "$API_BASE/metrics" 2>/dev/null | grep "^trader_leader_changes_total" | awk '{print $2}')
    
    if [[ -z "$LEADER" || -z "$LEADER_CHANGES" ]]; then
        echo "❌ $(date '+%H:%M:%S') - Could not fetch metrics"
        sleep $CHECK_INTERVAL
        continue
    fi
    
    # Check if leader changed
    if (( $(echo "$LEADER_CHANGES > $LAST_COUNT" | bc -l 2>/dev/null || echo 0) )); then
        CHANGE_COUNT=$((CHANGE_COUNT + 1))
        DIFF=$(echo "$LEADER_CHANGES - $LAST_COUNT" | bc -l 2>/dev/null || echo "0")
        echo "⚠️  $(date '+%H:%M:%S') - Leader changed! Total: $LEADER_CHANGES (+$DIFF)"
        
        # Alert if threshold exceeded
        if (( $(echo "$CHANGE_COUNT >= $ALERT_THRESHOLD" | bc -l 2>/dev/null || echo 0) )) && [[ "$ALERT_SENT" == "false" ]]; then
            echo "🚨 ALERT: Excessive leader changes detected ($CHANGE_COUNT in recent period)"
            echo "   This may indicate system instability. Check logs and system health."
            ALERT_SENT=true
        fi
    else
        # Reset alert if stable
        if [[ "$ALERT_SENT" == "true" ]]; then
            echo "✅ $(date '+%H:%M:%S') - Leader stable. Resetting alert."
            ALERT_SENT=false
            CHANGE_COUNT=0
        fi
    fi
    
    # Status update every 30 seconds
    if (( $(date +%S) % 30 < $CHECK_INTERVAL )); then
        if [[ "$LEADER" == "1.0" ]]; then
            echo "✅ $(date '+%H:%M:%S') - Leader: Active | Changes: $LEADER_CHANGES"
        else
            echo "⚠️  $(date '+%H:%M:%S') - Leader: Inactive ($LEADER) | Changes: $LEADER_CHANGES"
        fi
    fi
    
    LAST_COUNT=$LEADER_CHANGES
    sleep $CHECK_INTERVAL
done


