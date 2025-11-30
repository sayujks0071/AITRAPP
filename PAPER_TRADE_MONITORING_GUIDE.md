# Paper Trade Monitoring Guide

**Monitor your live paper trading in real-time using Kite MCP**

---

## 🎯 Quick Start

### **Option 1: Live Dashboard (Auto-refresh every 30s)**

```bash
# Continuous monitoring with auto-refresh
python3 scripts/monitor_paper_trade.py
```

**Output:**
```
======================================================================
📊 LIVE PAPER TRADE MONITOR
======================================================================

⏰ Time: 2025-11-27 10:49:52
👤 User: Your Name (ABC123)

----------------------------------------------------------------------
💰 P&L SUMMARY
----------------------------------------------------------------------
  🟢 Total P&L:      ₹1,245.50
  🟢 Realized:       ₹850.00
  🟢 Unrealized:     ₹395.50

----------------------------------------------------------------------
📈 POSITIONS
----------------------------------------------------------------------
  Total Positions:  5
  Active:           2
  Closed:           3

  Active Positions:

  1. NIFTY25DEC24800CE
     Qty: +75 | Avg: ₹145.30 | LTP: ₹152.80
     🟢 P&L: ₹562.50

  2. BANKNIFTY25DEC51000PE
     Qty: +50 | Avg: ₹235.60 | LTP: ₹228.90
     🔴 P&L: ₹-335.00
```

### **Option 2: Single Snapshot**

```bash
# Just show current status once
python3 scripts/monitor_paper_trade.py --once
```

### **Option 3: Export to JSON**

```bash
# Export current status to file
python3 scripts/monitor_paper_trade.py --once --export snapshot.json

# View the export
cat snapshot.json | python3 -m json.tool
```

---

## 📊 What You Can Monitor

### **1. Real-time P&L**
- ✅ Total P&L (realized + unrealized)
- ✅ Realized P&L (closed positions)
- ✅ Unrealized P&L (open positions)
- ✅ Color-coded (🟢 profit, 🔴 loss)

### **2. Active Positions**
- ✅ Open positions with live prices
- ✅ Quantity, avg price, LTP
- ✅ Individual position P&L
- ✅ Up to 10 most recent positions shown

### **3. Today's Orders**
- ✅ Total order count
- ✅ Orders by status (Complete, Open, Rejected, Cancelled)
- ✅ Last 5 orders with details
- ✅ Order timestamps

### **4. Margin Utilization**
- ✅ Available margin
- ✅ Used margin
- ✅ Total margin
- ✅ Utilization percentage with progress bar

---

## 🎛️ Command Options

### **Basic Usage**

```bash
# Continuous monitoring (default: 30s refresh)
python3 scripts/monitor_paper_trade.py

# Custom refresh interval (10 seconds)
python3 scripts/monitor_paper_trade.py --interval 10

# Fast refresh (5 seconds)
python3 scripts/monitor_paper_trade.py --interval 5

# Single snapshot (no loop)
python3 scripts/monitor_paper_trade.py --once
```

### **Data Export**

```bash
# Export to JSON
python3 scripts/monitor_paper_trade.py --once --export data.json

# Raw JSON output (for parsing)
python3 scripts/monitor_paper_trade.py --once --raw > output.json
```

### **Alerts (Coming Soon)**

```bash
# Watch P&L and alert if < -₹1000
python3 scripts/monitor_paper_trade.py --watch pnl

# Watch positions for changes
python3 scripts/monitor_paper_trade.py --watch positions
```

---

## 🔄 Integration with Paper Trading System

### **Monitor While Paper Trading**

```bash
# Terminal 1: Start paper trading
cd /Users/mac/CRYPTO/AITRAPP
export APP_MODE=PAPER
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Monitor live
python3 scripts/monitor_paper_trade.py
```

### **Monitor + Logs**

```bash
# Terminal 1: Paper trading
tail -f logs/api_8000.log

# Terminal 2: Live monitor
python3 scripts/monitor_paper_trade.py --interval 10
```

---

## 📈 Use Cases

### **1. Intraday Monitoring**

```bash
# Quick check every 30s during trading hours
python3 scripts/monitor_paper_trade.py
```

**When to use:**
- ✅ Actively trading during market hours
- ✅ Want to see real-time P&L
- ✅ Monitor position changes

### **2. End-of-Day Summary**

```bash
# Get final snapshot after market close
python3 scripts/monitor_paper_trade.py --once --export eod_$(date +%Y%m%d).json
```

**When to use:**
- ✅ After 3:30 PM to see final P&L
- ✅ Record daily performance
- ✅ Compare with backtest results

### **3. Position Check**

```bash
# Quick position check
python3 scripts/monitor_paper_trade.py --once | grep -A 20 "POSITIONS"
```

**When to use:**
- ✅ Verify position entries
- ✅ Check if stop losses triggered
- ✅ Monitor position sizes

### **4. Order Validation**

```bash
# Check order status
python3 scripts/monitor_paper_trade.py --once | grep -A 10 "ORDERS"
```

**When to use:**
- ✅ Verify order execution
- ✅ Check for rejections
- ✅ Monitor order flow

---

## 🎯 Example Workflows

### **Workflow 1: Active Trading Day**

```bash
# 09:00 AM - Pre-market check
python3 scripts/monitor_paper_trade.py --once

# 09:15 AM - Start paper trading + continuous monitor
# Terminal 1: Start paper trading
export APP_MODE=PAPER && python -m uvicorn apps.api.main:app --port 8000

# Terminal 2: Monitor live
python3 scripts/monitor_paper_trade.py --interval 30

# During the day: Monitor updates automatically every 30s

# 03:30 PM - Final snapshot
python3 scripts/monitor_paper_trade.py --once --export eod_$(date +%Y%m%d).json

# Review day's performance
cat eod_$(date +%Y%m%d).json | jq '.pnl'
```

