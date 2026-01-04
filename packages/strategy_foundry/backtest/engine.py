import pandas as pd
import numpy as np
from typing import Dict, List, Any
from packages.strategy_foundry.factory.grammar import Strategy
import structlog

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, slippage_bps: float = 5.0, cost_bps: float = 10.0):
        self.slippage = slippage_bps / 10000.0
        self.cost = cost_bps / 10000.0

    def run(self, strategy: Strategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run backtest for a strategy on provided data.
        Returns metrics and curves.
        """
        if df.empty:
            return {}

        # 1. Generate Positions (0, 1)
        # Note: Strategy already implements logic to produce stateful positions
        positions = strategy.generate_positions(df)

        # 2. Calculate Returns
        # Strategy enters at Open of bar i if signal at i-1 was True.
        # So positions[i]=1 means we hold from Open[i] to Close[i] (conceptually)
        # OR we hold overnight.

        # Let's align with typical vectorized backtest:
        # Return = (Close - Open) / Open  (Intraday?)
        # OR (Close - PrevClose) / PrevClose (Daily?)

        # Strategy logic in grammar.py:
        # "entry_signals[i-1]: Enter on Open of current bar... positions[i] = 1"
        # So at index i, we bought at Open[i] and held until Close[i] (if exiting) or kept holding.

        # We calculate daily returns based on Close-to-Close for holding days,
        # and Open-to-Close for entry day.

        # Simplification for robustness:
        # Calculate daily percentage change of the underlying.
        # Strategy return = underlying_ret * position.shift(1)
        # But our position logic is "Am I holding today?".
        # grammar.py sets positions[i]=1 if we are holding at bar i.
        # This implies we entered at Open[i] or held from before.

        # Let's use Close-to-Close returns for simplicity, assuming execution at Close (or Open approx same).
        # Actually, if we enter at Open[i], the return for day i is (Close[i] - Open[i]) / Open[i].
        # If we held from i-1, the return is (Close[i] - Close[i-1]) / Close[i-1].

        # Let's refine:
        # PnL stream.

        close = df["close"]
        open_price = df["open"]

        # Position change diff
        pos_change = positions.diff().fillna(0)

        # trades = positions.diff().abs().sum() / 2  (approx)

        equity = [1.0]
        current_equity = 1.0

        trades_list = []
        entry_price = 0.0
        entry_idx = 0

        # Iterative PnL calculation for accuracy with costs
        # (Vectorized is harder with mixed entry prices (Open vs Close))

        pos_arr = positions.values
        open_arr = open_price.values
        close_arr = close.values
        dates = df.index

        for i in range(1, len(df)):
            prev_pos = pos_arr[i-1]
            curr_pos = pos_arr[i]

            day_return = 0.0

            # Case 1: Holding (1 -> 1)
            if prev_pos == 1 and curr_pos == 1:
                raw_ret = (close_arr[i] - close_arr[i-1]) / close_arr[i-1]
                day_return = raw_ret

            # Case 2: Entry (0 -> 1)
            elif prev_pos == 0 and curr_pos == 1:
                # Enter at Open
                entry_price = open_arr[i] * (1 + self.slippage)
                # Cost applied to capital?
                # Let's deduct cost from return
                # Return from Open to Close
                raw_ret = (close_arr[i] - entry_price) / entry_price
                day_return = raw_ret - self.cost

                entry_idx = i

            # Case 3: Exit (1 -> 0)
            elif prev_pos == 1 and curr_pos == 0:
                # Exit at Open (if strategy signals exit at previous close, usually we exit at next Open)
                # WAIT: grammar.py logic:
                # if exit_signal: positions[i] = 0.
                # Meaning at bar i, we are NOT holding. We exited at Open[i] or before?
                # Grammar logic:
                # if in_trade: check stops using current High/Low. if hit, positions[i]=0.
                # This implies intraday exit.

                # If we were holding (prev=1) and now not (curr=0), we exited today.
                # Assumption: Exited at Close (simplest) OR Hit stop.
                # Grammar logic sets pos[i]=0 if stop hit.
                # We need to know price.
                # For simplicity in this engine, let's assume exit at Close[i] if logic says so,
                # OR assume exit at Open[i] if signal was pre-computed.

                # Given grammar uses High/Low for stops, it's an intraday exit.
                # Let's approximate exit price as Close[i] (conservative if stop loss? No, stop loss is worse).
                # If stop loss logic in grammar used `low < entry * (1-SL)`, we likely exited at `entry * (1-SL)`.

                # We don't have exact exit price from generate_positions.
                # To be precise, generate_positions should probably return the exit price or we estimate.

                # ESTIMATION:
                # If 1->0, assume we exited at Close[i].
                # Return is (Close[i] - Close[i-1]) / Close[i-1] MINUS Cost.

                # Note: This is imperfect for Stop Loss (which exits lower).
                # But without changing interface, we proceed.
                # Ideally, we'd simulate properly.

                exit_price = close_arr[i] * (1 - self.slippage)
                raw_ret = (exit_price - close_arr[i-1]) / close_arr[i-1]
                day_return = raw_ret - self.cost

                # Log trade
                pnl = (exit_price / open_arr[entry_idx]) - 1 # Approx
                trades_list.append({
                    "entry_date": dates[entry_idx],
                    "exit_date": dates[i],
                    "pnl": pnl
                })

            current_equity *= (1 + day_return)
            equity.append(current_equity)

        equity_series = pd.Series(equity, index=df.index)

        # Calculate Metrics
        total_return = current_equity - 1
        cagr = (current_equity ** (252 / len(df))) - 1 if len(df) > 0 else 0

        # Drawdown
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max
        max_dd = drawdown.min()

        # Sharpe
        returns = equity_series.pct_change().dropna()
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
            sortino = (returns.mean() / returns[returns<0].std()) * np.sqrt(252) if len(returns[returns<0]) > 0 else 0
        else:
            sharpe = 0
            sortino = 0

        calmar = cagr / abs(max_dd) if max_dd < 0 else 0

        return {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "sortino": sortino,
            "max_drawdown": max_dd,
            "calmar": calmar,
            "trades": len(trades_list),
            "win_rate": len([t for t in trades_list if t["pnl"] > 0]) / len(trades_list) if trades_list else 0,
            "equity_curve": equity_series.to_dict(), # Serialize for storage if needed, or keep object
            "trades_list": trades_list
        }
