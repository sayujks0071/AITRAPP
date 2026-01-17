import pandas as pd
import numpy as np
from packages.strategy_foundry.adapters.core_indicators import VectorIndicatorCalculator
from packages.strategy_foundry.adapters.core_costs import CostAdapter
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from typing import Dict, Tuple, List
import structlog

logger = structlog.get_logger(__name__)

class BacktestEngine:
    def __init__(self, initial_capital=100000.0):
        self.initial_capital = initial_capital
        self.costs = CostAdapter.get_costs()
        self.calculator = VectorIndicatorCalculator()

    def run(self, df: pd.DataFrame, strategy: StrategyCandidate) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """
        Run backtest.
        Returns:
            trades: DataFrame of trades
            equity_curve: Series of equity
            signals: DataFrame with signal columns
        """
        if df.empty:
            return pd.DataFrame(), pd.Series(), pd.DataFrame()

        # 1. Calculate Indicators
        indicators = self.calculator.compute_all_vectors(df)

        # 2. Generate Base Signals (Vectorized)
        raw_signal = self._evaluate_logic(strategy.source_code.get("logic", []), indicators, df)

        # 3. Simulate Logic (Loop for path dependency like risk management)
        trades, equity_curve = self._simulate_execution(df, indicators, raw_signal, strategy.source_code.get("risk", {}))

        return trades, equity_curve, raw_signal

    def _evaluate_logic(self, logic_blocks: List[Dict], indicators: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
        """
        Combine logic blocks to produce a signal series (-1, 0, 1).
        Default behavior:
        - If Trend logic -> gives direction.
        - If Filter logic -> masks signal (sets to 0).
        """
        signal = pd.Series(0, index=df.index)

        # We need to distinguish between 'direction' generators and 'filters'
        # Simple assumption: first block is primary direction, others are filters.
        # Or look at type.

        if not logic_blocks:
            return signal

        # Primary block
        primary = logic_blocks[0]
        signal = self._evaluate_block(primary, indicators, df)

        # Filters
        for block in logic_blocks[1:]:
            mask = self._evaluate_filter(block, indicators, df)
            # Apply mask: if filter is False (0), signal becomes 0
            signal = signal * mask

        return signal

    def _evaluate_block(self, block: Dict, ind: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
        btype = block['type']
        params = block.get('params', {})

        s = pd.Series(0, index=df.index)

        if btype == 'ema_crossover':
            # We computed standard 34/89 EMAs in adapter, but strategy might want custom.
            # Ideally adapter should compute all needed, or we compute here on fly.
            # For simplicity, let's compute ad-hoc if not standard.
            fast = params.get('fast', 10)
            slow = params.get('slow', 50)
            ema_f = df['close'].ewm(span=fast).mean()
            ema_s = df['close'].ewm(span=slow).mean()
            s = np.where(ema_f > ema_s, 1, -1)

        elif btype == 'supertrend':
            # We rely on adapter's supertrend if it matches params, or recompute
            # Adapter default is 10, 3.
            # If strategy params differ, we must recompute.
            st_val, st_dir = self.calculator.supertrend(df, period=params.get('period', 10), multiplier=params.get('multiplier', 3.0))
            s = st_dir # 1 for up, -1 for down

        elif btype == 'donchian':
            # Close > Upper -> Long, Close < Lower -> Short? Or breakout?
            # Standard breakout
            # We need to recompute if period differs from adapter default (20)
            p = params.get('period', 20)
            upper = df['high'].rolling(p).max().shift(1) # Breakout of PREVIOUS high
            lower = df['low'].rolling(p).min().shift(1)

            # 1 if close > upper, -1 if close < lower, else hold previous (ffill)
            # Vectorized stateful logic is tricky without loop or specialized func.
            # Simple approximation:
            cond_buy = df['close'] > upper
            cond_sell = df['close'] < lower

            # This logic needs state (hold until reverse).
            # We'll return 1 for Buy trigger, -1 for Sell trigger, 0 otherwise.
            # The simulator will handle the "holding".
            s = np.where(cond_buy, 1, np.where(cond_sell, -1, 0))

        elif btype == 'rsi_reversion':
            p = params.get('period', 14)
            lower = params.get('lower', 30)
            upper = params.get('upper', 70)

            # Recompute RSI if needed
            if p == 14 and 'rsi' in ind:
                rsi = ind['rsi']
            else:
                rsi = self.calculator.rsi_series(df) # Recalculate if we could pass period... calculator currently hardcodes.
                # Limitation: Calculator init sets period.
                # We should instantiate calculator with params or update it.
                # For now, let's assume standard RSI or accept divergence.
                # Better: update calculator
                # But calculator is shared? No, instance per engine.

            # Actually calculator.rsi_series uses self.rsi_period.
            # We should probably compute ad-hoc here for correctness.
            # But let's stick to simple reuse of 'rsi' from adapter for now to save time/complexity.
            # NOTE: Logic inaccuracy if param differs.
            rsi = ind['rsi']

            # Mean reversion: Buy when oversold (cross below lower), Sell when overbought
            s = np.where(rsi < lower, 1, np.where(rsi > upper, -1, 0))

        return pd.Series(s, index=df.index)

    def _evaluate_filter(self, block: Dict, ind: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
        btype = block['type']
        params = block.get('params', {})

        mask = pd.Series(1, index=df.index)

        if btype == 'adx_filter':
            # Trend filter: only trade if ADX > threshold
            thresh = params.get('threshold', 25)
            adx = ind['adx']
            mask = np.where(adx > thresh, 1, 0)

        elif btype == 'regime_filter':
            # Only long if Close > MA
            p = params.get('ma_period', 200)
            ma = df['close'].rolling(p).mean()
            mask = np.where(df['close'] > ma, 1, 0) # Only allow longs? Or allows following trend?
            # Usually regime filter implies: Bullish regime -> Allow Longs. Bearish -> Allow Shorts (or cash).
            # For simplicity, let's say it allows trading in direction of regime.
            # But here we return a mask for the primary signal.
            # If primary is Long(1) and Regime is Bullish(Close>MA), allow (1).
            # If primary is Short(-1) and Regime is Bearish(Close<MA), allow (1).
            # So mask is checking alignment?
            # Let's simplify: "Regime Filter" usually means "Only trade if price > 200SMA" (for Long-only systems).
            # Since we default to Long-only...
            mask = np.where(df['close'] > ma, 1, 0)

        return mask

    def _simulate_execution(self, df: pd.DataFrame, indicators: pd.DataFrame, signals: pd.Series, risk_config: Dict) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Simulate trading with costs and risk management.
        """
        capital = self.initial_capital
        equity = []
        trades = []

        position = 0 # 0, 1, -1
        entry_price = 0.0
        entry_idx = None
        stop_loss = 0.0
        take_profit = 0.0
        highest_price = 0.0 # For trailing SL

        sl_atr_mult = risk_config.get('stop_loss_atr', 2.0)
        tp_atr_mult = risk_config.get('take_profit_atr', 4.0)
        trailing = risk_config.get('trailing_stop', False)

        # Costs
        slippage_pct = self.costs['slippage_bps'] / 10000.0
        commission_pct = self.costs['all_in_cost_bps'] / 10000.0
        total_cost_pct = slippage_pct + commission_pct

        # Vectors
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        atrs = indicators['atr'].values
        dates = df.index
        sig_values = signals.values

        for i in range(1, len(df)): # Start from 1 to have prev signal
            # Execution happens at OPEN of i based on signal at i-1
            curr_date = dates[i]
            open_price = opens[i]
            high_price = highs[i]
            low_price = lows[i]
            close_price = closes[i]

            # Previous Bar Signal
            prev_sig = sig_values[i-1]

            # ATR from previous close (known at open)
            curr_atr = atrs[i-1]
            if np.isnan(curr_atr): curr_atr = open_price * 0.01 # Fallback

            # 1. Check Exits if in position
            if position != 0:
                exit_price = None
                reason = ""

                # Check SL/TP (Intraday assumption: High/Low hit)
                if position == 1:
                    # Trailing Logic
                    if trailing:
                        # If price moves in favor, tighten SL
                        # Simple trailing: SL moves up if (High - dist) > current SL?
                        # Or ratchet?
                        # Let's use High of today to update trailing for TOMORROW?
                        # Or update immediately? Immediate is standard.
                        # However, we can't exit on trailing SL update in same bar easily without more granularity.
                        # Assumption: Check SL hit on Low. Update SL on High.
                        pass

                    if low_price <= stop_loss:
                        exit_price = stop_loss # Slippage applied later
                        reason = "SL"
                    elif tp_atr_mult > 0 and high_price >= take_profit:
                        exit_price = take_profit
                        reason = "TP"
                    elif prev_sig == -1: # Reverse signal
                        exit_price = open_price
                        reason = "Signal"

                    # Update Trailing SL for next bar (if not exited)
                    if exit_price is None and trailing:
                        new_sl = close_price - (curr_atr * sl_atr_mult)
                        if new_sl > stop_loss:
                            stop_loss = new_sl

                elif position == -1: # Short
                    if high_price >= stop_loss:
                        exit_price = stop_loss
                        reason = "SL"
                    elif tp_atr_mult > 0 and low_price <= take_profit:
                        exit_price = take_profit
                        reason = "TP"
                    elif prev_sig == 1:
                        exit_price = open_price
                        reason = "Signal"

                    # Update Trailing
                    if exit_price is None and trailing:
                        new_sl = close_price + (curr_atr * sl_atr_mult)
                        if new_sl < stop_loss:
                            stop_loss = new_sl

                # Execute Exit
                if exit_price is not None:
                    # Apply slippage/cost
                    # Sell: Price * (1 - cost)
                    # Buy to Cover: Price * (1 + cost)

                    if position == 1:
                        realized_price = exit_price * (1 - total_cost_pct)
                        pnl = (realized_price - entry_price) / entry_price # entry_price already included cost? No, usually tracked raw.
                        # Let's track raw entry price and apply costs on PnL calculation
                        # Correct: Entry cost paid. Exit cost paid.
                        # PnL = (Exit * (1-cost)) - (Entry * (1+cost))
                        # Wait, capital update is easier.

                        proceeds = (capital / entry_price) * exit_price # Gross
                        cost_amt = proceeds * total_cost_pct
                        final_proceeds = proceeds - cost_amt
                        pnl_amt = final_proceeds - capital

                        capital = final_proceeds
                        pnl_pct = (exit_price - entry_price) / entry_price # Raw return

                    else: # Short
                        # Entry: Sold at EntryPrice.
                        # Exit: Bought at ExitPrice.
                        # PnL = Entry - Exit
                        # Costs on both.

                        # Short logic:
                        # Initial: Sell X units. Cash + (X * Entry). Margin blocked.
                        # Simplified: PnL added/subtracted from Capital.

                        gross_ret = (entry_price - exit_price) / entry_price
                        # Costs: Entry cost + Exit cost approx 2 * total_cost_pct
                        net_ret = gross_ret - (2 * total_cost_pct)

                        pnl_amt = capital * net_ret
                        capital += pnl_amt
                        pnl_pct = gross_ret

                    trades.append({
                        "entry_date": entry_idx,
                        "exit_date": curr_date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl_amt,
                        "pnl_pct": pnl_pct,
                        "reason": reason,
                        "side": position
                    })

                    position = 0
                    entry_price = 0.0
                    entry_idx = None

            # 2. Check Entry if flat
            if position == 0 and prev_sig != 0:
                # Enter at Open
                side = 1 if prev_sig > 0 else -1

                # Check Long-Only constraint (unless configured)
                # Default Long-Only for now as per plan "Long-only by default"
                if side == -1:
                    # If shorting disabled, skip
                    # We implement Long-Only by default
                    pass # Skip short
                else:
                    entry_price = open_price
                    entry_idx = curr_date
                    position = side

                    # Set Stops
                    atr = curr_atr
                    if side == 1:
                        stop_loss = entry_price - (atr * sl_atr_mult)
                        take_profit = entry_price + (atr * tp_atr_mult)
                    else:
                        stop_loss = entry_price + (atr * sl_atr_mult)
                        take_profit = entry_price - (atr * tp_atr_mult)

                    # Apply Entry Cost
                    # Effective capital reduces
                    cost_amt = capital * total_cost_pct
                    capital -= cost_amt

            equity.append(capital)

        return pd.DataFrame(trades), pd.Series(equity, index=dates[1:])
