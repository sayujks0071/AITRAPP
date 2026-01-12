import pandas as pd
import numpy as np
from typing import List, Dict, Any
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators
from packages.strategy_foundry.adapters.core_costs import RiskConfig

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, costs: RiskConfig):
        self.data = data
        self.costs = costs
        self.indicators = VectorizedIndicators()

    def run(self, candidate: StrategyCandidate) -> pd.DataFrame:
        """
        Run backtest for a candidate.
        Returns trades DataFrame.
        """
        df = self.data.copy()

        # 1. Calculate Indicators
        self._calculate_indicators(df, candidate)

        # 2. Generate Signals (1, -1, 0)
        # Vectorized signal generation where possible
        signals = self._generate_signals(df, candidate)

        # 3. Simulate Execution (Iterative for path dependence of stops)
        # Although vectorized is faster, path-dependent stops (trailing, ATR based on entry) require loop or numba.
        # We will use a fast loop.
        trades = self._simulate_execution(df, signals, candidate)

        return pd.DataFrame(trades)

    def _calculate_indicators(self, df: pd.DataFrame, candidate: StrategyCandidate):
        p = candidate.params
        c = df["close"].values
        h = df["high"].values
        l = df["low"].values

        # ATR always needed for risk
        df["atr"] = self.indicators.atr(h, l, c, period=p.get("sl_atr_period", 14))

        entry = candidate.entry_logic["type"]
        if entry == "trend_ema_cross":
            df["ema_fast"] = pd.Series(c).ewm(span=p["ema_fast"], adjust=False).mean()
            df["ema_slow"] = pd.Series(c).ewm(span=p["ema_slow"], adjust=False).mean()
            if p.get("adx_filter"):
                df["adx"] = self.indicators.adx(h, l, c, period=p["adx_period"])

        elif entry == "breakout_donchian":
            upper, lower = self.indicators.donchian(h, l, p["donchian_period"])
            df["donchian_upper"] = upper
            df["donchian_lower"] = lower
            if p.get("filter_ma"):
                 df["ma_filter"] = pd.Series(c).rolling(p["ma_period"]).mean()

        elif entry == "mean_rev_rsi":
            df["rsi"] = self.indicators.rsi(c, p["rsi_period"])

        elif entry == "supertrend":
            st, direction = self.indicators.supertrend(h, l, c, p["st_period"], p["st_multiplier"])
            df["supertrend"] = st
            df["supertrend_dir"] = direction

    def _generate_signals(self, df: pd.DataFrame, candidate: StrategyCandidate) -> np.ndarray:
        p = candidate.params
        entry = candidate.entry_logic["type"]

        # 0: None, 1: Long, -1: Short (optional)
        # We process entries. Exits are handled in execution loop.
        entries = np.zeros(len(df), dtype=int)

        c = df["close"].values

        if entry == "trend_ema_cross":
            # Crossover: fast > slow AND prev_fast <= prev_slow
            fast = df["ema_fast"].values
            slow = df["ema_slow"].values

            # Cross up
            long_cond = (fast > slow) & (np.roll(fast, 1) <= np.roll(slow, 1))

            if p.get("adx_filter"):
                long_cond &= (df["adx"].values > p["adx_threshold"])

            entries[long_cond] = 1

        elif entry == "breakout_donchian":
            # Close > prev upper
            # Donchian upper is max of PREVIOUS N bars usually in signal definition?
            # Or current bar breaks the level?
            # Standard: Breakout above High(N).
            # Our `donchian` calculation at `i` is max(high[i-N+1:i+1]).
            # So if close[i] > donchian[i-1].

            prev_upper = np.roll(df["donchian_upper"].values, 1)
            long_cond = c > prev_upper

            if p.get("filter_ma"):
                long_cond &= (c > df["ma_filter"].values)

            entries[long_cond] = 1

        elif entry == "mean_rev_rsi":
            # RSI < Oversold
            rsi = df["rsi"].values
            long_cond = (rsi < p["rsi_oversold"])
            entries[long_cond] = 1

        elif entry == "supertrend":
            # Direction change -1 -> 1
            st_dir = df["supertrend_dir"].values
            prev_dir = np.roll(st_dir, 1)
            long_cond = (st_dir == 1) & (prev_dir == -1)
            entries[long_cond] = 1

        return entries

    def _simulate_execution(self, df: pd.DataFrame, entry_signals: np.ndarray, candidate: StrategyCandidate) -> List[Dict]:
        """
        Bar-by-bar execution.
        Entry on Next Open.
        Exits: Stop Loss (ATR), Take Profit, EOD.
        """
        p = candidate.params

        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        atrs = df["atr"].values
        times = df.index

        trades = []
        position = 0 # 1 or 0 (Long only for now)
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        entry_time = None
        entry_idx = 0

        n = len(df)

        # Costs
        slippage = self.costs.slippage_bps / 10000.0
        tax = self.costs.tax_bps / 10000.0
        brokerage = self.costs.brokerage_per_order # Flat INR, handling this requires assuming capital.
        # We will compute return % and handle flat costs as reduction in capital if needed,
        # but here we output trade details.

        # EOD check: 15:25
        # times are pandas timestamps

        for i in range(1, n):
            current_time = times[i]

            # Check Exit if in position
            if position == 1:
                exit_price = 0.0
                exit_reason = ""

                # 1. EOD Exit
                # Assumes 5m/15m bars. If time >= 15:25, close.
                # Actually, check if current bar time is >= 15:25.
                # Market hours: 09:15-15:30.
                if current_time.hour == 15 and current_time.minute >= 25:
                    exit_price = opens[i] # Exit at Open of this bar (which is 15:25 bar?)
                    # Or exit at Close? "Flat by 15:25".
                    # If this bar starts at 15:25, we exit at Open.
                    exit_reason = "EOD"

                # 2. Stop Loss (Hit Low)
                elif lows[i] <= stop_loss:
                    exit_price = stop_loss # Assume filled at stop
                    # Slippage on stop? Yes.
                    exit_price *= (1 - slippage)
                    exit_reason = "SL"

                # 3. Take Profit (Hit High)
                elif take_profit > 0 and highs[i] >= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"

                # Execute Exit
                if exit_price > 0:
                    # Calculate PnL
                    # Gross Return
                    gross_ret = (exit_price - entry_price) / entry_price

                    # Apply Costs
                    # Slippage on entry (already applied below) and exit?
                    # We applied slippage on SL exit above.
                    # If EOD/TP, apply slippage.
                    if exit_reason != "SL":
                        exit_price *= (1 - slippage)

                    # Recalculate gross with exit slippage
                    gross_ret = (exit_price - entry_price) / entry_price

                    # Tax
                    # Approx turnover tax
                    # We will store net return

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return": gross_ret,
                        "reason": exit_reason
                    })

                    position = 0
                    continue

            # Check Entry
            # Signal from previous bar (i-1) triggers entry on Open (i)
            # If flat
            if position == 0:
                if entry_signals[i-1] == 1:
                    # Check spread/chop? (Spread guard)
                    # Skip if High-Low is too small? (Optional)

                    # Enter Long
                    entry_price = opens[i] * (1 + slippage) # Buy slippage
                    position = 1
                    entry_time = current_time
                    entry_idx = i

                    # Set Stops
                    atr_val = atrs[i-1] # Use previous ATR
                    if np.isnan(atr_val) or atr_val == 0:
                         atr_val = opens[i] * 0.01 # Fallback 1%

                    sl_dist = atr_val * p["sl_atr_mult"]
                    stop_loss = entry_price - sl_dist

                    if "tp_risk_reward" in p:
                        tp_dist = sl_dist * p["tp_risk_reward"]
                        take_profit = entry_price + tp_dist
                    else:
                        take_profit = 0.0

        return trades
