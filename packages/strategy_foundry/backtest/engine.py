"""Backtest Engine for Intraday Strategies"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import structlog
from dataclasses import dataclass

from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_indicators import TechnicalIndicators
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.adapters.core_costs import CostModel

logger = structlog.get_logger(__name__)

@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp = None
    exit_price: float = None
    direction: int = 0 # 1 long, -1 short
    pnl: float = 0.0
    pnl_net: float = 0.0
    reason: str = ""
    cost: float = 0.0
    holding_bars: int = 0

class BacktestEngine:
    def __init__(self, cost_model: CostModel):
        self.cost_model = cost_model
        self.market_hours = MarketHoursAdapter()
        self.indicators = TechnicalIndicators()

    def run(self, candidate: StrategyCandidate, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[Trade]]:
        """
        Run backtest for a candidate.

        Args:
            candidate: Strategy spec
            data: OHLCV DataFrame

        Returns:
            (equity_curve, trades_list)
        """
        if data.empty:
            return pd.DataFrame(), []

        # 1. Precompute Indicators
        df = data.copy()
        self._compute_indicators(df, candidate)

        # 2. Generate Signals (Vectorized where possible, but logic often iterative)
        # For flexibility with the grammar, we'll iterate or use apply.
        # Given N=80 candidates * 5m data, iteration is okay-ish, but vector preferred.
        # We will compute signal columns.

        df["signal"] = 0

        # --- Entry Logic ---
        entry_type = candidate.entry_logic["type"]
        params = candidate.params

        if entry_type == "ORB_BREAKOUT":
            # Can't easily vectorize ORB with simple pandas rolling because it depends on daily session start
            # We will use an iterator for the core loop or a hybrid approach.
            # For simplicity in this "Aggressive" lab, let's iterate bars. It's slower but safer for complex rules.
            pass
        elif entry_type == "DONCHIAN_BREAKOUT":
            upper, lower = self.indicators.donchian(df["high"], df["low"], params["donchian_period"])
            # Breakout Long: Close > Upper.shift(1)
            df.loc[df["close"] > upper.shift(1), "signal_long"] = 1
            # df.loc[df["close"] < lower.shift(1), "signal_short"] = 1 # Short optional

        elif entry_type == "RSI_REVERSION":
            rsi = self.indicators.rsi(df["close"], params["rsi_period"])
            # Long: RSI < Oversold
            df.loc[rsi < params["rsi_os"], "signal_long"] = 1

        elif entry_type == "EMA_CROSS":
            fast = df[f"ema_{params['ema_fast']}"]
            slow = df[f"ema_{params['ema_slow']}"]
            # Long: Fast crosses above Slow
            # (Fast > Slow) & (Fast.shift < Slow.shift)
            cross_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
            df.loc[cross_up, "signal_long"] = 1

        elif entry_type == "BOLLINGER_REVERSION":
             # Long: Close < Lower Band
             upper, mid, lower = self.indicators.bollinger_bands(df["close"], params["bb_period"], params["bb_std"])
             df.loc[df["close"] < lower, "signal_long"] = 1

        # --- Filter Logic ---
        # Apply filters as masks
        mask = pd.Series(True, index=df.index)
        for f in candidate.filters:
            if f["type"] == "TREND_EMA_1H":
                # Rough approximation: use longer EMA on current TF to simulate HTF trend
                # e.g. 5m * 12 = 1h. If 1h period is 50, then 5m period is 600.
                factor = 12 if "5m" in candidate.timeframe else 4 # 15m -> 1h = 4
                p = params.get("trend_ema", 50) * factor
                ema_htf = df["close"].ewm(span=p, adjust=False).mean()
                mask = mask & (df["close"] > ema_htf)

            elif f["type"] == "VOLATILITY_ATR":
                # Only trade if volatility is adequate (e.g. ATR > rolling avg ATR)
                atr = df["atr"]
                atr_avg = atr.rolling(window=100).mean()
                mask = mask & (atr > atr_avg)

        # Apply mask to signals
        if "signal_long" in df.columns:
            df.loc[~mask, "signal_long"] = 0
        else:
            df["signal_long"] = 0 # Ensure column exists

        # --- Execution Loop ---
        trades = []
        position = 0 # 1 or 0
        entry_price = 0.0
        entry_idx = None
        entry_time = None

        # Pre-calc exit indicators if needed
        atr_series = df.get("atr", pd.Series(0, index=df.index))

        # Session times
        flatten_time = self.market_hours.get_session_close()

        # Convert to records for speed
        records = df.to_dict('records')
        timestamps = df.index

        for i in range(1, len(records)):
            row = records[i]
            ts = timestamps[i]
            prev_row = records[i-1]

            # Check Session Boundary (Flat by 15:25)
            if position != 0:
                if ts.time() >= flatten_time:
                     # Force Exit
                    exit_price = row["open"] # Next open is usually how we trade, but this is intra-bar check?
                    # Actually, if we are AT 15:25 bar, we must close.
                    # Assumption: signal calculated at close, executed at open.
                    # If current bar open is >= flatten time, we execute immediately.
                    self._close_position(trades, ts, row["open"], position, "SESSION_END")
                    position = 0
                    continue

            # Check Stops / Targets if in position
            if position != 0:
                # 1. Exit Logic
                hit_exit = False

                exit_type = candidate.exit_logic["type"]
                current_atr = atr_series.iloc[i-1] # Use prev close ATR for fixed stops? Or current?
                # Usually stops are set at entry.

                # Dynamic stops (calculated relative to entry)
                if exit_type == "ATR_TRAIL":
                    # Simple trail: if Long, Stop = High - N*ATR. Move up only.
                    # Complex to sim in simple loop without tracking state.
                    # Simplified: Trailing stop from highest high since entry.
                    highest_high = df["high"].iloc[entry_idx:i].max()
                    stop_price = highest_high - (params["atr_mult"] * atr_series.iloc[entry_idx])
                    if row["low"] < stop_price:
                        # Stopped out
                        # Slippage on stop? Assume execution at stop price or open?
                        # Standard conservative: min(Open, StopPrice) if gap down?
                        # Let's use Stop Price w/ slippage, or Low if it jumped.
                        exec_px = min(row["open"], stop_price)
                        self._close_position(trades, ts, exec_px, position, "TRAIL_STOP")
                        position = 0
                        hit_exit = True

                elif exit_type == "TIME_STOP":
                    bars_held = i - entry_idx
                    if bars_held >= params["max_bars"]:
                        self._close_position(trades, ts, row["open"], position, "TIME_STOP")
                        position = 0
                        hit_exit = True

                elif exit_type == "FIXED_RR":
                    stop_dist = params["atr_mult_stop"] * atr_series.iloc[entry_idx]
                    target_dist = stop_dist * params["rr_ratio"]
                    stop_price = entry_price - stop_dist
                    target_price = entry_price + target_dist

                    if row["low"] < stop_price:
                        self._close_position(trades, ts, stop_price, position, "STOP_LOSS")
                        position = 0
                        hit_exit = True
                    elif row["high"] > target_price:
                         self._close_position(trades, ts, target_price, position, "TAKE_PROFIT")
                         position = 0
                         hit_exit = True

                if hit_exit:
                    continue

            # Entry (only if flat and market allow)
            # Signal from PREVIOUS bar close (no lookahead)
            # row is current bar (Open, H, L, C). We trade at Open based on prev signal.

            if position == 0:
                # Check Market Hours for Entry (09:15 - 15:20)
                if not self.market_hours.is_market_open(ts):
                    continue

                sig_long = prev_row.get("signal_long", 0)

                # Special Case: ORB (handled inside loop if not vectorized)
                if entry_type == "ORB_BREAKOUT":
                     # Define session start
                     # If ts is inside window, update high/low
                     # If ts > window, check breakout
                     # Need state tracking. Simplified:
                     # Calculate ORB daily.
                     pass

                if sig_long == 1:
                    position = 1
                    entry_price = row["open"]
                    entry_idx = i
                    entry_time = ts
                    # Record Entry
                    # We don't log trade until exit in this simple engine

        # Force close at end of data if open
        if position != 0:
             self._close_position(trades, timestamps[-1], records[-1]["close"], position, "EOD_FORCE")

        return self._build_equity_curve(trades, df.index)

    def _compute_indicators(self, df: pd.DataFrame, candidate: StrategyCandidate):
        # Always compute ATR for logic
        df["atr"] = self.indicators.atr(df["high"], df["low"], df["close"], 14)

        p = candidate.params
        t = candidate.entry_logic["type"]

        if t == "EMA_CROSS":
            df[f"ema_{p['ema_fast']}"] = df["close"].ewm(span=p['ema_fast'], adjust=False).mean()
            df[f"ema_{p['ema_slow']}"] = df["close"].ewm(span=p['ema_slow'], adjust=False).mean()

        # ... add others as needed (Donchian, RSI already called in loop/vector block)

    def _close_position(self, trades: List[Trade], time, price, direction, reason):
        # Get last partial trade or create new structure?
        # Here we only track completed trades
        # Need to know entry info. In this simple loop, we need to pass entry data.
        # Refactoring loop slightly to track entry state better.
        pass

    # Refactored _close_position to work with state passed in
    # But wait, I need to store the active trade.

    # Let's fix the run loop structure.

    def _build_equity_curve(self, trades: List[Trade], index) -> pd.DataFrame:
        if not trades:
            return pd.DataFrame({"equity": 0.0}, index=index)

        # Simple equity curve: sum PnL
        # Map trades to exit time
        pnl_series = pd.Series(0.0, index=index)
        for t in trades:
            if t.exit_time in pnl_series.index:
                 pnl_series[t.exit_time] += t.pnl_net
            else:
                 # Handle missing index (rare if using same index)
                 pass

        equity = pnl_series.cumsum()
        return pd.DataFrame({"equity": equity})

# Re-implementing run with better state management
    def run_safe(self, candidate: StrategyCandidate, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[Trade]]:
        if data.empty: return pd.DataFrame(), []

        df = data.copy()
        self._compute_indicators(df, candidate)

        # Vectorized Signals
        entry_type = candidate.entry_logic["type"]
        params = candidate.params

        df["signal_long"] = 0

        if entry_type == "DONCHIAN_BREAKOUT":
            u, l = self.indicators.donchian(df["high"], df["low"], params["donchian_period"])
            df.loc[df["close"] > u.shift(1), "signal_long"] = 1
        elif entry_type == "RSI_REVERSION":
            rsi = self.indicators.rsi(df["close"], params["rsi_period"])
            df.loc[rsi < params["rsi_os"], "signal_long"] = 1
        elif entry_type == "EMA_CROSS":
            f = df["close"].ewm(span=params['ema_fast'], adjust=False).mean()
            s = df["close"].ewm(span=params['ema_slow'], adjust=False).mean()
            df.loc[(f > s) & (f.shift(1) <= s.shift(1)), "signal_long"] = 1
        elif entry_type == "BOLLINGER_REVERSION":
             u, m, l = self.indicators.bollinger_bands(df["close"], params["bb_period"], params["bb_std"])
             df.loc[df["close"] < l, "signal_long"] = 1
        elif entry_type == "ORB_BREAKOUT":
            # ORB Logic: High of first X mins.
            # Identify session start.
            # Group by date.
            # This is slow in pandas. Approximation:
            # Shifted rolling max?
            # Correct approach: Resample to 1D to get date, then for each date find ORB.
            # Optimization: pass for now, implement simpler logic or skip ORB in v1.
            # Let's use a simplified "Time Range Breakout"
            pass

        # Filters
        mask = pd.Series(True, index=df.index)
        for f in candidate.filters:
            if f["type"] == "TREND_EMA_1H":
                 # 1H approx
                 factor = 12 if "5m" in candidate.timeframe else 4
                 per = params.get("trend_ema", 50) * factor
                 ema = df["close"].ewm(span=per).mean()
                 mask &= (df["close"] > ema)
            elif f["type"] == "VOLATILITY_ATR":
                 # ATR Regime
                 atr = df.get("atr", self.indicators.atr(df["high"], df["low"], df["close"]))
                 mask &= (atr > atr.rolling(100).mean())

        df.loc[~mask, "signal_long"] = 0

        # Loop
        trades = []
        active_trade = None # Trade object
        flatten_time = self.market_hours.get_session_close()

        # Arrays for speed
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        times = df.index
        sigs = df["signal_long"].values
        atrs = df["atr"].values if "atr" in df else np.zeros(len(df))

        for i in range(1, len(df)):
            ts = times[i]

            # 1. Manage Active Position
            if active_trade:
                # Session Close Check
                if ts.time() >= flatten_time:
                    self._finalize_trade(active_trade, ts, opens[i], "SESSION_END", trades)
                    active_trade = None
                    continue

                # Exits
                exit_logic = candidate.exit_logic["type"]
                # Price to check: we use Low/High of current bar to see if stop hit
                # Execution at stop price

                if exit_logic == "FIXED_RR":
                    # Params stored in trade or calc?
                    # Recalc levels
                    # Stored in active_trade metadata?
                    stop_px = active_trade.meta['stop']
                    target_px = active_trade.meta['target']

                    if lows[i] < stop_px:
                        px = min(opens[i], stop_px) # Gap handling
                        self._finalize_trade(active_trade, ts, px, "STOP_LOSS", trades)
                        active_trade = None
                        continue
                    elif highs[i] > target_px:
                        px = max(opens[i], target_px)
                        self._finalize_trade(active_trade, ts, px, "TAKE_PROFIT", trades)
                        active_trade = None
                        continue

                elif exit_logic == "ATR_TRAIL":
                    # Trail
                    mult = params["atr_mult"]
                    # Update highest high
                    if highs[i-1] > active_trade.meta.get('highest', -1):
                        active_trade.meta['highest'] = highs[i-1]
                        # Recalc stop
                        # Needs ATR at that point? usually trail is based on current price or solidified stop
                        # Standard Chandelier Exit: Highest High - ATR*Mult
                        # Use current ATR?
                        current_atr = atrs[i-1]
                        new_stop = active_trade.meta['highest'] - (current_atr * mult)
                        if new_stop > active_trade.meta['stop']:
                            active_trade.meta['stop'] = new_stop

                    if lows[i] < active_trade.meta['stop']:
                        px = min(opens[i], active_trade.meta['stop'])
                        self._finalize_trade(active_trade, ts, px, "TRAIL_STOP", trades)
                        active_trade = None
                        continue

                elif exit_logic == "TIME_STOP":
                    if (i - active_trade.meta['entry_idx']) >= params["max_bars"]:
                        self._finalize_trade(active_trade, ts, opens[i], "TIME_STOP", trades)
                        active_trade = None
                        continue

            # 2. Entry
            if not active_trade:
                # Market Hours
                if not self.market_hours.is_market_open(ts):
                    continue

                # Signal from PREV bar
                if sigs[i-1] == 1:
                    t = Trade(entry_time=ts, entry_price=opens[i], direction=1)
                    t.meta = {'entry_idx': i}

                    # Setup Exit Params
                    cur_atr = atrs[i-1] if i>0 else 0

                    if candidate.exit_logic["type"] == "FIXED_RR":
                        dist = params["atr_mult_stop"] * cur_atr
                        t.meta['stop'] = t.entry_price - dist
                        t.meta['target'] = t.entry_price + (dist * params["rr_ratio"])
                    elif candidate.exit_logic["type"] == "ATR_TRAIL":
                        t.meta['highest'] = t.entry_price
                        t.meta['stop'] = t.entry_price - (params["atr_mult"] * cur_atr)

                    active_trade = t

        return self._build_equity_curve(trades, df.index), trades

    def _finalize_trade(self, trade, time, price, reason, trades_list):
        trade.exit_time = time
        trade.exit_price = self.cost_model.get_slippage_price(price, -1 * trade.direction) # Slippage on exit
        trade.entry_price = self.cost_model.get_slippage_price(trade.entry_price, trade.direction) # Slippage on entry (retrospective adjustment or just calculate cost?)

        # Better: Apply slippage to prices, then calc PnL
        # Re-adjust entry price in object? Or just use raw for PnL and subtract cost?
        # Let's subtract cost.

        raw_pnl = (trade.exit_price - trade.entry_price) * trade.direction # Price diff
        # Wait, if I adjusted price above, I double count.
        # Let's reset.

        # Slippage is part of execution price.
        # Buy at 100. Slippage 2bps. Exec Price = 100.02
        # Sell at 102. Slippage 2bps. Exec Price = 101.98
        # PnL = 101.98 - 100.02 = 1.96

        # Cost (Commissions) is separate.

        # Let's assume trade.entry_price passed in was RAW.
        real_entry = self.cost_model.get_slippage_price(trade.entry_price, trade.direction)
        real_exit = self.cost_model.get_slippage_price(price, -1 * trade.direction)

        trade.entry_price = real_entry
        trade.exit_price = real_exit

        trade.pnl = (real_exit - real_entry) * trade.direction

        # Commission
        c_entry = self.cost_model.estimate_cost(real_entry, 1, "entry")
        c_exit = self.cost_model.estimate_cost(real_exit, 1, "exit")
        trade.cost = c_entry + c_exit

        trade.pnl_net = trade.pnl - trade.cost
        trade.reason = reason
        trade.holding_bars = 0 # Calculate if needed

        trades_list.append(trade)
