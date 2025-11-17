#!/bin/bash
# Comprehensive health monitoring script for live trading system

API_BASE="${API_BASE:-http://localhost:8000}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
ALERT_TELEGRAM="${ALERT_TELEGRAM:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_api_health() {
    local response=$(curl -fsS "$API_BASE/ready" 2>/dev/null)
    if [[ -z "$response" ]]; then
        echo -e "${RED}❌ API Server: Not responding${NC}"
        return 1
    fi
    
    local mode=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('mode', 'UNKNOWN'))" 2>/dev/null)
    local leader=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('leader', 0))" 2>/dev/null)
    local status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)
    
    if [[ "$status" == "ready" && "$leader" == "1" ]]; then
        echo -e "${GREEN}✅ API Server: Ready (Mode: $mode, Leader: Active)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  API Server: $status (Mode: $mode, Leader: $leader)${NC}"
        return 1
    fi
}

check_heartbeats() {
    local metrics=$(curl -fsS "$API_BASE/metrics" 2>/dev/null)
    if [[ -z "$metrics" ]]; then
        echo -e "${RED}❌ Metrics: Not available${NC}"
        return 1
    fi
    
    local market_hb=$(echo "$metrics" | grep "^trader_marketdata_heartbeat_seconds" | awk '{print $2}')
    local order_hb=$(echo "$metrics" | grep "^trader_order_stream_heartbeat_seconds" | awk '{print $2}')
    local scan_hb=$(echo "$metrics" | grep "^trader_scan_heartbeat_seconds" | awk '{print $2}')
    
    local issues=0
    
    if [[ -n "$market_hb" ]]; then
        if (( $(echo "$market_hb > 5.0" | bc -l 2>/dev/null || echo 1) )); then
            echo -e "${RED}❌ Market Data Heartbeat: ${market_hb}s (STALE)${NC}"
            issues=$((issues + 1))
        else
            echo -e "${GREEN}✅ Market Data Heartbeat: ${market_hb}s${NC}"
        fi
    fi
    
    if [[ -n "$order_hb" ]]; then
        if (( $(echo "$order_hb > 5.0" | bc -l 2>/dev/null || echo 1) )); then
            echo -e "${RED}❌ Order Stream Heartbeat: ${order_hb}s (STALE)${NC}"
            issues=$((issues + 1))
        else
            echo -e "${GREEN}✅ Order Stream Heartbeat: ${order_hb}s${NC}"
        fi
    fi
    
    if [[ -n "$scan_hb" ]]; then
        if (( $(echo "$scan_hb > 5.0" | bc -l 2>/dev/null || echo 1) )); then
            echo -e "${RED}❌ Scan Heartbeat: ${scan_hb}s (STALE)${NC}"
            issues=$((issues + 1))
        else
            echo -e "${GREEN}✅ Scan Heartbeat: ${scan_hb}s${NC}"
        fi
    fi
    
    return $issues
}

check_leader_stability() {
    local metrics=$(curl -fsS "$API_BASE/metrics" 2>/dev/null)
    if [[ -z "$metrics" ]]; then
        return 1
    fi
    
    local changes=$(echo "$metrics" | grep "^trader_leader_changes_total" | awk '{print $2}')
    local leader=$(echo "$metrics" | grep "^trader_is_leader" | awk '{print $2}')
    
    if [[ "$leader" == "1.0" ]]; then
        if (( $(echo "$changes > 20" | bc -l 2>/dev/null || echo 0) )); then
            echo -e "${YELLOW}⚠️  Leader Changes: $changes (High - may indicate instability)${NC}"
            return 1
        else
            echo -e "${GREEN}✅ Leader: Active (Changes: $changes)${NC}"
            return 0
        fi
    else
        echo -e "${RED}❌ Leader: Not active ($leader)${NC}"
        return 1
    fi
}

check_oco_orphans() {
    local metrics=$(curl -fsS "$API_BASE/metrics" 2>/dev/null)
    if [[ -z "$metrics" ]]; then
        return 1
    fi
    
    local orphans=$(echo "$metrics" | grep "^trader_oco_orphans_total" | awk '{print $2}')
    
    if [[ -n "$orphans" ]]; then
        if (( $(echo "$orphans > 0" | bc -l 2>/dev/null || echo 0) )); then
            echo -e "${RED}❌ OCO Orphans: $orphans (Cleanup needed)${NC}"
            return 1
        else
            echo -e "${GREEN}✅ OCO Orphans: 0${NC}"
            return 0
        fi
    fi
}

check_processes() {
    local api_running=$(ps aux | grep -E "uvicorn.*apps.api.main|python.*apps.api.main" | grep -v grep | wc -l | tr -d ' ')
    local ops_running=$(ps aux | grep -E "next dev" | grep -v grep | wc -l | tr -d ' ')
    
    if [[ "$api_running" -gt 0 ]]; then
        echo -e "${GREEN}✅ API Server Process: Running${NC}"
    else
        echo -e "${RED}❌ API Server Process: Not found${NC}"
        return 1
    fi
    
    if [[ "$ops_running" -gt 0 ]]; then
        echo -e "${GREEN}✅ Ops Browser Process: Running${NC}"
    else
        echo -e "${YELLOW}⚠️  Ops Browser Process: Not running${NC}"
    fi
    
    return 0
}

# Main health check
main() {
    echo "🏥 Live Trading System Health Check"
    echo "===================================="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    local total_issues=0
    
    echo "📡 API & Connectivity:"
    check_api_health || total_issues=$((total_issues + 1))
    echo ""
    
    echo "💓 Heartbeats:"
    check_heartbeats || total_issues=$((total_issues + 1))
    echo ""
    
    echo "👑 Leader Status:"
    check_leader_stability || total_issues=$((total_issues + 1))
    echo ""
    
    echo "🔗 OCO Status:"
    check_oco_orphans || total_issues=$((total_issues + 1))
    echo ""
    
    echo "⚙️  Processes:"
    check_processes || total_issues=$((total_issues + 1))
    echo ""
    
    echo "===================================="
    if [[ $total_issues -eq 0 ]]; then
        echo -e "${GREEN}✅ All systems healthy!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  Found $total_issues issue(s)${NC}"
        exit 1
    fi
}

# Run health check
main "$@"


