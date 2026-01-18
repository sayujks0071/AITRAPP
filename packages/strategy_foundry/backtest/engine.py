import pandas as pd
import numpy as np
import structlog
from typing import List, Dict, Any
from ..factory.grammar import StrategyCandidate
from ..adapters.core_costs import TransactionCosts

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, costs: TransactionCosts = TransactionCosts()):
        self.costs = costs

    def run(self, df: pd.DataFrame, candidate: StrategyCandidate, indicators: pd.DataFrame) -> Dict[str, Any]:
        """
        Run backtest for a single candidate on a single instrument dataframe.
        Optimized loop.
        """
        # 1. Generate Signal Series (Vectorized)
        target_positions = candidate.generate_positions(df, indicators)

        # 2. Extract Risk Params
        risk = candidate.get_risk_params()
        sl_pct = risk["stop_loss_pct"] / 100.0
        tp_pct = risk["take_profit_pct"] / 100.0
        trail_act = risk["trailing_stop_activation_pct"] / 100.0
        trail_cb = risk["trailing_stop_callback_pct"] / 100.0
        max_hold = risk["max_bars_hold"]

        # 3. Event Loop for Path Dependent Risk (Stops/Exits)
        # We process bar by bar.

        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        dates = df.index

        signals = target_positions.values # 0 or 1

        position = 0 # 0, 1 (Long), -1 (Short)
        entry_price = 0.0
        entry_idx = 0
        peak_price = 0.0

        trades = []
        equity_curve = [] # Simple points

        # Current equity (starts at 0%, we track returns)
        # Actually easier to track % return per trade

        for i in range(1, len(df)):
            # Check Exit First
            if position != 0:
                curr_open = opens[i] # Open of current bar
                # We assume we can exit at Open if gap causes SL?
                # Simplification: Check Low/High for SL/TP.
                # If gap opens below SL, we exit at Open.

                # Update Peak (for trailing)
                if position == 1:
                    peak_price = max(peak_price, highs[i])

                exit_price = 0.0
                exit_reason = ""

                # 1. Time Exit
                if max_hold > 0 and (i - entry_idx) >= max_hold:
                    exit_price = opens[i] # Exit at open of max_hold bar
                    exit_reason = "TIME"

                # 2. Stop Loss (Hit during bar)
                if not exit_reason:
                    if position == 1:
                        sl_price = entry_price * (1 - sl_pct)
                        if lows[i] < sl_price:
                            # If open was already below, exit at Open
                            exit_price = min(opens[i], sl_price)
                            exit_reason = "SL"

                # 3. Take Profit
                if not exit_reason and tp_pct > 0:
                    if position == 1:
                        tp_price = entry_price * (1 + tp_pct)
                        if highs[i] > tp_price:
                             exit_price = max(opens[i], tp_price)
                             exit_reason = "TP"

                # 4. Trailing Stop
                if not exit_reason and trail_act > 0:
                    if position == 1:
                        if peak_price >= entry_price * (1 + trail_act):
                            trail_price = peak_price * (1 - trail_cb)
                            if lows[i] < trail_price:
                                exit_price = min(opens[i], trail_price)
                                exit_reason = "TRAIL"

                # 5. Signal Reversal (Exit)
                # If signal becomes 0 or opposite?
                # The generator returns "Target Position".
                # If signal is 0, we exit?
                # If signal is 1, we stay.
                # Let's assume Signal 0 means "Flat".
                if not exit_reason and signals[i] == 0:
                     exit_price = opens[i] # Exit at next open?
                     # Wait, signals[i] is generated from Data[i].
                     # We can execute at Close[i] or Open[i+1].
                     # "Execution: next-bar open".
                     # So signals[i-1] determines action at Open[i].
                     # Logic below checks signals[i-1] for entry.
                     # Here we check signals[i-1] for exit?
                     pass

                # Let's align execution:
                # Loop i is "Today".
                # Decisions based on i-1.
                signal_prev = signals[i-1]

                if not exit_reason and position == 1 and signal_prev != 1:
                    exit_price = opens[i]
                    exit_reason = "SIGNAL"

                # DO EXIT
                if exit_price > 0:
                    pnl_gross = (exit_price - entry_price) / entry_price
                    # Apply costs
                    cost_bps = self.costs.slippage_bps * 2 + self.costs.all_in_cost_bps * 2
                    pnl_net = pnl_gross - (cost_bps / 10000.0)

                    trades.append({
                        "entry_date": dates[entry_idx],
                        "exit_date": dates[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl_net,
                        "reason": exit_reason,
                        "bars": i - entry_idx
                    })
                    position = 0
                    peak_price = 0.0

            # Check Entry (if flat)
            if position == 0:
                # Based on i-1
                signal_prev = signals[i-1]
                if signal_prev == 1:
                    position = 1
                    entry_price = opens[i]
                    entry_idx = i
                    peak_price = entry_price

        return {
            "trades": pd.DataFrame(trades),
            "equity": self._compute_equity(trades, df.index)
        }

    def _compute_equity(self, trades: List[Dict], index: pd.DatetimeIndex) -> pd.Series:
        """
        Compute daily equity curve.
        """
        eq = pd.Series(0.0, index=index)
        current = 1.0

        if not trades:
            return eq

        # Naive implementation: just step updates on exit dates
        # A full implementation would track MTM.
        # For ranking, realized PnL curve is acceptable.

        trade_df = pd.DataFrame(trades)
        if trade_df.empty:
             return eq

        # Aggregate pnl by exit date
        daily_pnl = trade_df.groupby("exit_date")["pnl"].sum()

        # Cumulative product
        # 1.0 * (1 + r1) * (1 + r2) ...
        # Log return sum is safer

        # Mapping to full index
        pnl_series = daily_pnl.reindex(index, fill_value=0.0)

        # Cumulative
        equity = (1 + pnl_series).cumprod()
        return equity
