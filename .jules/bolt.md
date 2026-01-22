# Bolt's Journal

## 2025-02-23 - [Supertrend Optimization] **Learning:** Python loops are slow for recursive indicators. **Action:** Optimize inner loop.

## 2025-02-23 - [Backtest Loop Optimization] **Learning:** Updating pandas Series row-by-row (`iloc`) and repeated attribute access (e.g., `dt.hour`) inside a hot loop is a major bottleneck. **Action:** Use numpy arrays for mutable state and pre-compute invariants before the loop.

## 2026-01-21 - [Foundry Backtest Vectorization] **Learning:** Removing per-tick array assignments and reconstructing equity curve via vectorized cumsum/roll reduced runtime by ~50%. **Action:** Identify other path-dependent loops that can be reconstructed vectorially.
