# MCP Historical Data - Quick Command Reference

**Copy-paste commands for common workflows**

---

## ✅ Prerequisites Check

```bash
# Check if MCP server is running
curl -s http://localhost:8080/health && echo "✅ MCP server is UP" || echo "❌ MCP server is DOWN"

# Check Kite credentials
echo "API Key: ${KITE_API_KEY:0:10}..."
echo "Access Token: ${KITE_ACCESS_TOKEN:0:10}..."
```

## 🚀 Start MCP Server (if not running)

```bash
cd kite-mcp-server
./kite-mcp-server

# Or run in background
nohup ./kite-mcp-server > logs/kite_mcp.log 2>&1 &
```

---

## 📊 Common Backtest Commands

### Quick Test (Last 7 Days)

```bash
# RSI Mean Reversion - 7 days
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 7 \
  --interval 5minute
```

### Multiple Strategies Comparison

```bash
# Test 3 strategies together
python scripts/run_mcp_backtest.py \
  --strategy "RSIMeanReversion,MACD,BollingerBands" \
  --days 14 \
  --interval 5minute \
  --output results/strategy_comparison.json
```

### High Resolution Backtest

```bash
# 1-minute data for precise replay
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 3 \
  --interval 1minute
```

### Custom Date Range

```bash
# Specific date range
python scripts/run_mcp_backtest.py \
  --strategy MACD \
  --from-date "2025-11-15" \
  --to-date "2025-11-26" \
  --interval 5minute
```

### BANKNIFTY Backtest

```bash
# Test on BANKNIFTY instead of NIFTY
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --underlying BANKNIFTY \
  --days 7 \
  --interval 5minute
```

---

## 🎬 Replay Mode (Paper Trading Simulation)

### Replay Today's Market

```bash
# After market close (3:30 PM) - replay full day
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD" \
  --interval 1minute
```

### Replay with Multiple Strategies

```bash
# Test all strategies on today's data
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD,BollingerBands,VWAP,ORB" \
  --interval 1minute \
  --output results/today_replay_$(date +%Y%m%d).json
```

### Replay BANKNIFTY Today

```bash
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --underlying BANKNIFTY \
  --strategy "RSIMeanReversion,MACD" \
  --interval 1minute
```

---

## 🔄 Automated Daily Backtesting

### Setup Cron Job (Runs at 4 PM daily)

```bash
# Edit crontab
crontab -e

# Add this line (runs Mon-Fri at 4 PM after market close)
0 16 * * 1-5 cd /Users/mac/CRYPTO/AITRAPP && \
  /usr/local/bin/python3 scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD,BollingerBands" \
  --interval 1minute \
  --output results/daily_backtest_$(date +\%Y\%m\%d).json \
  >> logs/daily_backtest.log 2>&1
```

### Manual Daily Run (After Market Close)

```bash
# Run after 3:30 PM
cd /Users/mac/CRYPTO/AITRAPP

python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD,BollingerBands,VWAP,ORB" \
  --interval 1minute \
  --output results/daily_backtest_$(date +%Y%m%d).json
```

---

## 📈 Analysis Commands

### View Results

```bash
# Pretty print JSON results
cat results/backtest_results.json | python3 -m json.tool

# Extract key metrics
jq '.total_signals, .total_trades, .signals_by_strategy' results/backtest_results.json
```

### Compare Multiple Results

```bash
# Compare today vs yesterday
echo "Today:"
jq '.total_signals, .total_trades' results/daily_backtest_$(date +%Y%m%d).json

echo "Yesterday:"
jq '.total_signals, .total_trades' results/daily_backtest_$(date -v-1d +%Y%m%d).json
```

### Summary Report

```bash
# Quick summary of last 7 daily backtests
for f in results/daily_backtest_*.json; do
  echo "=== $(basename $f) ==="
  jq -r '"Signals: \(.total_signals) | Trades: \(.total_trades)"' "$f"
done
```

---

## 🛠️ Development Workflow

### Step 1: Quick Test (Minutes)

```bash
# Test on last 3 days only
python scripts/run_mcp_backtest.py \
  --strategy MyNewStrategy \
  --days 3 \
  --interval 5minute
```

### Step 2: Full Backtest (30 Days)

```bash
# If step 1 looks good, test on longer period
python scripts/run_mcp_backtest.py \
  --strategy MyNewStrategy \
  --days 30 \
  --interval 5minute \
  --output results/strategy_backtest_30d.json
```

### Step 3: High Fidelity Test (1-Minute)

```bash
# Test at highest resolution on recent data
python scripts/run_mcp_backtest.py \
  --strategy MyNewStrategy \
  --days 3 \
  --interval 1minute \
  --output results/strategy_backtest_1min.json
```

### Step 4: Replay Today

```bash
# After market close, test on today
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy MyNewStrategy \
  --interval 1minute \
  --output results/strategy_today.json
```

### Step 5: Enable Paper Trading

```bash
# If all tests pass, add to paper trading config
# Edit configs/kite_paper.yaml and add MyNewStrategy

# Restart paper trading
export APP_MODE=PAPER
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

---

## 🔍 Debugging Commands

### Test MCP Connection

```python
# Quick Python test
python3 << 'EOF'
from packages.core.historical_data_mcp import HistoricalDataMCPProvider
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient

mcp = MCPClient(server_url="http://localhost:8080")
adapter = KiteMCPAdapter(mcp_client=mcp)
provider = HistoricalDataMCPProvider(kite_mcp_adapter=adapter)

