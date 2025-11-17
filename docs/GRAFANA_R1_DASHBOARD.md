# Grafana Dashboard: Vol Regime & Performance

## Dashboard Overview

This dashboard monitors the R1 Regime-Switching Volatility Engine, showing current regimes, feature values, and performance metrics.

## Panels

### 1. Current Regime (Stat Panel)

**Query:**
```promql
last_over_time(algo_vol_regime_code{underlying="NIFTY"}[5m])
```

**Value Mappings:**
- 0 → "UNKNOWN" (grey)
- 1 → "LOW_MEAN_REVERT" (green)
- 2 → "MEDIUM_TREND" (blue)
- 3 → "HIGH_EVENT" (orange)
- 4 → "CHAOTIC" (red)

**Repeat for:** BANKNIFTY

---

### 2. Regime Over Time (Time-series)

**Query:**
```promql
algo_vol_regime_code{underlying="NIFTY"}
```

**Display:** Stepped line chart
**Y-axis:** 0-4 (regime codes)
**Legend:** Show underlying

**Helps you see:** When the engine switched regimes intraday

---

### 3. IV Rank vs Thresholds (Time-series)

**Query:**
```promql
algo_vol_iv_rank{underlying="NIFTY"}
```

**Thresholds (Grafana "Thresholds"):**
- `low_iv_rank` = 0.25 (yellow line)
- `high_iv_rank` = 0.65 (red line)

**Display:** Line chart with threshold markers

**Helps you see:** When regime boundaries are crossed

---

### 4. ATR% vs Thresholds (Time-series)

**Query:**
```promql
algo_vol_atr_pct{underlying="NIFTY"}
```

**Thresholds:**
- `atr_pct_low` = 0.40 (yellow line)
- `atr_pct_high` = 1.50 (red line)

**Display:** Line chart with threshold markers

---

### 5. Time Spent in Each Regime (Bar/Pie Chart)

**Query:**
```promql
avg_over_time(algo_vol_regime_flag{underlying="NIFTY"}[30d])
```

**Group by:** `regime` label

**Display:** Bar chart or pie chart

**Shows:** Fraction of time spent in each regime over last 30 days

---

### 6. Realized PnL by Regime (Bar Chart)

**Query:**
```promql
sum(increase(algo_pnl_realized{underlying="NIFTY"}[30d])) by (regime)
```

**Display:** Bar chart grouped by regime

**Shows:** Which regime is actually paying you

**Note:** Requires wiring `algo_pnl_realized` counter on position close (see below)

---

### 7. Trades Executed per Regime (Bar Chart)

**Query:**
```promql
sum(increase(algo_trades_executed{underlying="NIFTY"}[30d])) by (regime)
```

**Display:** Bar chart

**Shows:** Sample size per regime (cross-check with PnL)

**Note:** Requires adding `algo_trades_executed` counter (see below)

---

### 8. Feature Dashboard (Multi-panel)

**Panel 1: RV/IV Ratio**
```promql
algo_vol_rv_iv_ratio{underlying="NIFTY"}
```

**Panel 2: VIX Rank**
```promql
algo_vol_vix_rank{underlying="NIFTY"}
```

**Panel 3: All Features Overlay**
```promql
algo_vol_iv_rank{underlying="NIFTY"}
algo_vol_atr_pct{underlying="NIFTY"}
algo_vol_rv_iv_ratio{underlying="NIFTY"}
algo_vol_vix_rank{underlying="NIFTY"}
```

**Display:** Multi-series line chart

---

## Additional Metrics to Wire

### PnL Tracking

When a position closes, record the PnL with regime tag:

```python
# In your position close handler
if hasattr(position, 'entry_regime') and position.entry_regime:
    metrics.counter(
        "algo_pnl_realized",
        labels={"underlying": underlying, "regime": position.entry_regime}
    ).inc(pnl_value)
```

### Trade Execution Counter

When a trade is executed, increment:

```python
# In your order fill handler
if signal.features and signal.features.get("entry_regime"):
    metrics.counter(
        "algo_trades_executed",
        labels={"underlying": underlying, "regime": signal.features["entry_regime"]}
    ).inc(1)
```

---

## Dashboard JSON Export

To create the dashboard in Grafana:

1. Go to Grafana → Dashboards → New Dashboard
2. Add panels using the queries above
3. Configure value mappings for regime codes
4. Set up thresholds for feature panels
5. Export as JSON for sharing

---

## Quick Reference

**Metrics Prefix:** `algo_vol_*`

**Key Labels:**
- `underlying`: NIFTY, BANKNIFTY
- `regime`: LOW_MEAN_REVERT, MEDIUM_TREND, HIGH_EVENT, CHAOTIC, UNKNOWN

**Regime Codes:**
- 0 = UNKNOWN
- 1 = LOW_MEAN_REVERT
- 2 = MEDIUM_TREND
- 3 = HIGH_EVENT
- 4 = CHAOTIC


