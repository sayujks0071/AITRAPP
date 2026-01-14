import pandas as pd
import numpy as np
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.adapters.core_costs import CostsAdapter
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

class BacktestEngine:
    def __init__(self, df: pd.DataFrame, initial_capital=100000.0):
        self.df = df
        self.initial_capital = initial_capital
        self.generator = StrategyGenerator()
        self.costs_adapter = CostsAdapter()

    def run(self, strategy: StrategyConfig, instrument_type='EQUITY'):
        """
        Runs backtest for a single strategy.
        Assumes df has OHLC data.
        """
        # 1. Generate Raw Entry Signals
        raw_signals = self.generator.generate_positions(self.df, strategy)

        trades = []
        equity_curve = [1.0]

        opens = df["open"].values
        dates = df.index
        targets = target_pos.values

        current_pos = 0 # 0 or 1
        entry_price = 0.0
        entry_date = None

        capital = 1.0

        for i in range(len(df)):
            tgt = targets[i]
            price = opens[i]

            if tgt != current_pos:
                # Close existing
                if current_pos != 0:
                    if current_pos == 1:
                        # Long Exit (Sell)
                        exit_price = price * (1 - self.slip_bps/10000)
                        pnl_pct = (exit_price - entry_price) / entry_price
                    else:
                        # Short Exit (Buy to Cover)
                        exit_price = price * (1 + self.slip_bps/10000)
                        pnl_pct = (entry_price - exit_price) / entry_price

                    pnl_pct -= (self.fee_bps/10000) * 2

                    capital *= (1 + pnl_pct)

                    trades.append(Trade(
                        entry_date=entry_date,
                        exit_date=dates[i],
                        entry_price=entry_price,
                        exit_price=exit_price,
                        side=current_pos,
                        pnl=pnl_pct * entry_price,
                        pnl_pct=pnl_pct,
                        exit_reason="Signal"
                    ))

                # Open new
                if tgt != 0:
                    current_pos = tgt
                    if current_pos == 1:
                        # Long Entry (Buy)
                        entry_price = price * (1 + self.slip_bps/10000)
                    else:
                        # Short Entry (Sell)
                        entry_price = price * (1 - self.slip_bps/10000)

                    entry_date = dates[i]
                else:
                    current_pos = 0

        return {
            "trades": trades,
            "equity_curve": [],
            "final_capital": capital
        }

    def calculate_metrics(self, trades: List[Trade], initial_capital=100000.0) -> Dict[str, Any]:
        if not trades:
            return {"cagr": 0, "sharpe": 0, "max_dd": 0, "trades": 0, "total_return": 0}

        df_trades = pd.DataFrame([vars(t) for t in trades])
        df_trades['cum_pnl'] = (1 + df_trades['pnl_pct']).cumprod()

        total_ret = df_trades['cum_pnl'].iloc[-1] - 1
        n_years = (df_trades['exit_date'].max() - df_trades['entry_date'].min()).days / 365.25
        cagr = (1 + total_ret) ** (1/n_years) - 1 if n_years > 0 else 0
        # 2. Simulate P&L
        # Note: We duplicate logic from generator.apply_risk_overlay because we need granular Trade P&L,
        # whereas apply_risk_overlay returns only position state for Signal Generation.
        # Ideally, we should unify this logic in a shared component.

        return self._simulate_loop(self.df, raw_signals, strategy, instrument_type)

    def _simulate_loop(self, df: pd.DataFrame, entry_signals: pd.Series, config: StrategyConfig, instrument_type: str):
        # ... logic similar to apply_risk_overlay but recording P&L ...

        # Setup
        open_prices = df['open'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        dates = df['datetime'].values # assuming datetime column exists

        # Indicators needed for stops
        atr = IndicatorsAdapter.atr(df, period=14)
        # Ensure it's numpy array (adapter returns ndarray or Series depending on implementation details)
        if isinstance(atr, pd.Series):
            atr = atr.values

        n = len(df)
        equity = np.zeros(n)
        equity[0] = self.initial_capital
        current_capital = self.initial_capital

        trades = []

        in_trade = False
        entry_price = 0.0
        entry_idx = 0
        entry_date = None
        quantity = 0

        stop_loss = 0.0
        take_profit = 0.0

        signal_values = entry_signals.values

        for i in range(1, n):
            # Default: carry over capital
            equity[i] = equity[i-1]

            if in_trade:
                # Mark to market (Close)
                # Unrealized PnL
                curr_val = quantity * close_prices[i]
                # equity[i] = cash + curr_val
                # cash = current_capital - (quantity * entry_price) approx
                # Let's track Portfolio Value directly

                # Check Exits
                exit_price = 0.0
                exit_reason = ""
                bars_held = i - entry_idx

                # SL/TP logic on Low/High
                if low_prices[i] <= stop_loss:
                    exit_price = stop_loss # Assumes fill at SL
                    # Gap check: if Open < SL, we fill at Open
                    if open_prices[i] < stop_loss:
                         exit_price = open_prices[i]
                    exit_reason = "SL"
                elif high_prices[i] >= take_profit:
                    exit_price = take_profit
                    # Gap check: if Open > TP, fill at Open
                    if open_prices[i] > take_profit:
                        exit_price = open_prices[i]
                    exit_reason = "TP"
                elif bars_held >= config.max_bars_hold:
                    exit_price = open_prices[i] # Exit at Open of this bar?
                    # Or Close? "Time stop" usually at close of max bar or open of next.
                    # Let's say Open of this bar (after max bars passed).
                    exit_reason = "TIME"

                if exit_price > 0:
                    # Execute Exit
                    cost_est = self.costs_adapter.estimate_costs(instrument_type, exit_price, quantity)
                    proceeds = (exit_price * quantity) - cost_est.total_fees - cost_est.slippage

                    current_capital += proceeds
                    in_trade = False

                    trades.append({
                        "entry_date": entry_date,
                        "exit_date": dates[i],
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "quantity": quantity,
                        "pnl": proceeds - (quantity * entry_price), # Gross PnL - Exit Costs. Entry costs already deducted.
                        "reason": exit_reason
                    })

                    equity[i] = current_capital
                    continue # Next bar

                # Still in trade, update equity with Close price
                # We need to account for what capital would be if liquidated now
                # But we don't pay costs yet.
                unrealized_val = quantity * close_prices[i]
                equity[i] = current_capital + unrealized_val

            if not in_trade:
                # Check Entry (signal from i-1)
                if signal_values[i-1] == 1:
                    entry_price = open_prices[i]

                    # Risk Management for Sizing
                    # 1% risk
                    current_atr = atr[i-1]
                    if np.isnan(current_atr) or current_atr == 0:
                        current_atr = entry_price * 0.01

                    sl_dist = config.stop_loss_atr * current_atr
                    risk_per_share = sl_dist

                    # Capital to risk = 1% of current equity
                    risk_capital = equity[i] * 0.01

                    if risk_per_share > 0:
                        qty = int(risk_capital / risk_per_share)
                    else:
                        qty = 0

                    if qty > 0:
                        # Cost Check
                        cost_est = self.costs_adapter.estimate_costs(instrument_type, entry_price, qty)
                        total_cost = (entry_price * qty) + cost_est.total_fees + cost_est.slippage

                        if total_cost < equity[i]:
                            # Execute Entry
                            current_capital = equity[i] - total_cost
                            quantity = qty
                            in_trade = True
                            entry_idx = i
                            entry_date = dates[i]

                            stop_loss = entry_price - sl_dist
                            take_profit = entry_price + (config.take_profit_atr * current_atr)

                            # Update Equity (Mark to market at Open is Entry Price - Costs)
                            # Actually usually MTM at Close
                            unrealized_val = quantity * close_prices[i]
                            equity[i] = current_capital + unrealized_val

        # Use datetime index for equity curve if available
        idx = df['datetime'] if 'datetime' in df.columns else df.index

        return {
            "equity_curve": pd.Series(equity, index=idx),
            "trades": pd.DataFrame(trades)
        }
