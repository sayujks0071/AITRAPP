"""
Backtest Engine.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, slippage_bps: float = 5.0, all_in_cost_bps: float = 10.0):
        self.raw_data = data.copy()
        # Pre-calculate indicators
        self.data = IndicatorsAdapter.add_all_indicators(self.raw_data.copy())
        self.slippage_bps = slippage_bps
        self.cost_bps = all_in_cost_bps

    def run(self, candidate: StrategyCandidate, start_date=None, end_date=None) -> Dict:
        """
        Run backtest for a single candidate.
        Returns stats dict.
        """
        df = self.data.copy()
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        if df.empty:
            return {"trades": 0, "return": 0.0, "max_dd": 0.0, "sharpe": 0.0}

        # Logic interpretation
        signals = self._generate_signals(df, candidate)

        # Sim execution
        trades, equity_curve, final_position = self._simulate_execution(df, signals, candidate)

        # Calculate metrics (simplified here, detailed in metrics.py if needed)
        metrics = self._calculate_metrics(trades, equity_curve)

        return {
            "metrics": metrics,
            "trades": trades, # List of dicts
            "equity_curve": equity_curve, # Series
            "current_position": final_position
        }

    def _generate_signals(self, df: pd.DataFrame, candidate: StrategyCandidate) -> pd.Series:
        """
        Evaluate entry/exit rules to generate a signal series (-1, 0, 1).
        """
        entries = pd.Series(False, index=df.index)
        exits = pd.Series(False, index=df.index)

        # Evaluate Entry Rules (AND logic for now)
        first_entry = True
        for rule in candidate.entry_rules:
            condition = self._evaluate_rule(df, rule, candidate.params)
            if first_entry:
                entries = condition
                first_entry = False
            else:
                entries = entries & condition

        # Evaluate Exit Rules (OR logic usually, but let's stick to explicit signals)
        # Actually, for exits, if ANY exit rule triggers, we exit.
        for rule in candidate.exit_rules:
             # Skip stop loss rules here, they are handled in simulation usually?
             # Or we can approximate them as boolean series if possible.
             # Trailing stops are path dependent, must be handled in loop.
             if rule["type"] in ["trailing_stop_atr", "time_stop"]:
                 continue

             condition = self._evaluate_rule(df, rule, candidate.params)
             exits = exits | condition

        return entries # We assume loop will handle exits + entries combined

    def _evaluate_rule(self, df: pd.DataFrame, rule: Dict, params: Dict) -> pd.Series:
        rtype = rule["type"]

        if rtype == "ema_cross_above":
            fast_col = f"ema_{params[rule['fast']]}"
            slow_col = f"ema_{params[rule['slow']]}"
            # Crossover logic: Fast > Slow AND Fast.shift(1) <= Slow.shift(1)
            return (df[fast_col] > df[slow_col]) & (df[fast_col].shift(1) <= df[slow_col].shift(1))

        elif rtype == "ema_cross_below":
            fast_col = f"ema_{params[rule['fast']]}"
            slow_col = f"ema_{params[rule['slow']]}"
            return (df[fast_col] < df[slow_col]) & (df[fast_col].shift(1) >= df[slow_col].shift(1))

        elif rtype == "supertrend_bullish":
            # Assuming 'supertrend' column is the value, and we need direction.
            # Often implemented as Close > Supertrend for bullish.
            return df['Close'] > df['supertrend']

        elif rtype == "rsi_oversold":
            p = params[rule['period']]
            t = params[rule['threshold']]
            # RSI < Threshold
            col = f"rsi_{p}"
            return df[col] < t

        elif rtype == "rsi_overbought":
            p = params[rule['period']]
            t = params[rule['threshold']]
            # RSI > Threshold
            col = f"rsi_{p}"
            return df[col] > t

        elif rtype == "price_below_bb_lower":
            return df['Close'] < df['bb_lower']

        return pd.Series(False, index=df.index)

    def _simulate_execution(self, df: pd.DataFrame, entry_signals: pd.Series, candidate: StrategyCandidate):
        """
        Path-dependent simulation for accurate costs and trailing stops.
        """
        position = 0 # 0: Flat, 1: Long
        entry_price = 0.0
        entry_idx = None
        highest_price = 0.0

        trades = []
        equity = [100.0] # start with 100 units

        dates = df.index
        opens = df['Open'].values
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        atrs = df.get('atr_14', pd.Series(0, index=df.index)).values # Default 0 if missing

        # Parse params for risk
        stop_atr_mult = candidate.params.get("stop_loss_atr")
        max_hold = candidate.params.get("max_bars_hold")

        entries_arr = entry_signals.values

        # Find explicit exit rules (boolean series)
        explicit_exits = pd.Series(False, index=df.index)
        for rule in candidate.exit_rules:
            if rule["type"] not in ["trailing_stop_atr", "time_stop"]:
                explicit_exits = explicit_exits | self._evaluate_rule(df, rule, candidate.params)
        explicit_exits_arr = explicit_exits.values

        # Iterating bar by bar
        for i in range(1, len(df)):
            current_date = dates[i]
            open_p = opens[i]
            high_p = highs[i]
            low_p = lows[i]
            close_p = closes[i]

            # PnL update (mark to market)
            # Simplified: we update equity only on trade close for this fast engine?
            # Or daily? Let's do daily for equity curve.

            # Check exits first if we are long
            if position == 1:
                exit_price = None
                reason = ""

                # Update highest price for trailing stop
                if high_p > highest_price:
                    highest_price = high_p

                # 1. Trailing Stop
                if stop_atr_mult:
                    # Trailing from highest high since entry
                    # Using previous bar's ATR for stop calculation to avoid lookahead?
                    # Or current? Usually trigger is intraday.
                    # Stop level = highest_price - ATR * mult
                    # Check if Low < Stop Level
                    # Use ATR from previous bar (i-1)
                    prev_atr = atrs[i-1]
                    stop_level = highest_price - (prev_atr * stop_atr_mult)

                    if low_p < stop_level:
                        exit_price = max(open_p, stop_level) # Assume slippage later
                        # If gap down below stop, we exit at Open (or worse)
                        # If open is above stop, we exit at stop.
                        # Conservative: exit at min(Open, Stop) -> No, if gap down we exit at Open.
                        if open_p < stop_level:
                             exit_price = open_p
                        else:
                             exit_price = stop_level
                        reason = "trailing_stop"

                # 2. Time Stop
                if not exit_price and max_hold:
                    if (i - entry_idx) >= max_hold:
                        exit_price = open_p
                        reason = "time_stop"

                # 3. Explicit Signal Exit
                if not exit_price and explicit_exits_arr[i]:
                    # Exit at Open of NEXT bar? Or Close of current?
                    # "Execution: next-bar open".
                    # So if signal was generated at i-1, we enter/exit at i Open.
                    # But here we are iterating i.
                    # If signal is True at i (based on Close[i]), we exit at i+1 Open.
                    # Wait, let's align.
                    # If we use `entries_arr` which is calculated on Close[i],
                    # we should act on it at i+1.
                    pass

                # Check explicit exit from PREVIOUS bar
                if not exit_price and explicit_exits_arr[i-1]:
                    exit_price = open_p
                    reason = "signal_exit"

                if exit_price:
                    # Execute Exit
                    # Apply costs
                    # Slippage: assume worst case on exit (sell lower)
                    exec_price = exit_price * (1 - self.slippage_bps/10000)
                    gross_ret = (exec_price / entry_price) - 1
                    net_ret = gross_ret - (self.cost_bps/10000) # One way cost? Or round trip?
                    # We apply cost on entry and exit.
                    # Let's apply total cost here to simplify logic or per side.
                    # "all_in_cost_bps per side"

                    # Update equity
                    # (Exit/Entry) * (1-costs) ...
                    # Precise:
                    # units = equity / (entry * (1+cost))
                    # new_equity = units * (exit * (1-cost))

                    trade_ret = (exit_price/entry_price) * (1 - self.cost_bps/10000) * (1 - self.slippage_bps/10000) - 1
                    # Note: entry cost was paid already?
                    # Let's compute PnL multiplier:
                    # P_exit_net = exit * (1 - cost - slip)
                    # P_entry_net = entry * (1 + cost + slip)
                    # Ret = P_exit_net / P_entry_net - 1

                    p_entry_net = entry_price * (1 + (self.cost_bps + self.slippage_bps)/10000)
                    p_exit_net = exit_price * (1 - (self.cost_bps + self.slippage_bps)/10000)

                    pnl_pct = (p_exit_net / p_entry_net) - 1

                    trades.append({
                        "entry_date": dates[entry_idx],
                        "exit_date": current_date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl_pct,
                        "reason": reason
                    })

                    equity[-1] = equity[-1] * (1 + pnl_pct) # Update today's equity
                    position = 0
                    highest_price = 0.0
                    entry_idx = None
                    continue # Finished this bar logic

            # If Flat, check Entry
            if position == 0:
                # Check entry signal from PREVIOUS bar
                if entries_arr[i-1]:
                    # Enter at Open
                    entry_price = open_p
                    entry_idx = i
                    highest_price = high_p # Initialize for trailing stop
                    position = 1

            # Record Daily Equity (Mark to market if position open)
            if position == 1:
                # MTM
                # current val = equity * (close / entry) ... approx
                # We won't apply costs to daily MTM, just final
                curr_val = equity[-1] * (close_p / entry_price) # VERY rough, ignores prior trade compounding within day?
                # Actually equity array stores end-of-day equity.
                # If we just traded (exit), equity[-1] is updated.
                # If we just entered, equity is roughly same minus spread.
                # If holding, it moves with price.

                # Better: track 'cash' and 'units'.
                # But simple series:
                # previous_equity * (change in price)
                change = close_p / opens[i] # Intra-day change
                # This is getting complex for single loop.
                # Simple approximation:
                # If holding, equity = last_equity * (close_i / close_i-1)
                # But we entered at open.
                if entry_idx == i:
                    # Entered today
                    change = close_p / open_p
                else:
                    change = close_p / closes[i-1]

                equity.append(equity[-1] * change)
            else:
                # Flat, no change (assume 0% interest on cash)
                equity.append(equity[-1])

        return trades, pd.Series(equity, index=df.index[:len(equity)]), position

    def _calculate_metrics(self, trades: List[Dict], equity_curve: pd.Series) -> Dict:
        """
        Compute standard metrics.
        """
        if not trades:
            return {
                "cagr": 0.0,
                "sharpe": 0.0,
                "max_dd": 0.0,
                "trades": 0,
                "win_rate": 0.0
            }

        # CAGR
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        if days <= 0: days = 1
        years = days / 365.25
        final_eq = equity_curve.iloc[-1]
        cagr = (final_eq / 100.0) ** (1/years) - 1 if final_eq > 0 else -0.99

        # Max DD
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_dd = abs(drawdown.min())

        # Sharpe
        daily_ret = equity_curve.pct_change().dropna()
        if daily_ret.std() > 0:
            sharpe = (daily_ret.mean() / daily_ret.std()) * (252**0.5)
        else:
            sharpe = 0.0

        # Win Rate
        wins = sum(1 for t in trades if t['pnl'] > 0)
        win_rate = wins / len(trades)

        # Sortino
        neg_ret = daily_ret[daily_ret < 0]
        if neg_ret.std() > 0:
            sortino = (daily_ret.mean() / neg_ret.std()) * (252**0.5)
        else:
            sortino = 0.0

        # Calmar
        calmar = cagr / max_dd if max_dd > 0 else 0.0

        return {
            "cagr": cagr,
            "sharpe": sharpe,
            "sortino": sortino,
            "max_dd": max_dd,
            "calmar": calmar,
            "trades": len(trades),
            "win_rate": win_rate,
            "pf": 0.0 # TODO calculate profit factor
        }
