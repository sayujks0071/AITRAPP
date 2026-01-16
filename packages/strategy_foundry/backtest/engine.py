import pandas as pd
import numpy as np
from typing import Dict, List, Any
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.costs import CostModel
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

class BacktestEngine:
    def __init__(self, cost_model: CostModel):
        self.cost_model = cost_model
        self.generator = StrategyGenerator()

    def run(self, df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
        """
        Runs the backtest. Returns a DataFrame of trades.
        """
        if df.empty:
             return pd.DataFrame()

        # 1. Generate Signals (Vectorized)
        # Returns 1 where entry condition is met
        entry_signals = self.generator.generate_signal(df, config)

        # 2. Prepare arrays for fast loop
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        # ATR for dynamic stops
        atr_series = IndicatorsAdapter.atr(df, period=14).fillna(0).values

        signal_arr = entry_signals.values

        n = len(df)
        trades = []

        # State
        in_trade = False
        entry_price = 0.0
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0

        # Parse Exit Time
        try:
             exit_hour, exit_minute = map(int, config.exit_time.split(':'))
        except:
             exit_hour, exit_minute = 15, 25

        # Pre-compute EOD exit boolean mask
        # Vectorized check is faster than datetime object access in loop
        times_pd = df['datetime']
        minutes_of_day = times_pd.dt.hour * 60 + times_pd.dt.minute
        exit_minutes = exit_hour * 60 + exit_minute
        force_exit_mask = (minutes_of_day >= exit_minutes).values

        # Reset mask for new day?
        # If bars are continuous multi-day, mask works correctly (resets each day implicitly by hour).

        # Loop
        # We start from 1 because we need i-1 for signal
        for i in range(1, n):
            # Check Exit first
            if in_trade:
                # 1. EOD Exit (Session Close)
                if force_exit_mask[i]:
                    # Forced exit at Open of this bar (or Close of previous?)
                    # Strategy: If time >= 15:25, exit immediately at Open.
                    exit_price = opens[i]
                    self._record_trade(trades, entry_price, exit_price, entry_idx, i, "EOD")
                    in_trade = False
                    continue

                # 2. Time Stop (Max Bars)
                if (i - entry_idx) >= config.max_bars_hold:
                    exit_price = opens[i]
                    self._record_trade(trades, entry_price, exit_price, entry_idx, i, "Time")
                    in_trade = False
                    continue

                # 3. Stop Loss / Take Profit (Intra-bar)
                # Check SL (Hit Low)
                if lows[i] <= stop_loss:
                    # Gap check
                    if opens[i] < stop_loss:
                        executed_price = opens[i]
                    else:
                        executed_price = stop_loss

                    self._record_trade(trades, entry_price, executed_price, entry_idx, i, "SL")
                    in_trade = False
                    continue

                # Check TP (Hit High)
                if highs[i] >= take_profit:
                    # Gap check
                    if opens[i] > take_profit:
                        executed_price = opens[i]
                    else:
                        executed_price = take_profit

                    self._record_trade(trades, entry_price, executed_price, entry_idx, i, "TP")
                    in_trade = False
                    continue

            # Check Entry
            if not in_trade:
                # If Signal at i-1 (completed bar), Enter Open i
                if signal_arr[i-1] == 1:
                    # Prevent entry if we are already in forced exit window
                    if force_exit_mask[i]:
                         continue

                    # Enter Long
                    in_trade = True
                    entry_price = opens[i]
                    entry_idx = i

                    # Set Stops
                    atr_val = atr_series[i-1]
                    if atr_val == 0 or np.isnan(atr_val):
                         atr_val = entry_price * 0.01

                    stop_loss = entry_price - (config.stop_loss_atr * atr_val)
                    take_profit = entry_price + (config.take_profit_atr * atr_val)

        return pd.DataFrame(trades)

    def _record_trade(self, trades: List, entry_price: float, exit_price: float, entry_idx: int, exit_idx: int, reason: str):
        # Calculate PnL with costs (Long only)

        # Apply slippage
        buy_price = self.cost_model.get_slippage_price(entry_price, 1)
        sell_price = self.cost_model.get_slippage_price(exit_price, -1)

        # Spread Guard Cost (BPS)
        spread_cost = self.cost_model.spread_guard_bps / 10000.0

        # Tax BPS
        tax = self.cost_model.tax_bps / 10000.0

        # Effective Entry (incl Spread guard penalty in cost)
        # We penalize entry with spread guard to simulate "crossing the spread" aggressively?
        # Or just add to friction.
        total_friction = spread_cost + tax

        # Effective Return
        # (Exit_adj - Entry_adj) / Entry_adj
        # Entry pays (Price + Slippage) * (1 + Friction) ?
        # Standard:
        # Net PnL = (Sell Price * (1 - Tax)) - (Buy Price * (1 + Tax? No STT only on Sell usually))
        # Let's assume symmetric friction for simplicity of the lab.

        eff_entry = buy_price * (1 + total_friction)
        eff_exit = sell_price * (1 - total_friction)

        net_ret = (eff_exit - eff_entry) / eff_entry

        trades.append({
            "entry_idx": entry_idx,
            "exit_idx": exit_idx,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "net_return": net_ret,
            "reason": reason,
            "bars_held": exit_idx - entry_idx
        })
