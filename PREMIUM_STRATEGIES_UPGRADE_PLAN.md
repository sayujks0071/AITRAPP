# Premium Strategies Upgrade Plan - Day-4+

## Overview

This document outlines the upgrade plan for premium trading strategies, starting with `expiry_short_strangle_v2` as the foundation.

---

## 1️⃣ Expiry Short Strangle V2 (Core Weekly Income Engine)

### Status: 🚧 **TO BE IMPLEMENTED**

### Key Upgrades from V1

1. **Regime-Aware Entry**
   - Strict R1 regime gating: Only `LOW_MEAN_REVERT` or `MEDIUM_TREND`
   - Block in `HIGH_EVENT` or `CHAOTIC`

2. **Delta-Based Strike Selection**
   - Target absolute delta: **0.18-0.22** (not just "~0.2 by feel")
   - Use actual option delta from market data

3. **IV + Realized Vol Filter**
   - IV percentile: **40-85**
   - 5-10 day realized vol < IV (getting paid more than realized)

4. **Move/ATR Filter**
   - Block if intraday move from open > **1.5× ATR(1d)**
   - Don't sell into runaway trends

5. **Tight Time Gate**
   - Entry window: **10:15-12:00** IST
   - No fresh entries after 12:00

6. **Hard Linkage to H1**
   - Always allocate **10-15%** of premium collected to tail hedges
   - Automatic tail deployment via H1 overlay

### Implementation Files

- **Strategy Class:** `packages/core/strategies/expiry_short_strangle_v2.py`
- **Config:** `configs/expiry_short_strangle_v2.yaml`
- **Integration:** Update `apps/api/main.py` to instantiate strategy

---

## 2️⃣ Intraday Short Strangle V1 (Scalper)

### Status: 📋 **PLANNED**

### Structure
- 1× intraday strangle, NIFTY only, 1 lot
- H1 tails active (cheaper, intraday only)

### Entry Conditions
- Time window: **11:00-13:30** IST
- R1 regime: `LOW_MEAN_REVERT` + low intraday realized vol (<0.5-0.6%)
- No major events (E1 check)

### Exits
- Time-based: Force exit by **15:00**
- Loss cut: 1.5× net premium
- Profit: 40-50% premium decay

### Allocator
- Cap: **5-10%** of risk budget
- Daily limit: **₹3k-₹5k** max loss

---

## 3️⃣ Credit Spreads

### 3.1 Drifting Credit Spread (Trend-Following)

**Status:** 📋 **PLANNED**

**Idea:** Sell put credit spreads in uptrends, call credit spreads in downtrends

**Entry:**
- R1 regime: `MEDIUM_TREND` with directional bias
- Trend filter: EMA34 > EMA89 + price > VWAP (bullish)

**Structure:**
- Put credit spread: Sell 0.25Δ put, Buy 0.10Δ lower strike put
- Risk bounded from start

**Risk:**
- Max loss: Width of spread - credit
- SL: 60-70% of max loss
- Size: 1 spread, **₹3k-₹5k** max risk

### 3.2 VScore Credit Spread (Vol Score Based)

**Status:** 📋 **PLANNED**

**Idea:** Only sell when IV is clearly overpriced vs realized

**Formula:**
```
vscore = (IV - RealizedVol) / RealizedVol
```

**Entry:**
- Only when `vscore > threshold` (e.g., > +0.3)
- Never trade when IV is cheap or fairly priced

---

## 4️⃣ Dispersion Arb Repositioning

### Status: 📋 **PLANNED**

**New Role:** Premium hedge & alpha

**Strategy:**
- Long index vol, short single-name vol (or vice versa)
- Keep low weight, mostly long-gamma/long-vega
- Natural hedge for short index premium book

**Trigger:**
- When short index premium notional > X
- D1 opens small long straddle/calendar on correlated sector

**Allocator:**
- Cap: **5-10%** of risk budget
- Position size: Similar risk to one debit spread

---

## 5️⃣ Implementation Phases

### Phase A (Current - Day-4)
- ✅ OptionsRanker (debit spreads) - primary
- ✅ expiry_short_strangle (basic) - very small
- ✅ R1, H1 live; others tiny or shadow

### Phase B (Next Few Days)
- 🚧 **expiry_short_strangle_v2** (upgraded weekly engine)
- 🚧 intraday_short_strangle_v1 (tiny risk, 1 lot, 1 trade/day max)
- 🚧 drifting_credit_spread (one-direction only: bullish put spreads)

### Phase C (After ≥20-30 live trades)
- 📋 vscore_credit_spread (small size)
- 📋 D1 long-gamma/long-vega overlays
- 📋 StatsEngine + MCP ranking
- 📋 Weekly allocator rebalancing

---

## Next Steps

1. **Implement expiry_short_strangle_v2** (this document)
2. Create strategy class with all v2 filters
3. Wire into main.py
4. Add Prometheus metrics for filter rejections
5. Test with paper trading
6. Promote to tiny live size

---

**Last Updated:** 2025-11-19  
**Status:** Ready for implementation

