# Broker-Grade Cockpit - Implementation Guide

## Overview

The AITRAPP dashboard now includes a **broker-grade cockpit** that displays real-time portfolio state from Kite, including funds, margin, positions, and broker-vs-algo reconciliation.

---

## Architecture

### Backend Components

1. **Portfolio Snapshot Aggregator** (`packages/core/broker/portfolio_snapshot.py`)
   - Aggregates broker state from Kite API
   - Calculates funds, margin, utilization
   - Maps positions with Greeks
   - Performs broker-vs-algo reconciliation

2. **FastAPI Endpoint** (`apps/api/routes/portfolio.py`)
   - `GET /api/portfolio/snapshot`
   - Returns comprehensive portfolio snapshot
   - Auto-refreshes from Kite every request

### Frontend Components

1. **PortfolioPanel Component** (`apps/ops-browser/components/portfolio/PortfolioPanel.tsx`)
   - React component with Tailwind styling
   - Displays funds, margin, positions
   - Shows broker-vs-algo drift status
   - Auto-refreshes every 10 seconds

2. **usePortfolio Hook** (`apps/ops-browser/hooks/usePortfolio.ts`)
   - React hook for fetching portfolio data
   - Handles loading/error states
   - Auto-refresh with interval

---

## Features

### 1. Capital & Margin Card

Displays:
- **Net Worth**: Total equity + cash
- **Available Cash**: Available margin
- **Used Margin**: Utilized debits + premium
- **Utilization %**: Used / (Used + Available)
- **Collateral**: Pledge/collateral amount
- **Withdrawable**: Cash available for withdrawal

### 2. Broker vs Algo Reconciliation

Shows:
- Broker positions count (from Kite)
- Algo positions count (from PositionStore)
- **Drift Status**:
  - ✅ `MATCH` (green) - No drift
  - ⚠️ `N DRIFT` (amber/red) - Positions mismatch

### 3. Positions Table

Displays top 4 positions with:
- Instrument symbol
- Segment (EQ/F&O/CURRENCY)
- Strategy name (mapped from PositionStore)
- Quantity & Average price
- Live PnL (green/red)
- Delta (Greek)

---

## API Endpoint

### `GET /api/portfolio/snapshot`

**Response:**
```json
{
  "funds": {
    "net": 1000000.0,
    "available_cash": 500000.0,
    "withdrawable": 450000.0,
    "used_margin": 500000.0,
    "utilisation_pct": 50.0,
    "collateral": 100000.0
  },
  "positions": [
    {
      "instrument": "NIFTY26DEC25000C",
      "segment": "FNO",
      "qty": -50,
      "avg_price": 120.0,
      "last_price": 100.0,
      "pnl": -1000.0,
      "delta": 42.0,
      "gamma": 0.5,
      "vega": 0.3,
      "theta": -0.2,
      "strategy": "intraday_short_strangle_v1"
    }
  ],
  "broker_positions_count": 5,
  "algo_positions_count": 5,
  "drift_count": 0,
  "drift_details": []
}
```

---

## Usage

### Backend

The endpoint is automatically available when the API server is running:

```bash
curl http://localhost:8000/api/portfolio/snapshot
```

### Frontend

The `PortfolioPanel` component is already integrated into the main dashboard (`apps/ops-browser/app/page.tsx`). It appears in the right column.

To use it standalone:

```tsx
import { PortfolioPanel } from '@/components/portfolio/PortfolioPanel';

export default function MyPage() {
  return (
    <div>
      <PortfolioPanel />
    </div>
  );
}
```

---

## Data Flow

```
Kite API (margins, positions)
    ↓
build_portfolio_snapshot()
    ↓
FastAPI /api/portfolio/snapshot
    ↓
usePortfolio() hook
    ↓
PortfolioPanel component
    ↓
Dashboard UI
```

---

## Reconciliation Logic

The system compares:
- **Broker positions**: From `kite.positions()["net"]`
- **Algo positions**: From `position_store.get_open_positions()`

**Drift Detection:**
- Compares instrument symbols
- Reports symmetric difference (positions in broker but not algo, or vice versa)
- Shows count and details of drift

---

## Strategy Mapping

Positions are mapped to strategies using:
- `position_store.get_open_positions()` returns positions with `strategy_name`
- Strategy name is displayed in the positions table
- Unmapped positions show as "UNMAPPED"

---

## Error Handling

- **Kite API errors**: Returns empty snapshot with zero values
- **PositionStore errors**: Continues with broker-only data
- **Network errors**: Component shows error message
- **Missing data**: Graceful degradation with placeholders

---

## Future Enhancements

1. **Greeks Calculation**: Integrate actual GreeksEngine for real-time Greeks
2. **Full Positions Modal**: Click to view all positions in detail
3. **Drift Details**: Click drift badge to see which positions differ
4. **Per-Strategy PnL**: Add strategy-wise PnL breakdown
5. **Historical Charts**: Show margin utilization over time
6. **HiveMind Integration**: Let Claude analyze portfolio state

---

## Notes

- Portfolio data refreshes every 10 seconds
- All monetary values are in INR (₹)
- Greeks are currently placeholder (0.0) - needs GreeksEngine integration
- Strategy mapping requires PositionStore to have positions with strategy_name set




