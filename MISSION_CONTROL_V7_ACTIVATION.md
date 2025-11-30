# 🚀 Mission Control v7.0 - Activation Guide

## ✅ Upgrade Complete

Mission Control v7.0 is fully integrated with:
- ✅ Real-time NIFTY 50 and BANKNIFTY prices
- ✅ True Strategy Status (DEPLOYED vs SCANNING)
- ✅ Portfolio Intelligence (ALGO vs MANUAL tags)

---

## 🎯 Activation Steps

### Step 1: Restart the API

The backend changes require a restart to load the new snapshot engine:

```bash
./go_live.sh
```

This will:
- Restart the FastAPI server
- Load the updated `portfolio_snapshot.py` with indices fetching
- Enable real-time data feeds

### Step 2: Open Mission Control Dashboard

Open the dashboard in your browser:

```bash
# Option 1: Direct file open
open web_dashboard.html

# Option 2: Via local server (if you have one)
python3 -m http.server 8080
# Then visit: http://localhost:8080/web_dashboard.html
```

---

## 🔍 What to Expect

### Live Indices Display
- **NIFTY 50**: Real-time price from Kite API
- **BANKNIFTY**: Real-time price from Kite API
- Color-coded change percentages (green/red)
- Updates every 2 seconds

### Strategy Status Cards

**SCANNING (Blue Radar):**
- Strategy is enabled but has no open positions
- Shows "SCANNING" badge
- Displays Total PnL (realized + unrealized)

**DEPLOYED (Green/Red):**
- Strategy has open positions detected in portfolio
- Shows "DEPLOYED" badge
- Displays **Live PnL** from actual positions
- Color: Green if profitable, Red if losing

### Portfolio Positions Table

Each position now shows:
- **Instrument** name
- **ALGO** badge (purple) - Position from algorithmic strategy
- **MANUAL** badge (gray) - Position not from any strategy
- **Quantity** (green/red)
- **PnL** (color-coded)

---

## 🧪 Verification Checklist

After activation, verify:

- [ ] NIFTY 50 price is updating (not showing mock data)
- [ ] BANKNIFTY price is updating (not showing mock data)
- [ ] Strategy cards show correct status (SCANNING or DEPLOYED)
- [ ] Deployed strategies show Live PnL
- [ ] Portfolio positions show ALGO/MANUAL tags
- [ ] Dashboard title shows "v7.0"

---

## 🔧 Troubleshooting

### Indices Not Updating

**Issue**: NIFTY/BANKNIFTY showing `--.--`

**Solutions**:
1. Check Kite API connection: `curl http://localhost:8000/health`
2. Verify Kite credentials in `.env`
3. Check API logs for errors
4. Fallback to portfolio snapshot indices should work

### Strategy Status Incorrect

**Issue**: Strategies showing wrong status

**Solutions**:
1. Verify portfolio snapshot endpoint: `curl http://localhost:8000/api/portfolio/snapshot`
2. Check that positions have correct `strategy` tags
3. Verify PositionStore is syncing correctly

### Portfolio Tags Missing

**Issue**: ALGO/MANUAL tags not showing

**Solutions**:
1. Check browser console for JavaScript errors
2. Verify portfolio snapshot includes strategy tags
3. Refresh dashboard (F5)

---

## 📊 API Endpoints Used

The dashboard uses these endpoints:

- `/api/market/indices` - Direct indices API (primary)
- `/api/portfolio/snapshot` - Portfolio snapshot with indices (fallback)
- `/api/strategies/summary` - Strategy performance data
- `/api/regime/current` - Market regime
- `/health` - System health

---

## 🎉 Success Indicators

You'll know v7.0 is working when:

1. ✅ **Real Prices**: NIFTY/BANKNIFTY show actual market prices (not sine waves)
2. ✅ **Smart Status**: Strategies correctly show DEPLOYED when they have positions
3. ✅ **Live PnL**: Deployed strategies show PnL from actual positions
4. ✅ **Clear Tags**: Portfolio positions clearly marked ALGO or MANUAL

---

## 📝 Technical Details

### Backend Changes
- `PortfolioSnapshot` dataclass now includes `indices` field
- Snapshot engine fetches `NSE:NIFTY 50` and `NSE:NIFTY BANK` via `kite.ltp()`
- Improved strategy tag mapping from PositionStore

### Frontend Changes
- Indices fallback chain: Direct API → Portfolio Snapshot → Mock
- Strategy status calculated from portfolio positions
- Live PnL computed from actual position data
- Visual badges for ALGO/MANUAL positions

---

**Mission Control v7.0 is ready for launch!** 🚀

*For issues or questions, check the logs or API health endpoint.*


