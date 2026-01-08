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
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0):
        self.data = data.copy()
        self.initial_capital = initial_capital
        # Precompute common indicators if not already there
        self.data = VectorizedIndicators.add_all(self.data)

    def run(self, strategy: StrategyConfig) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Run the strategy.
        Returns: (trades_df, equity_curve_series)
        """
        df = self.data

        # 1. Generate Entry/Exit Signals (Vectorized)
        entries = self._generate_entries(df, strategy)

        # 2. Execute Loop (Event-driven for correct risk/management)
        trades = []
        equity = [self.initial_capital]
        current_capital = self.initial_capital
        position = 0 # 0, 1 (Long), -1 (Short)
        entry_price = 0.0
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0

        equity_curve_values = np.zeros(len(df))
        equity_curve_values[0] = self.initial_capital

        # --- OPTIMIZATION START ---
        # Pre-convert columns to numpy arrays for fast access
        # This gives ~20x speedup over iloc iteration
        timestamps = df.index
        # Convert to numpy array of objects (datetime) or native depending on index type
        # Assuming DatetimeIndex, this is usually fast enough, but accessing .hour/.minute
        # on Timestamp is slower than precomputing integer hour/minute arrays if very hot loop.
        # But just extracting the array is a big win.
        times = timestamps.to_pydatetime()

        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        entry_signals = entries.values

        # Pre-fetch indicator arrays needed for logic
        atr_values = df['atr_14'].values if 'atr_14' in df.columns else np.zeros(len(df))
        rsi_values = df['rsi_14'].values if 'rsi_14' in df.columns else np.zeros(len(df))

        # Helper for time exit
        check_time_exit = (strategy.exit_block == "exit_time")
        exit_max_bars = strategy.exit_params.get('max_bars', 0)

        # Helper for RSI exit
        check_rsi_exit = (strategy.entry_block == "entry_mean_rev_rsi")
        exit_rsi_thresh = strategy.entry_params.get('exit_rsi', 60)

        # Risk params
        use_atr_risk = (strategy.risk_block == "risk_atr")
        risk_multiplier = strategy.risk_params.get('multiplier', 2.0)

        use_rr_exit = (strategy.exit_block == "exit_rr")
        rr_ratio = strategy.exit_params.get('risk_reward', 2.0)

        # Constants
        inf = float('inf')

        n_bars = len(df)

        for i in range(1, n_bars):
            # Access arrays directly
            curr_time = times[i]
            curr_open = opens[i]
            curr_high = highs[i]
            curr_low = lows[i]
            curr_close = closes[i]

            # Check Exits if in position
            if position != 0:
                exit_price = None
                reason = ""

                # Check Stop Loss / Take Profit (intra-bar assumption: Worst case)
                # If Long
                if position > 0:
                    if curr_low <= stop_loss:
                        exit_price = min(curr_open, stop_loss) # Gap handling: exit at open if below SL
                        reason = "SL"
                    elif curr_high >= take_profit:
                        exit_price = max(curr_open, take_profit)
                        reason = "TP"

                # Check End of Day Exit (15:25) - Higher Priority than Time Exit
                if exit_price is None:
                    # Note: strict optimization - accessing .hour/.minute on python datetime object
                    if (curr_time.hour == 15 and curr_time.minute >= 25) or (curr_time.hour > 15):
                        exit_price = curr_close # Force close at end of this bar
                        reason = "EOD"

                # Check Time Exit
                if exit_price is None and check_time_exit:
                    bars_held = i - entry_idx
                    if bars_held >= exit_max_bars:
                        exit_price = curr_open
                        reason = "Time"

                # Check RSI exit if applicable
                if exit_price is None and check_rsi_exit:
                    prev_rsi = rsi_values[i-1]
                    if position > 0 and prev_rsi > exit_rsi_thresh:
                        exit_price = curr_open
                        reason = "RSI_Exit"

                # Execute Exit
                if exit_price is not None:
                    pnl = (exit_price - entry_price) * position * (current_capital / entry_price) # Simplistic sizing

                    # Apply costs
                    notional = current_capital
                    costs = (notional * (DEFAULT_COSTS.slippage_bps + DEFAULT_COSTS.commission_bps) / 10000) * 2 # Entry + Exit

                    net_pnl = pnl - costs
                    current_capital += net_pnl
                    position = 0

                    trades.append({
                        "entry_time": times[entry_idx],
                        "exit_time": curr_time,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": net_pnl,
                        "reason": reason
                    })

            # Check Entries if flat
            if position == 0:
                # Intraday constraint: Don't enter after 15:00
                if not (curr_time.hour == 15 and curr_time.minute >= 0):
                     if entry_signals[i-1]: # Signal from previous close
                        position = 1 # Long only for now
                        entry_price = curr_open
                        entry_idx = i

                        # Set SL/TP
                        atr_val = atr_values[i-1]

                        # Calculate Risk Params
                        if use_atr_risk:
                            sl_dist = atr_val * risk_multiplier
                            stop_loss = entry_price - sl_dist

                        if use_rr_exit:
                            take_profit = entry_price + (entry_price - stop_loss) * rr_ratio
                        else:
                            take_profit = inf

            equity_curve_values[i] = current_capital

        # --- OPTIMIZATION END ---

        return pd.DataFrame(trades), pd.Series(equity_curve_values, index=df.index)

    def _generate_entries(self, df: pd.DataFrame, strategy: StrategyConfig) -> pd.Series:
        """Vectorized entry signal generation"""
        signals = pd.Series(False, index=df.index)

        if strategy.entry_block == "entry_trend_ema_cross":
            fast = df.ewm(span=strategy.entry_params['fast_period'], adjust=False).mean()
            slow = df.ewm(span=strategy.entry_params['slow_period'], adjust=False).mean()
            # Crossover logic: Fast crosses above Slow
            # Fast > Slow AND PrevFast <= PrevSlow
            # Actually, we just need the condition. The engine loop checks signal[i-1] so "True" means "Buy Next Open"

            cond = (fast['close'] > slow['close']) & (fast['close'].shift(1) <= slow['close'].shift(1))

            if strategy.entry_params.get('adx_filter'):
                cond = cond & (df['adx_14'] > strategy.entry_params['adx_threshold'])

            signals = cond

        elif strategy.entry_block == "entry_breakout_donchian":
            period = strategy.entry_params['period']
            # We need to recompute donchian with dynamic period if not standard 20
            # Optimization: don't recompute if period is 20
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
            # If dynamic RSI period needed, recompute. Assuming 14 for speed or implementing dynamic later.
            # Using standard 14 for now as strict optimization.
            # To support dynamic period:
            if strategy.entry_params['rsi_period'] != 14:
                 rsi = VectorizedIndicators.rsi(df['close'], strategy.entry_params['rsi_period'])

            cond = rsi < strategy.entry_params['oversold']
            signals = cond

        return signals
