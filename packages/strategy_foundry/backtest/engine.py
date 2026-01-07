import pandas as pd
import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from ..adapters.core_costs import CostAdapter

@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    side: int # 1 or -1
    quantity: int
    pnl: float
    return_pct: float
    entry_reason: str
    exit_reason: str
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, slippage_bps: float = 5.0):
        self.initial_capital = initial_capital
        self.slippage = slippage_bps / 10000.0
        self.cost_adapter = CostAdapter()

    def run(self, df: pd.DataFrame, positions: pd.Series, stop_atr_mult: float = 2.0, instrument_type: str = 'EQUITY') -> Dict[str, Any]:
        """
        Run backtest.
        df: DataFrame with OHLCV and 'atr' column.
        positions: Series with target position (1, 0, -1).
        Assumptions:
        - Signal generated at close of day T.
        - Entry at Open of day T+1.
        """
        trades: List[Trade] = []
        equity_curve = [self.initial_capital]
        current_capital = self.initial_capital

        current_pos = 0 # 0, 1, -1
        entry_price = 0.0
        entry_date = None
        quantity = 0
        stop_loss = 0.0
        take_profit = 0.0 # Optional, not used by default

        # Align signals: signal at T applies to T+1
        # positions series indicates what we want to be holding.
        # But we execute at OPEN.
        # If positions[i] != current_pos, we trade at open[i+1]

        # We need to iterate
        # To make it safe, we can shift positions by 1 to align with execution time?
        # No, let's iterate day by day.

        # Pre-calculate shifted signals for execution at open
        # signal[i] is generated using Close[i].
        # We trade at Open[i+1].

        dates = df.index
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        atrs = df['atr'].values if 'atr' in df else np.zeros(len(df))

        signals = positions.values

        n = len(df)

        for i in range(n - 1): # Can't trade on last day's signal (would enter next day)
            # Today is i. We have signal from today (calculated at close).
            # We execute tomorrow (i+1).

            date = dates[i+1]
            open_price = opens[i+1]
            high = highs[i+1]
            low = lows[i+1]
            close = closes[i+1]

            signal = signals[i] # Signal from prev close

            # 1. Manage existing position (Check Stops/Exits)
            if current_pos != 0:
                # Check Intraday Stop
                exit_price = 0.0
                exit_reason = ""

                # Check Low/High against Stop
                hit_stop = False
                if current_pos == 1:
                    if low < stop_loss:
                        hit_stop = True
                        exit_price = min(open_price, stop_loss) # If gap down, use open. Else stop.
                        # Slippage on stop
                        exit_price = exit_price * (1 - self.slippage)
                        exit_reason = "STOP_LOSS"
                elif current_pos == -1:
                    if high > stop_loss:
                        hit_stop = True
                        exit_price = max(open_price, stop_loss)
                        exit_price = exit_price * (1 + self.slippage)
                        exit_reason = "STOP_LOSS"

                # Check Signal Exit (if signal changed)
                # If signal opposes position or is 0
                signal_exit = False
                if not hit_stop:
                    if (current_pos == 1 and signal != 1) or (current_pos == -1 and signal != -1):
                        signal_exit = True
                        exit_price = open_price
                        # Apply slippage on signal exit
                        if current_pos == 1: exit_price *= (1 - self.slippage)
                        else: exit_price *= (1 + self.slippage)
                        exit_reason = "SIGNAL"

                if hit_stop or signal_exit:
                    # Calculate PnL
                    raw_pnl = (exit_price - entry_price) * quantity * current_pos
                    # Costs
                    costs = self.cost_adapter.estimate_fees(instrument_type, quantity, entry_price, exit_price)
                    net_pnl = raw_pnl - costs

                    current_capital += net_pnl

                    trades.append(Trade(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=date,
                        exit_price=exit_price,
                        side=current_pos,
                        quantity=quantity,
                        pnl=net_pnl,
                        return_pct=net_pnl / (entry_price * quantity),
                        entry_reason="SIGNAL",
                        exit_reason=exit_reason
                    ))

                    current_pos = 0
                    quantity = 0

            # 2. Enter New Position
            if current_pos == 0 and signal != 0:
                # Calculate Quantity (Risk Based)
                # Risk per trade = 1% of capital
                risk_amt = current_capital * 0.01

                # ATR based stop distance
                atr = atrs[i] # Prev day ATR
                if pd.isna(atr) or atr == 0:
                    atr = open_price * 0.01 # Fallback 1%

                stop_dist = atr * stop_atr_mult

                if stop_dist > 0:
                    qty = int(risk_amt / stop_dist)
                    if qty > 0:
                        entry_price = open_price
                        # Slippage on entry
                        if signal == 1: entry_price *= (1 + self.slippage)
                        else: entry_price *= (1 - self.slippage)

                        quantity = qty
                        current_pos = signal
                        entry_date = date

                        # Set Stop Loss
                        if signal == 1:
                            stop_loss = entry_price - stop_dist
                        else:
                            stop_loss = entry_price + stop_dist

            # Record Equity (Mark to Market at Close)
            if current_pos != 0:
                unrealized = (close - entry_price) * quantity * current_pos
                equity_curve.append(current_capital + unrealized)
            else:
                equity_curve.append(current_capital)

        # Flatten at end
        if current_pos != 0:
             # Assume close
             exit_price = closes[-1]
             raw_pnl = (exit_price - entry_price) * quantity * current_pos
             costs = self.cost_adapter.estimate_fees(instrument_type, quantity, entry_price, exit_price)
             net_pnl = raw_pnl - costs
             current_capital += net_pnl
             trades.append(Trade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=dates[-1],
                exit_price=exit_price,
                side=current_pos,
                quantity=quantity,
                pnl=net_pnl,
                return_pct=net_pnl / (entry_price * quantity),
                entry_reason="SIGNAL",
                exit_reason="EOD_FORCE"
            ))
             equity_curve[-1] = current_capital

        return {
            "trades": trades,
            "equity_curve": pd.Series(equity_curve, index=dates),
            "final_capital": current_capital,
            "total_trades": len(trades)
        }
