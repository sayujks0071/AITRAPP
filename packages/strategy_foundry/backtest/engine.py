import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, cost_bps: float = 5.0, slippage_bps: float = 5.0):
        self.initial_capital = initial_capital
        self.cost_bps = cost_bps / 10000.0
        self.slippage_bps = slippage_bps / 10000.0

    def run(self, strategy: StrategyCandidate, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run backtest for a single instrument.
        Returns metrics, trades, and equity curve.
        """
        # Get raw signals (1=Enter, -10=Exit, 0=None)
        raw_signals = strategy.generate_raw_signals(df)

        trades = []
        equity_curve = [self.initial_capital] * len(df)
        cash = self.initial_capital
        position_qty = 0

        # Helper vars
        entry_price = 0.0
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0

        # Params
        sl_mult = strategy.risk_params.get("sl_atr", 2.0)
        tp_mult = strategy.risk_params.get("tp_atr", 0.0)
        max_bars = strategy.risk_params.get("max_bars", 0)
        trailing_sl = strategy.risk_params.get("trailing_sl", False)

        # Arrays for speed
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        dates = df.index
        atrs = df["atr_14"].values if "atr_14" in df else (df["atr"].values if "atr" in df else np.zeros(len(df)))
        sigs = raw_signals.values

        pending_entry = False
        pending_sl = 0.0
        pending_tp = 0.0

        for i in range(1, len(df)):
            current_date = dates[i]

            # 1. Execute Pending Entry (Market Open)
            if pending_entry:
                exec_price = opens[i] * (1 + self.slippage_bps) # Buy slippage
                # Position sizing: Fixed fractional or Fixed capital?
                # Let's use 100% equity for simplicity (compounding) or fixed?
                # Metrics usually assume compounding.
                # Qty = Cash / Price
                qty = cash / exec_price
                cost = qty * exec_price * self.cost_bps

                cash -= (qty * exec_price + cost)
                position_qty = qty
                entry_price = exec_price
                entry_idx = i

                stop_loss = pending_sl
                take_profit = pending_tp

                pending_entry = False

            # 2. Manage Position (Intraday Exits)
            if position_qty > 0:
                exit_price = 0.0
                exit_reason = ""

                # Check Stops (Low/High)
                if lows[i] <= stop_loss:
                    exit_price = stop_loss * (1 - self.slippage_bps) # Sell slippage
                    exit_reason = "SL"
                elif tp_mult > 0 and highs[i] >= take_profit:
                    exit_price = take_profit * (1 - self.slippage_bps)
                    exit_reason = "TP"
                elif max_bars > 0 and (i - entry_idx) >= max_bars:
                    # Time exit: Exit at Close (simplification)
                    exit_price = closes[i] * (1 - self.slippage_bps)
                    exit_reason = "TIME"
                elif sigs[i] == -10:
                    # Technical exit at Close
                    exit_price = closes[i] * (1 - self.slippage_bps)
                    exit_reason = "SIGNAL"

                if exit_price > 0:
                    # Execute Exit
                    proceeds = position_qty * exit_price
                    cost = proceeds * self.cost_bps
                    cash += (proceeds - cost)

                    # Record Trade
                    pnl = proceeds - cost - (position_qty * entry_price * (1 + self.cost_bps)) # Approx
                    # Better PnL: Cash Delta
                    # We updated Cash on Entry and Exit.
                    # PnL = (ExitVal - ExitCost) - (EntryVal + EntryCost)
                    # But we are compounding, so cash tracks it.

                    trade_pnl = (exit_price - entry_price) * position_qty - (position_qty * entry_price * self.cost_bps) - (position_qty * exit_price * self.cost_bps)

                    trades.append({
                        "entry_date": dates[entry_idx],
                        "exit_date": current_date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": trade_pnl,
                        "return_pct": (exit_price / entry_price) - 1,
                        "reason": exit_reason
                    })

                    position_qty = 0
                else:
                    # Update Trailing SL
                    if trailing_sl:
                        new_sl = closes[i] - atrs[i] * sl_mult
                        if new_sl > stop_loss:
                            stop_loss = new_sl

            # 3. Check New Entry Signal
            if position_qty == 0 and not pending_entry:
                if sigs[i] == 1:
                    pending_entry = True
                    ref_price = closes[i]
                    ref_atr = atrs[i]
                    pending_sl = ref_price - ref_atr * sl_mult
                    if tp_mult > 0:
                        pending_tp = ref_price + ref_atr * tp_mult
                    else:
                        pending_tp = 0

            # Update Equity Curve
            # If in position, mark-to-market at Close
            if position_qty > 0:
                mtm = position_qty * closes[i]
                equity_curve[i] = cash + mtm
            else:
                equity_curve[i] = cash

        # Calculate Metrics
        equity_series = pd.Series(equity_curve, index=dates)
        metrics = calculate_metrics(trades, equity_series)

        return {
            "metrics": metrics,
            "trades": pd.DataFrame(trades),
            "equity_curve": equity_series
        }