### **Workflow 2: Strategy Validation**

```bash
# After strategy generates signal, verify position opened
python3 scripts/monitor_paper_trade.py --once

# Check if position matches expectations:
# - Correct symbol
# - Correct quantity
# - Correct side (BUY/SELL)
# - Correct price range

# Monitor P&L evolution
python3 scripts/monitor_paper_trade.py --interval 10
```

### **Workflow 3: Daily Performance Tracking**

```bash
# Create daily tracking script
cat > scripts/daily_tracking.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
OUTPUT="results/daily_tracking_${DATE}.json"

# Get EOD snapshot
python3 scripts/monitor_paper_trade.py --once --export "$OUTPUT"

# Extract key metrics
echo "=== Daily Performance $DATE ==="
jq '.pnl' "$OUTPUT"
jq '.positions' "$OUTPUT"
EOF

chmod +x scripts/daily_tracking.sh

# Run daily at 4 PM
# Add to crontab:
# 0 16 * * 1-5 cd /Users/mac/CRYPTO/AITRAPP && ./scripts/daily_tracking.sh
```

---

## 📊 Sample Output Scenarios

### **Scenario 1: Profitable Day**

```
💰 P&L SUMMARY
  🟢 Total P&L:      ₹3,245.80
  🟢 Realized:       ₹2,850.00
  🟢 Unrealized:     ₹395.80

📈 POSITIONS
  Active:           2
  Closed:           5
```

### **Scenario 2: Loss Day**

```
💰 P&L SUMMARY
  🔴 Total P&L:      ₹-1,458.20
  🔴 Realized:       ₹-1,200.00
  🔴 Unrealized:     ₹-258.20

📈 POSITIONS
  Active:           1
  Closed:           4
```

### **Scenario 3: Mixed Results**

```
💰 P&L SUMMARY
  🟢 Total P&L:      ₹185.50
  🟢 Realized:       ₹450.00
  🔴 Unrealized:     ₹-264.50

📈 POSITIONS
  Active:           3
  Closed:           2
```

---

## 🔍 Advanced Usage

### **Parse JSON for Automation**

```bash
# Extract specific metrics
python3 scripts/monitor_paper_trade.py --once --raw | jq '.pnl.total'

# Count active positions
python3 scripts/monitor_paper_trade.py --once --raw | jq '.positions.active'

# Get margin utilization
python3 scripts/monitor_paper_trade.py --once --raw | jq '.margin.used / .margin.total * 100'
```

### **Alert on Specific Conditions**

```bash
# Check if P&L below threshold
PNL=$(python3 scripts/monitor_paper_trade.py --once --raw | jq '.pnl.total')
if (( $(echo "$PNL < -1000" | bc -l) )); then
    echo "🚨 Alert: P&L below -₹1000!"
    # Send notification, email, etc.
fi
```

### **Track Performance Over Time**

```bash
# Log snapshots every 5 minutes
while true; do
    python3 scripts/monitor_paper_trade.py --once --raw >> logs/performance_$(date +%Y%m%d).jsonl
    sleep 300  # 5 minutes
done
```

---

## 🛠️ Troubleshooting

### **"Credentials not set"**

```bash
# Set Kite credentials
export KITE_API_KEY="your_key"
export KITE_ACCESS_TOKEN="your_token"

# Or get new token
python3 scripts/kite_express_login.py
```

### **"No positions/orders"**

This is normal if:
- ✅ Paper trading hasn't started yet today
- ✅ No signals generated yet
- ✅ All positions already closed
- ✅ Market is closed

### **"KiteConnect not installed"**

```bash
pip3 install --break-system-packages kiteconnect
```

---

## 📱 Quick Commands Cheat Sheet

```bash
# Live monitor (auto-refresh)
python3 scripts/monitor_paper_trade.py

# Single snapshot
python3 scripts/monitor_paper_trade.py --once

# Fast refresh (10s)
python3 scripts/monitor_paper_trade.py --interval 10

# Export to JSON
python3 scripts/monitor_paper_trade.py --once --export snapshot.json

# Raw JSON output
python3 scripts/monitor_paper_trade.py --once --raw

# Extract P&L only
python3 scripts/monitor_paper_trade.py --once --raw | jq '.pnl'

# Extract positions only
python3 scripts/monitor_paper_trade.py --once --raw | jq '.positions'

# Extract orders only
python3 scripts/monitor_paper_trade.py --once --raw | jq '.orders'
```

---

## 🎉 Summary

**You now have:**
- ✅ Real-time paper trade monitoring
- ✅ Live P&L tracking
- ✅ Position & order visibility
- ✅ Margin utilization tracking
- ✅ JSON export for analysis
- ✅ Integration with paper trading system

**Quick start:**
```bash
python3 scripts/monitor_paper_trade.py
```

**That's it!** Monitor your paper trades in real-time with live data from Kite. 🚀

---

## 📚 Related Documentation

- [SETUP_HISTORICAL_DATA.md](SETUP_HISTORICAL_DATA.md) - Historical data backtesting
- [PAPER_TRADING_LIVE_STATUS.md](PAPER_TRADING_LIVE_STATUS.md) - Paper trading setup
- [MCP_HISTORICAL_DATA_GUIDE.md](MCP_HISTORICAL_DATA_GUIDE.md) - MCP integration
