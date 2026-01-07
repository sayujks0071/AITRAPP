"""
Backtest Engine
Intraday-capable backtest engine with support for various strategy blocks.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.adapters.core_market_hours import MARKET_CLOSE

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0):
        self.data = data
        self.initial_capital = initial_capital
        # Default Costs
        self.slippage_bps = 2.0
        self.commission_bps = 3.0 # per side
        self.spread_guard_bps = 1.0

    def run(self, strategy: StrategyConfig) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Run backtest for a given strategy.
        Returns: (trades_df, equity_curve)
        """
        if self.data.empty:
            return pd.DataFrame(), pd.Series()

        df = self.data.copy()

        # 1. Calculate Indicators
        df = self._calculate_indicators(df, strategy)

        # 2. Generate Entries
        entries = self._generate_entries(df, strategy)

        # 3. Simulate Trades
        trades, equity = self._simulate(df, entries, strategy)

        return trades, equity

    def _calculate_indicators(self, df: pd.DataFrame, strategy: StrategyConfig) -> pd.DataFrame:
        # Entry Indicators
        if strategy.entry_block == "breakout_donchian":
            period = strategy.entry_params['period']
            df['upper'] = df['High'].rolling(window=period).max().shift(1)
            df['lower'] = df['Low'].rolling(window=period).min().shift(1)

        elif strategy.entry_block == "trend_ema_cross":
            fast = strategy.entry_params['fast']
            slow = strategy.entry_params['slow']
            df['ema_fast'] = df['Close'].ewm(span=fast).mean()
            df['ema_slow'] = df['Close'].ewm(span=slow).mean()

        elif strategy.entry_block == "mean_reversion_rsi":
            period = strategy.entry_params['period']
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

        # ATR for stops
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()

        # Filter Indicators
        if strategy.filter_block == "trend_filter_ema":
            p = strategy.filter_params['period']
            df['filter_ema'] = df['Close'].ewm(span=p).mean()

        return df

    def _generate_entries(self, df: pd.DataFrame, strategy: StrategyConfig) -> pd.Series:
        entries = pd.Series(0, index=df.index) # 1: Long, -1: Short

        # Signal Logic
        long_condition = pd.Series(False, index=df.index)

        if strategy.entry_block == "breakout_donchian":
            long_condition = df['Close'] > df['upper']

        elif strategy.entry_block == "trend_ema_cross":
            long_condition = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))

        elif strategy.entry_block == "mean_reversion_rsi":
            long_condition = df['rsi'] < strategy.entry_params['lower']

        # Filters
        if strategy.filter_block == "trend_filter_ema":
            long_condition = long_condition & (df['Close'] > df['filter_ema'])

        if strategy.filter_block == "time_filter_chop":
            # e.g., after 09:45
            start_time = pd.to_datetime(strategy.filter_params['start_time'], format="%H:%M").time()
            long_condition = long_condition & (df.index.time >= start_time)

        # Market Hours Filter (No new entries after 15:20)
        # Assuming index is in IST
        entry_cutoff = pd.to_datetime("15:20", format="%H:%M").time()
        long_condition = long_condition & (df.index.time < entry_cutoff)

        entries[long_condition] = 1
        return entries

    def _simulate(self, df: pd.DataFrame, entries: pd.Series, strategy: StrategyConfig) -> Tuple[pd.DataFrame, pd.Series]:
        trades = []
        equity_curve = []

        capital = self.initial_capital
        position = 0 # 0: Flat, 1: Long
        entry_price = 0.0
        stop_price = 0.0
        target_price = 0.0
        entry_time = None

        idx_list = df.index.tolist()
        close_arr = df['Close'].values
        high_arr = df['High'].values
        low_arr = df['Low'].values
        atr_arr = df['atr'].values

        # Convert entries to numpy for speed
        entry_arr = entries.values

        for i in range(1, len(df)):
            current_time = idx_list[i]
            price = close_arr[i]

            # 1. Manage Open Position
            if position != 0:
                exit_signal = False
                exit_reason = ""
                exit_price = price

                # Check Stops/Targets (Intra-bar check approx)
                if low_arr[i] <= stop_price:
                    exit_signal = True
                    exit_reason = "SL"
                    exit_price = stop_price # Assume filled at stop
                elif strategy.exit_block == "simple_target_stop" and high_arr[i] >= target_price:
                    exit_signal = True
                    exit_reason = "TP"
                    exit_price = target_price

                # Trailing Stop
                if strategy.exit_block == "trailing_stop_atr" and not exit_signal:
                    new_stop = price - (atr_arr[i] * strategy.exit_params['multiplier'])
                    if new_stop > stop_price:
                        stop_price = new_stop

                # Time Stop / EOD
                # EOD: 15:25
                flat_time = pd.to_datetime("15:25", format="%H:%M").time()
                if current_time.time() >= flat_time:
                    exit_signal = True
                    exit_reason = "EOD"
                    exit_price = price

                if exit_signal:
                    # Calculate PnL
                    # Cost: Comm + Slippage + Spread Guard
                    # 10 bps total for conservative est?
                    # Cost = Price * (comm + slip)
                    total_cost_pct = (self.commission_bps + self.slippage_bps + self.spread_guard_bps) / 10000.0

                    gross_pnl = (exit_price - entry_price) * position # Only Long supported for now
                    cost_amt = (entry_price * total_cost_pct) + (exit_price * total_cost_pct)
                    net_pnl = gross_pnl - cost_amt

                    # Assuming 1 unit for simplicity, or fractional based on capital?
                    # Let's say fixed fractional: invest 100% capital
                    qty = capital / entry_price
                    trade_pnl = net_pnl * qty
                    capital += trade_pnl

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "reason": exit_reason,
                        "pnl": trade_pnl,
                        "return_pct": net_pnl / entry_price
                    })

                    position = 0

            # 2. Check for New Entry (if flat)
            # Execute on NEXT OPEN?
            # The prompt says: "Signal calculated on bar close; execute next bar open (no lookahead)."
            # My loop is iterating bar by bar. `i` is current bar.
            # If `entries[i-1]` was 1, we enter at Open of `i`.

            if position == 0:
                if entry_arr[i-1] == 1: # Signal from prev close
                    entry_time = current_time
                    entry_price = df['Open'].iloc[i] # Execute at Open
                    position = 1

                    # Set Stops
                    atr = atr_arr[i-1]
                    if np.isnan(atr): atr = entry_price * 0.01

                    if strategy.risk_block == "atr_stop":
                        stop_dist = atr * strategy.risk_params['multiplier']
                        stop_price = entry_price - stop_dist
                    elif strategy.risk_block == "percent_stop":
                        stop_dist = entry_price * (strategy.risk_params['pct'] / 100.0)
                        stop_price = entry_price - stop_dist
                    else:
                        stop_price = entry_price * 0.99

                    # Set Targets
                    if strategy.exit_block == "simple_target_stop":
                         risk = entry_price - stop_price
                         reward = risk * strategy.exit_params['rr_ratio']
                         target_price = entry_price + reward

            equity_curve.append({"time": current_time, "equity": capital})

        return pd.DataFrame(trades), pd.DataFrame(equity_curve).set_index("time")['equity']