# Search for NIFTY
instruments = provider.search_instrument("NIFTY")
print(f"Found {len(instruments)} instruments")
print(instruments[0] if instruments else "No instruments found")
EOF
```

### Fetch Sample Data

```python
# Test data fetching
python3 << 'EOF'
from packages.core.historical_data_mcp import HistoricalDataMCPProvider
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient
from datetime import datetime, timedelta

mcp = MCPClient(server_url="http://localhost:8080")
adapter = KiteMCPAdapter(mcp_client=mcp)
provider = HistoricalDataMCPProvider(kite_mcp_adapter=adapter)

# Fetch last 2 days for NIFTY (token 256265)
candles = provider.fetch_date_range(
    instrument_token=256265,
    days=2,
    interval="5minute"
)

print(f"Fetched {len(candles)} candles")
if candles:
    print(f"Sample: {candles[0]}")
EOF
```

### Check Historical Data Availability

```bash
# Check if data exists for a specific date
python3 << 'EOF'
from packages.core.historical_data_mcp import HistoricalDataMCPProvider
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient

mcp = MCPClient(server_url="http://localhost:8080")
adapter = KiteMCPAdapter(mcp_client=mcp)
provider = HistoricalDataMCPProvider(kite_mcp_adapter=adapter)

candles = provider.fetch_candles(
    instrument_token=256265,
    from_date="2025-11-26 09:15:00",
    to_date="2025-11-26 15:30:00",
    interval="5minute"
)

print(f"Data available for 2025-11-26: {len(candles)} candles")
EOF
```

---

## 📁 File Organization

```bash
# Create results directory structure
mkdir -p results/{daily,weekly,monthly,strategy_tests}

# Daily backtests go here
results/daily/backtest_20251126.json

# Weekly comparisons
results/weekly/comparison_week48.json

# Strategy development tests
results/strategy_tests/my_strategy_v1.json
```

---

## 🎯 Common Workflows

### Workflow 1: New Strategy Development

```bash
# 1. Quick sanity check
python scripts/run_mcp_backtest.py --strategy MyStrategy --days 3 --interval 5minute

# 2. Extended backtest
python scripts/run_mcp_backtest.py --strategy MyStrategy --days 30 --interval 5minute

# 3. High fidelity test
python scripts/run_mcp_backtest.py --strategy MyStrategy --days 3 --interval 1minute

# 4. Replay today (after market)
python scripts/run_mcp_backtest.py --replay-mode --strategy MyStrategy --interval 1minute

# 5. If all pass, enable in paper trading config
```

### Workflow 2: Daily Strategy Validation

```bash
# Every day after 4 PM:

# 1. Replay today for all active strategies
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "$(grep 'name:' configs/kite_paper.yaml | awk '{print $3}' | tr '\n' ',' | sed 's/,$//')" \
  --interval 1minute \
  --output results/daily/backtest_$(date +%Y%m%d).json

# 2. Review results
cat results/daily/backtest_$(date +%Y%m%d).json | jq '.signals_by_strategy'
```

### Workflow 3: Strategy Comparison

```bash
# Compare multiple strategies on same data
python scripts/run_mcp_backtest.py \
  --strategy "Strategy1,Strategy2,Strategy3" \
  --days 14 \
  --interval 5minute \
  --output results/comparison_$(date +%Y%m%d).json

# Extract comparison metrics
jq '.signals_by_strategy' results/comparison_$(date +%Y%m%d).json
```

---

## 🚨 Troubleshooting

### MCP Server Not Responding

```bash
# Check if running
ps aux | grep kite-mcp-server

# Check logs
tail -f kite-mcp-server/logs/*.log

# Restart
cd kite-mcp-server
killall kite-mcp-server
./kite-mcp-server
```

### No Data Returned

```bash
# Check date range (weekends/holidays have no data)
date +%A  # Check day of week

# Try a known good date (last Friday if today is weekend)
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --from-date "2025-11-22" \
  --to-date "2025-11-22" \
  --interval 5minute
```

### Rate Limit Errors

```bash
# If you hit rate limits, reduce frequency:
# 1. Use longer intervals (5minute instead of 1minute)
# 2. Fetch fewer days
# 3. Wait 1-2 minutes between requests

# Example: Gentler backtest
python scripts/run_mcp_backtest.py \
  --strategy RSIMeanReversion \
  --days 7 \
  --interval 15minute  # Less data points = fewer API calls
```

---

## 📊 Performance Monitoring

### Track Backtest Performance Over Time

```bash
# Create performance tracking script
cat > scripts/track_performance.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
OUTPUT="results/daily/backtest_${DATE}.json"

# Run backtest
python scripts/run_mcp_backtest.py \
  --replay-mode \
  --strategy "RSIMeanReversion,MACD,BollingerBands" \
  --interval 1minute \
  --output "$OUTPUT"

# Extract metrics
echo "Date: $DATE"
jq '.signals_by_strategy' "$OUTPUT"
EOF

chmod +x scripts/track_performance.sh
```

### Aggregate Weekly Stats

```bash
# Summarize last week's results
cat > scripts/weekly_summary.sh << 'EOF'
#!/bin/bash
echo "=== Weekly Backtest Summary ==="
for file in results/daily/backtest_*.json; do
    if [[ -f "$file" ]]; then
        DATE=$(basename "$file" | grep -o '[0-9]\{8\}')
        SIGNALS=$(jq '.total_signals' "$file")
        TRADES=$(jq '.total_trades' "$file")
        echo "$DATE: $SIGNALS signals, $TRADES trades"
    fi
done
EOF

chmod +x scripts/weekly_summary.sh
./scripts/weekly_summary.sh
```

---

**🎉 You're ready to backtest with real data!**

Start with the quick test command and work your way up to automated daily validation.
