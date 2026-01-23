import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate, EntryType, RiskType, FilterType
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.backtest.metrics import calculate_metrics

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, cost_bps: float = 2.0, slippage_bps: float = 3.0):
        self.initial_capital = initial_capital
        self.cost_bps = cost_bps
        self.slippage_bps = slippage_bps
        self.total_cost_bps = cost_bps + slippage_bps
        self.market_hours = MarketHoursAdapter()
        self.indicator_calc = IndicatorsAdapter()

    def run(self, candidate: StrategyCandidate, data: pd.DataFrame, timeframe: str = "5m") -> Dict:
        """
        Run backtest for a single candidate on data.

        Args:
            candidate: StrategyCandidate object
            data: DataFrame with open, high, low, close, volume (datetime index)
            timeframe: "5m", "15m", "1D"

        Returns:
            Dict with equity curve, trades, metrics
        """
        if data.empty:
            return {}

        # 1. Pre-calculate Indicators & Signals
        # -------------------------------------
        df = data.copy()
        indicators = self._calculate_indicators(df, candidate)

        # Calculate Signals (Vectorized)
        # 1 = Long Entry, 0 = No Signal
        # (Shorts not supported in default grammar yet, but flexible)
        entry_signals = self._generate_entry_signals(df, indicators, candidate)

        # 2. Prepare Loop Variables
        # -------------------------
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        times = df.index

        # Market Hours Masks
        is_open, is_session_start, is_session_end = self.market_hours.get_masks(df.index)

        # State
        position = 0 # 0, 1 (Long), -1 (Short)
        entry_price = 0.0
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0
        highest_high = 0.0 # For trailing stop

        equity = [self.initial_capital] * len(df)
        cash = self.initial_capital
        trades = []

        # Exit Params
        risk_params = candidate.exit.params
        atr_period = risk_params.get("atr_period", 14)
        atr_values = indicators.get(f"atr_{atr_period}")
        stop_mult = risk_params.get("stop_mult", 2.0)
        tp_mult = risk_params.get("tp_mult", 0.0)
        trail = risk_params.get("trail", False)

        # 3. Execution Loop
        # -----------------
        # Tracking Variables
        current_equity = self.initial_capital
        qty = 0.0

        # Iterate from 1 to N-1
        for i in range(1, len(df)):
            current_time = times[i]
            prev_equity = equity[i-1]

            # --- A. Check Exits (if Position exists) ---
            if position != 0:
                exit_price = 0.0
                exit_reason = ""

                # 1. EOD Exit / Session End
                if is_session_end[i]:
                    exit_price = opens[i]
                    exit_reason = "EOD"

                # 2. Stop Loss / Take Profit / Trailing
                else:
                    # Update Trailing Stop (Chandelier-like)
                    if trail and position > 0:
                        if highs[i] > highest_high:
                            highest_high = highs[i]
                            if atr_values is not None:
                                current_atr = atr_values[i-1]
                                new_sl = highest_high - (current_atr * stop_mult)
                                stop_loss = max(stop_loss, new_sl)

                    # Check SL/TP
                    if position > 0:
                        if opens[i] <= stop_loss:
                            exit_price = opens[i]
                            exit_reason = "SL_GAP"
                        elif lows[i] <= stop_loss:
                            exit_price = stop_loss
                            exit_reason = "SL"
                        elif tp_mult > 0 and take_profit > 0:
                            if opens[i] >= take_profit:
                                exit_price = opens[i]
                                exit_reason = "TP_GAP"
                            elif highs[i] >= take_profit:
                                exit_price = take_profit
                                exit_reason = "TP"

                # Execute Exit
                if exit_price > 0:
                    # Calculate PnL
                    # Cost: entry_price * bps + exit_price * bps
                    entry_cost = entry_price * (self.total_cost_bps / 10000.0)
                    exit_cost = exit_price * (self.total_cost_bps / 10000.0)

                    gross_pnl_per_share = (exit_price - entry_price)
                    net_pnl_per_share = gross_pnl_per_share - entry_cost - exit_cost

                    trade_pnl = qty * net_pnl_per_share

                    current_equity = current_equity + trade_pnl

                    trades.append({
                        "entry_time": times[entry_idx],
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "qty": qty,
                        "pnl": trade_pnl,
                        "pnl_net": trade_pnl, # Same as pnl here
                        "reason": exit_reason
                    })

                    position = 0
                    qty = 0.0
                    entry_price = 0.0
                    highest_high = 0.0

            # --- B. Check Entries (if Flat) ---
            if position == 0:
                # Signal from PREVIOUS close (i-1) executed at Open[i]
                if is_open[i] and entry_signals[i-1]:
                    entry_price = opens[i]
                    position = 1
                    entry_idx = i
                    highest_high = highs[i]

                    # Sizing: Use 100% equity (1x leverage)
                    qty = current_equity / entry_price

                    # Setup Risk
                    atr = atr_values[i-1] if atr_values is not None else entry_price * 0.01
                    stop_loss = entry_price - (atr * stop_mult)
                    if tp_mult > 0:
                        take_profit = entry_price + (atr * tp_mult)
                    else:
                        take_profit = 0.0

            # --- C. Update Equity Curve ---
            if position != 0:
                # Mark to Market
                # Equity = Cash + Position Value
                # But we tracked current_equity as realized.
                # MTM Equity = Realized Equity at entry - Entry Cost + Unrealized PnL

                # Let's simplify: Equity = Qty * CurrentPrice + (Cash Reserve)
                # At Entry: Cash Reserve = Equity - (Qty * EntryPrice) - EntryCost
                # This is tricky with loop var `current_equity`.

                # Let's use:
                # Equity[i] = StartEquity + Sum(Realized PnL) + Unrealized PnL

                # Unrealized PnL = Qty * (Close[i] - EntryPrice) - ExitCost(Approx)
                # We won't deduct exit cost in MTM usually, or we can.

                unrealized_gross = qty * (closes[i] - entry_price)
                # Entry cost was already "paid" implicitly in our tracking?
                # No, in logic above `current_equity` is only updated on Exit.
                # So `current_equity` holds the equity *before* the current open trade (minus previous losses/gains).

                # So MTM = current_equity + unrealized_gross - entry_cost
                entry_cost = qty * entry_price * (self.total_cost_bps / 10000.0)
                equity[i] = current_equity + unrealized_gross - entry_cost

            else:
                equity[i] = current_equity

        open_position = None
        if position != 0:
            open_position = {
                "entry_time": times[entry_idx],
                "entry_price": entry_price,
                "qty": qty,
                "current_price": closes[-1],
                "pnl_unrealized": (closes[-1] - entry_price) * qty, # Approx
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "side": "LONG" if position > 0 else "SHORT"
            }

        return self._finalize_results(equity, trades, df.index, open_position)

    def _calculate_indicators(self, df: pd.DataFrame, candidate: StrategyCandidate) -> Dict[str, np.ndarray]:
        indicators = {}

        # Entry Params
        ep = candidate.entry.params
        et = candidate.entry.type

        if et == EntryType.BREAKOUT:
            period = ep.get("period", 20)
            up, low = self.indicator_calc.donchian_series(df, period)
            indicators[f"donchian_high_{period}"] = up
            indicators[f"donchian_low_{period}"] = low

        elif et == EntryType.TREND:
            fast = ep.get("fast_period", 9)
            slow = ep.get("slow_period", 20)
            indicators[f"ema_{fast}"] = self.indicator_calc.ema_series(df["close"], fast)
            indicators[f"ema_{slow}"] = self.indicator_calc.ema_series(df["close"], slow)

        elif et == EntryType.MEAN_REVERSION:
            rsi_p = ep.get("rsi_period", 14)
            indicators[f"rsi_{rsi_p}"] = self.indicator_calc.rsi_series(df) # returns numpy array

        # Exit Params
        rp = candidate.exit.params
        atr_p = rp.get("atr_period", 14)
        indicators[f"atr_{atr_p}"] = self.indicator_calc.atr_series(df) # returns numpy array

        # Filters
        for f in candidate.filters:
            if f.type == FilterType.REGIME_MA:
                p = f.params.get("period", 200)
                indicators[f"ma_{p}"] = self.indicator_calc.ema_series(df["close"], p) # returns series

        return indicators

    def _generate_entry_signals(self, df: pd.DataFrame, indicators: Dict, candidate: StrategyCandidate) -> np.ndarray:
        signals = np.zeros(len(df), dtype=bool)
        close = df["close"].values

        # 1. Base Signal
        et = candidate.entry.type
        ep = candidate.entry.params

        if et == EntryType.BREAKOUT:
            p = ep.get("period", 20)
            # Breakout: Close > Donchian High of prev bar?
            # Usually Donchian High includes current bar if calculated on High.
            # So if Close > DonchianHigh[i-1].
            # IndicatorCalculator.donchian_series uses rolling max of High.
            # So donchian_high[i] = max(High[i-p+1]...High[i]).
            # We want to check if Close[i] > Max(High[i-p]...High[i-1]).
            # So shift by 1.
            donchian = indicators[f"donchian_high_{p}"].shift(1).fillna(np.inf) # Pandas Series
            # Ensure numpy
            base_signal = close > donchian.values

        elif et == EntryType.TREND:
            fast = indicators[f"ema_{ep.get('fast_period', 9)}"]
            slow = indicators[f"ema_{ep.get('slow_period', 20)}"]
            # Cross: Fast > Slow
            base_signal = (fast > slow).values & (fast.shift(1) <= slow.shift(1)).values

        elif et == EntryType.MEAN_REVERSION:
            rsi = indicators[f"rsi_{ep.get('rsi_period', 14)}"]
            thresh = ep.get("rsi_threshold", 30)
            # Reversion: RSI < Threshold
            base_signal = rsi < thresh

        else:
            base_signal = np.zeros(len(df), dtype=bool)

        # 2. Apply Filters
        for f in candidate.filters:
            if f.type == FilterType.REGIME_MA:
                p = f.params.get("period", 200)
                ma = indicators[f"ma_{p}"]
                # Regime: Close > MA
                mask = (close > ma.values)
                base_signal = base_signal & mask

        return base_signal

    def _finalize_results(self, equity_curve, trades, index, open_position=None):
        equity_series = pd.Series(equity_curve, index=index)
        metrics = calculate_metrics(equity_series, trades, self.initial_capital)
        return {
            "equity": equity_series,
            "trades": trades,
            "metrics": metrics,
            "open_position": open_position
        }
