"""
Backtest Engine
Executes strategies on historical data.
Vectorized signal generation + Event-driven execution loop.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators
from packages.strategy_foundry.adapters.core_costs import DEFAULT_COSTS

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0, spread_guard_bps: float = 0.0):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.spread_guard_bps = spread_guard_bps
        # Precompute common indicators if not already there
        self.data = VectorizedIndicators.add_all(self.data)

    def run(self, strategy: StrategyConfig) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Run the strategy.
        Returns: (trades_df, equity_curve_series)
        """
        df = self.data
        if df.empty:
            return pd.DataFrame(), pd.Series()

        # 1. Generate Entry/Exit Signals (Vectorized)
        entries = self._generate_entries(df, strategy)

        # 2. Execute Loop (Event-driven for correct risk/management)
        trades = []
        equity = [self.initial_capital]
        current_capital = self.initial_capital
        position = 0 # 0, 1 (Long), -1 (Short)
        entry_price = 0.0
        entry_time = None
        stop_loss = 0.0
        take_profit = 0.0

        equity_curve = pd.Series(index=df.index, dtype=float)
        equity_curve.iloc[0] = self.initial_capital

        for i in range(1, len(df)):
            curr_time = df.index[i]
            curr_open = df['open'].iloc[i]
            curr_high = df['high'].iloc[i]
            curr_low = df['low'].iloc[i]
            curr_close = df['close'].iloc[i]

            # prev_bar for signals (avoid lookahead)
            # prev_close = df['close'].iloc[i-1]

            # Check Exits if in position
            if position != 0:
                exit_price = None
                reason = ""

                # Check Stop Loss / Take Profit (intra-bar assumption: Worst case)
                # If Long
                if position > 0:
                    if curr_low <= stop_loss:
                        exit_price = min(curr_open, stop_loss) # Gap handling
                        reason = "SL"
                    elif curr_high >= take_profit:
                        exit_price = max(curr_open, take_profit)
                        reason = "TP"

                # Check End of Day Exit (15:25) - Higher Priority than Time Exit
                if exit_price is None:
                    # Check for 15:25 or later.
                    if (curr_time.hour == 15 and curr_time.minute >= 25) or (curr_time.hour > 15):
                        # Force close
                        exit_price = curr_close # Close at end of bar
                        reason = "EOD"

                # Check Time Exit
                if exit_price is None and strategy.exit_block == "exit_time":
                    max_bars = strategy.exit_params['max_bars']
                    bars_held = i - df.index.get_loc(entry_time)
                    if bars_held >= max_bars:
                        exit_price = curr_open
                        reason = "Time"

                # Check RSI exit if applicable
                if exit_price is None and strategy.entry_block == "entry_mean_rev_rsi":
                    exit_rsi_thresh = strategy.entry_params['exit_rsi']
                    prev_rsi = df['rsi_14'].iloc[i-1]
                    if position > 0 and prev_rsi > exit_rsi_thresh:
                        exit_price = curr_open
                        reason = "RSI_Exit"

                # Execute Exit
                if exit_price is not None:
                    # Gross PnL
                    gross_pnl = (exit_price - entry_price) * position * (current_capital / entry_price)

                    # Apply costs: Slippage + Comm + Spread Guard
                    notional = current_capital
                    total_bps = DEFAULT_COSTS.slippage_bps + DEFAULT_COSTS.commission_bps + self.spread_guard_bps

                    costs = (notional * total_bps / 10000) * 2 # Entry + Exit costs applied at exit for simplicity
                    costs += (DEFAULT_COSTS.flat_fee * 2) # Flat fee per order (entry+exit)

                    net_pnl = gross_pnl - costs
                    current_capital += net_pnl
                    position = 0

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": curr_time,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": net_pnl,
                        "reason": reason
                    })

            # Check Entries if flat
            if position == 0:
                # Intraday constraint: Don't enter after 15:00
                if not (curr_time.hour == 15 and curr_time.minute >= 0) and not (curr_time.hour > 15):
                     if entries.iloc[i-1]: # Signal from previous close
                        position = 1 # Long only for now
                        entry_price = curr_open
                        entry_time = curr_time

                        # Set SL/TP
                        atr_val = df['atr_14'].iloc[i-1]

                        # Calculate Risk Params
                        if strategy.risk_block == "risk_atr":
                            sl_dist = atr_val * strategy.risk_params['multiplier']
                            stop_loss = entry_price - sl_dist

                        if strategy.exit_block == "exit_rr":
                            rr = strategy.exit_params['risk_reward']
                            take_profit = entry_price + (entry_price - stop_loss) * rr
                        else:
                            take_profit = float('inf')

            equity_curve.iloc[i] = current_capital

        # Fill NaNs in equity curve (from gaps)
        equity_curve = equity_curve.ffill()

        return pd.DataFrame(trades), equity_curve

    def _generate_entries(self, df: pd.DataFrame, strategy: StrategyConfig) -> pd.Series:
        """Vectorized entry signal generation"""
        signals = pd.Series(False, index=df.index)

        if strategy.entry_block == "entry_trend_ema_cross":
            # Recompute specific EMAs if not pre-calculated or standard
            # We precalculated ema_20, ema_50, ema_200.
            # If params match, reuse. Else recompute.
            p_fast = strategy.entry_params['fast_period']
            p_slow = strategy.entry_params['slow_period']

            fast = VectorizedIndicators.ema(df['close'], p_fast)
            slow = VectorizedIndicators.ema(df['close'], p_slow)

            # Crossover logic: Fast crosses above Slow
            cond = (fast > slow) & (fast.shift(1) <= slow.shift(1))

            if strategy.entry_params.get('adx_filter'):
                cond = cond & (df['adx_14'] > strategy.entry_params['adx_threshold'])

            signals = cond

        elif strategy.entry_block == "entry_breakout_donchian":
            period = strategy.entry_params['period']
            if period == 20 and 'donchian_upper' in df.columns:
                upper = df['donchian_upper']
            else:
                 upper = df['high'].rolling(window=period).max()

            cond = df['close'] > upper.shift(1) # Breakout of previous high

            if strategy.entry_params['filter_ma']:
                 ma_period = strategy.entry_params['ma_period']
                 sma = df['close'].rolling(window=ma_period).mean()
                 cond = cond & (df['close'] > sma)

            signals = cond

        elif strategy.entry_block == "entry_mean_rev_rsi":
            rsi = df['rsi_14']
            if strategy.entry_params['rsi_period'] != 14:
                 rsi = VectorizedIndicators.rsi(df['close'], strategy.entry_params['rsi_period'])

            cond = rsi < strategy.entry_params['oversold']
            signals = cond

        return signals
