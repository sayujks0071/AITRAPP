import pandas as pd
import numpy as np
from typing import List, Dict, Any
from packages.strategy_foundry.factory.generator import StrategyCandidate

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, candidate: StrategyCandidate, force_eod_exit: bool = True):
        self.data = data
        self.candidate = candidate
        self.force_eod_exit = force_eod_exit

    def run(self) -> Dict[str, Any]:
        """
        Run backtest.
        Returns metrics and trades.
        """
        df = self.data.copy()

        # Calculate signals
        # 1. Entry
        entry_mask = pd.Series(False, index=df.index)

        for rule in self.candidate.entry_rules:
            if rule['type'] == 'ema_cross':
                fast = f"ema_{rule['fast']}"
                slow = f"ema_{rule['slow']}"
                # Crossover
                condition = (df[fast] > df[slow]) & (df[fast].shift(1) <= df[slow].shift(1))
                entry_mask = entry_mask | condition
            elif rule['type'] == 'donchian_breakout':
                upper = f"donchian_upper_{rule['period']}"
                # Breakout
                condition = df['close'] > df[upper].shift(1)
                entry_mask = entry_mask | condition
            elif rule['type'] == 'rsi_reversion':
                 # Buy when RSI < low threshold (reversion means we bet on bounce?)
                 # Usually RSI < 30 is oversold, so buy.
                 condition = df['rsi_14'] < rule['threshold_low']
                 entry_mask = entry_mask | condition

        # Apply Filters
        for filt in self.candidate.filters:
            if filt['type'] == 'adx_filter':
                entry_mask = entry_mask & (df['adx_14'] > filt['threshold'])

        # 2. Simulation Loop (Simple vectorized or Iterative for path dependency)
        # We need iterative for stops/exits

        trades = []
        position = 0
        entry_price = 0.0
        entry_time = None
        stop_price = 0.0
        target_price = 0.0

        atr_sl_mult = next((r['multiplier'] for r in self.candidate.exit_rules if r['type'] == 'stop_loss_atr'), 2.0)
        atr_tp_mult = next((r['multiplier'] for r in self.candidate.exit_rules if r['type'] == 'take_profit_atr'), 5.0)
        time_stop_bars = next((r['bars'] for r in self.candidate.exit_rules if r['type'] == 'time_stop'), 100)

        # Iteration
        # Assumes sorted by time

        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        atrs = df['atr_14'].values
        times = df.index

        entries = entry_mask.values

        n = len(df)
        bars_in_trade = 0

        for i in range(n):
            is_last_bar = (i == n - 1)

            # Check exits if in position
            if position > 0:
                bars_in_trade += 1

                # Check stops/targets on current bar i
                # Hit Stop?
                if lows[i] <= stop_price:
                    exit_price = min(opens[i], stop_price) # Conservative: if gap down, use open. Else stop.
                    # Simplified slippage
                    exit_price -= exit_price * 0.0005 # 5 bps slippage
                    pnl = (exit_price - entry_price) / entry_price
                    trades.append({'entry_time': entry_time, 'exit_time': times[i], 'pnl': pnl, 'reason': 'sl'})
                    position = 0
                # Hit Target?
                elif highs[i] >= target_price:
                    exit_price = max(opens[i], target_price)
                    exit_price -= exit_price * 0.0005
                    pnl = (exit_price - entry_price) / entry_price
                    trades.append({'entry_time': entry_time, 'exit_time': times[i], 'pnl': pnl, 'reason': 'tp'})
                    position = 0
                # Time Stop?
                elif bars_in_trade >= time_stop_bars:
                    exit_price = opens[i] # Close at open of this bar
                    exit_price -= exit_price * 0.0005
                    pnl = (exit_price - entry_price) / entry_price
                    trades.append({'entry_time': entry_time, 'exit_time': times[i], 'pnl': pnl, 'reason': 'time'})
                    position = 0
                # End of Day Exit (15:25)
                elif self.force_eod_exit and times[i].hour == 15 and times[i].minute >= 25:
                     exit_price = closes[i]
                     exit_price -= exit_price * 0.0005
                     pnl = (exit_price - entry_price) / entry_price
                     trades.append({'entry_time': entry_time, 'exit_time': times[i], 'pnl': pnl, 'reason': 'eod'})
                     position = 0

            # Check Entry (if flat)
            # Signal at i, enter at i+1
            # We cannot enter on the last bar of the dataset because we don't know the outcome of the next bar.
            # But for Live Signal purposes, if we get an entry signal at the last bar, we want to know.
            # So we track "current_signal" at the end.

            if position == 0 and entries[i]:
                # Filter: Don't enter after 15:00 if strictly intraday
                if times[i].hour < 15:
                    # If this is the last bar, we can't simulate the trade, but we record the signal
                    if is_last_bar:
                         # We would enter on NEXT open.
                         pass
                    else:
                        position = 1
                        entry_price = opens[i+1] # Enter on Next Open
                        entry_price += entry_price * 0.0005 # Slippage
                        entry_time = times[i+1]
                        bars_in_trade = 0

                        # Set Stops (based on signal bar atr)
                        current_atr = atrs[i]
                        stop_price = entry_price - (current_atr * atr_sl_mult)
                        target_price = entry_price + (current_atr * atr_tp_mult)

        # If still in position at end of simulation
        current_status = 0
        if position > 0:
            current_status = 1 # Long
            # Close incomplete trade for stats?
            # Usually we mark to market.
            pnl = (closes[-1] - entry_price) / entry_price
            trades.append({'entry_time': entry_time, 'exit_time': None, 'pnl': pnl, 'reason': 'open'})

        # Check if we have a new signal on the LAST bar
        if position == 0 and entries[-1] and times[-1].hour < 15:
            current_status = 1 # Signal to Buy Next Open

        return {
            "trades": [t for t in trades if t['exit_time'] is not None], # Closed trades only for metrics
            "open_trades": [t for t in trades if t['exit_time'] is None],
            "total_trades": len([t for t in trades if t['exit_time'] is not None]),
            "win_rate": len([t for t in trades if t.get('pnl', 0) > 0 and t['exit_time']]) / len(trades) if trades else 0,
            "avg_pnl": np.mean([t['pnl'] for t in trades if t['exit_time']]) if trades else 0,
            "net_return": sum([t['pnl'] for t in trades if t['exit_time']]),
            "current_signal": current_status
        }
