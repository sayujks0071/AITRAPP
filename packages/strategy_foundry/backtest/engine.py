import pandas as pd
import numpy as np
from typing import Dict, Any, List
import structlog
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.adapters.core_costs import CostModel, RiskConfig

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, cost_model: CostModel):
        self.cost_model = cost_model

    def run(self, strategy: Strategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run backtest for a strategy on a DataFrame.
        """
        if df.empty:
            return {}

        # 1. Generate Raw Signals
        raw_positions = strategy.generate_positions(df)

        # 2. Risk Management Overlay (Stop Loss / Take Profit)
        # This requires iteration or vectorization with state.
        # Vectorized path dependent logic is hard. We'll use a fast loop using numpy.

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        timestamps = df.index
        atr = strategy.get_atr_array(df)

        raw_pos_arr = raw_positions.values

        n = len(df)
        final_pos = np.zeros(n, dtype=int)
        trades = []

        # State
        current_pos = 0 # 0, 1, -1
        entry_price = 0.0
        entry_idx = 0
        sl_price = 0.0
        tp_price = 0.0

        # Performance optimization: Use numpy arrays for lookup
        # Execution: Next Open.
        # So signal at i affects pos at i+1.

        # We need Open prices for execution
        opens = df["open"].values

        # Loop starts at 1 because we need previous signal
        for i in range(1, n):
            # Check exits if in position
            if current_pos != 0:
                # Check SL/TP hit on Today's OHLC
                # Assumption: If Low < SL, we hit SL.
                # If High > TP, we hit TP.
                # Order of check matters.
                # Standard assumption: Worst case first? Or based on Open?
                # If Open triggers SL/TP?

                exit_price = None
                exit_reason = ""

                # Check Gap Open vs SL/TP
                if current_pos == 1:
                    if opens[i] <= sl_price:
                        exit_price = opens[i]
                        exit_reason = "SL_GAP"
                    elif opens[i] >= tp_price:
                        exit_price = opens[i]
                        exit_reason = "TP_GAP"
                    elif low[i] <= sl_price:
                        exit_price = sl_price
                        exit_reason = "SL"
                    elif high[i] >= tp_price:
                        exit_price = tp_price
                        exit_reason = "TP"

                elif current_pos == -1:
                    if opens[i] >= sl_price:
                        exit_price = opens[i]
                        exit_reason = "SL_GAP"
                    elif opens[i] <= tp_price:
                        exit_price = opens[i]
                        exit_reason = "TP_GAP"
                    elif high[i] >= sl_price:
                        exit_price = sl_price
                        exit_reason = "SL"
                    elif low[i] <= tp_price:
                        exit_price = tp_price
                        exit_reason = "TP"

                if exit_price is not None:
                    # Close trade
                    trades.append({
                        "entry_time": timestamps[entry_idx],
                        "exit_time": timestamps[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "side": current_pos,
                        "reason": exit_reason
                    })
                    current_pos = 0
                    final_pos[i] = 0
                else:
                    # Hold
                    final_pos[i] = current_pos

                    # Check signal for reversal?
                    # If raw_signal[i-1] != current_pos (and not 0), maybe reverse?
                    # For simplicty: Exits are only SL/TP or Reversal Signal.
                    # If Reversal:
                    new_signal = raw_pos_arr[i-1]
                    if new_signal != 0 and new_signal != current_pos:
                        # Close current
                        trades.append({
                            "entry_time": timestamps[entry_idx],
                            "exit_time": timestamps[i],
                            "entry_price": entry_price,
                            "exit_price": opens[i],
                            "side": current_pos,
                            "reason": "SIGNAL"
                        })
                        # Open new
                        current_pos = int(new_signal)
                        entry_price = opens[i]
                        entry_idx = i
                        final_pos[i] = current_pos

                        # Set new SL/TP
                        cur_atr = atr[i-1] # Use ATR from prev close
                        if np.isnan(cur_atr): cur_atr = entry_price * 0.01 # Fallback

                        if current_pos == 1:
                            sl_price = entry_price - (cur_atr * strategy.stop_loss_atr)
                            tp_price = entry_price + (cur_atr * strategy.take_profit_atr)
                        else:
                            sl_price = entry_price + (cur_atr * strategy.stop_loss_atr)
                            tp_price = entry_price - (cur_atr * strategy.take_profit_atr)

            else:
                # No position, check entry
                signal = raw_pos_arr[i-1] # Signal from yesterday
                if signal != 0:
                    current_pos = int(signal)
                    entry_price = opens[i]
                    entry_idx = i
                    final_pos[i] = current_pos

                    cur_atr = atr[i-1]
                    if np.isnan(cur_atr): cur_atr = entry_price * 0.01

                    if current_pos == 1:
                        sl_price = entry_price - (cur_atr * strategy.stop_loss_atr)
                        tp_price = entry_price + (cur_atr * strategy.take_profit_atr)
                    else:
                        sl_price = entry_price + (cur_atr * strategy.stop_loss_atr)
                        tp_price = entry_price - (cur_atr * strategy.take_profit_atr)

        # Close open position at end
        if current_pos != 0:
            trades.append({
                "entry_time": timestamps[entry_idx],
                "exit_time": timestamps[-1],
                "entry_price": entry_price,
                "exit_price": close[-1],
                "side": current_pos,
                "reason": "END"
            })

        # Calculate PnL curve
        # We need equity curve.
        # Simplified: Sum up trade returns.
        # Better: Daily Mark-to-Market.
        # Let's reconstruct daily equity from trades + hold logic.

        # Convert trades to DataFrame
        trades_df = pd.DataFrame(trades)

        equity_curve = pd.Series(0.0, index=df.index)
        # TODO: Precise daily equity logic is complex.
        # For ranking, we usually rely on Trade Statistics.
        # But Drawdown requires equity curve.
        # Let's calculate Equity Curve by iterating days.

        capital = 100000.0 # Base 100k
        equity = [capital] * n

        # Map trades to days
        # This is O(N) pass again.

        # Apply costs
        if not trades_df.empty:
            for idx, trade in trades_df.iterrows():
                # Gross PnL
                diff = trade["exit_price"] - trade["entry_price"]
                gross_pnl_pts = diff * trade["side"]

                # Costs
                cost = self.cost_model.estimate_cost(trade["exit_price"], 1, "SELL") + \
                       self.cost_model.estimate_cost(trade["entry_price"], 1, "BUY")

                net_pnl_pts = gross_pnl_pts - cost

                # ROI
                # trade_ret = net_pnl_pts / trade["entry_price"]
                trades_df.at[idx, "net_pnl"] = net_pnl_pts
                trades_df.at[idx, "return_pct"] = net_pnl_pts / trade["entry_price"]

        return {
            "trades": trades_df,
            "final_pos": final_pos
        }
