"""
Vectorized Backtest Engine.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.backtest.costs import BacktestCostModel

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0, cost_model: BacktestCostModel = None):
        self.initial_capital = initial_capital
        self.cost_model = cost_model or BacktestCostModel(slippage_bps=5, all_in_cost_bps=10) # Default simple

    def run(self, strategy: Strategy, df: pd.DataFrame, instrument_type: str = "EQUITY") -> Tuple[pd.Series, pd.DataFrame]:
        """
        Run backtest.
        Returns (Equity Curve, Trades DataFrame)
        """
        # 1. Generate Target Positions
        # This returns a series of -1, 0, 1 indicating DESIRED holding state at Close.
        # However, due to Risk Overlay (Stops), the position might change intra-bar (simulated).
        # The Grammar's apply_risk_overlay returns the "Actual End-of-Day Position".

        # Note: We assume execution happens at NEXT OPEN.
        # But if Stops are hit, they happen Intra-bar.

        # Let's clarify the logic in Grammar:
        # `apply_risk_overlay` returns the realized position series.
        # If I am Long at Close i, I hold it until Close i+1, unless stopped out.

        raw_signal = strategy.generate_positions(df)
        positions = strategy.apply_risk_overlay(df, raw_signal)

        # 2. Calculate PnL
        # Positions series: p[i] is the position held AT THE END of day i.
        # Entry/Exit assumption:
        # If p[i-1] != p[i]:
        #   We traded. When?
        #   Standard backtest: Trade at Open of i.
        #   But our positions are derived from Close i data?
        #   If `generate_positions` uses Close i, we can only trade at Open i+1.
        #   So we shift positions by 1?

        # Let's look at `apply_risk_overlay` implementation in Grammar.
        # It iterates. It updates position based on signal (from prev close?).
        # "sig = signals.iloc[i-1] # Signal from prev bar".
        # So `positions[i]` is indeed the position held during bar i (established at Open i).
        # Correct.

        # So p[i] is position held during day i.
        # Return on day i = (Close[i] - Open[i]) if we entered at Open?
        # Or (Close[i] - Close[i-1]) if we held from prev close?

        # Let's align:
        # p[i] is position held FROM Open[i] TO Close[i].
        # If p[i] != p[i-1], we adjusted at Open[i].
        # Return[i] = p[i] * (Close[i] - Close[i-1]) ... No.
        # If we entered at Open[i], Return[i] part 1 is (Close[i] - Open[i]).
        # If we exited at Open[i], Return[i] is 0 (for that trade).

        # Let's refine.
        # Market Open: check if p[i] != p[i-1].
        # Execute trade at Open[i].
        # Held throughout day i.
        # PnL[i] = p[i] * (Close[i] - Open[i]) ? No, this ignores Gap.
        # PnL comes from holding.
        # If we held from i-1 to i: PnL = p[i-1] * (Open[i] - Close[i-1]) [Gap] + p[i] * (Close[i] - Open[i]) [Intraday] ??

        # Simpler vectorization:
        # Shift positions to get "Position held at start of day i".
        # We trade at Open[i] to match `positions[i]`.
        # So we pay costs on `abs(positions[i] - positions[i-1])` at price `Open[i]`.
        # Daily Value Change = positions[i] * (Close[i] - Open[i])?
        # What about Gap?
        # If `positions[i]` represents "Position held during Day i", does it capture the Gap?
        # Usually, if we decide at Close i-1, we enter at Open i. We miss the Gap (Open i - Close i-1).
        # So our PnL for day i is `positions[i] * (Close[i] - Open[i])`.
        # Correct.

        # Costs:
        # Trade Qty = `abs(positions[i] - positions[i-1])`.
        # Price = `Open[i]`.

        # Wait, if `apply_risk_overlay` simulates stops at `stop_price`, then `positions[i]` might be 0 even if we entered at Open.
        # In that case, we held from Open to StopPrice.
        # This is hard to vectorize perfectly if logic is inside Strategy.

        # Compromise:
        # The `positions` series returned by strategy is "End of Day Position".
        # If p[i] == 0 and p[i-1] == 1, we exited.
        # Did we exit at Open or Stop?
        # If `apply_risk_overlay` handles it, it sets p[i]=0 if stopped.
        # If stopped, we need to know the EXIT PRICE.
        # The simple Series return [-1, 0, 1] loses the "Exit Price" info.

        # To do this accurately, `apply_risk_overlay` should probably return a DataFrame with `position` and `exit_price` (if any).
        # Or the Engine must run the loop.

        # Given the requirements "Backtest engine (auditable, no magic)", maybe I should move the loop to the Engine?
        # And strategy just returns "Target Signal".
        # Yes. That is better design.

        # Re-reading Plan: "Create packages/strategy_foundry/backtest/engine.py: Vectorized daily backtest engine".
        # If I iterate in engine, it's not vectorized. But Daily iteration is fast (5000 days is nothing).
        # I will implement an event-driven loop in the Engine for accuracy of Stops/Costs.

        # But wait, `grammar.py` already implements `apply_risk_overlay`.
        # The prompt says: "Unified interface ... apply_risk_overlay(df, positions) -> final_positions".
        # If the interface forces that, then the engine just takes `final_positions`.
        # If I only get `final_positions` (the series of 0, 1, -1), I don't know IF a stop was hit or if it was a signal exit.
        # AND I don't know the price.

        # Assumption:
        # If p[i] != p[i-1], trade happened at Open[i].
        # This implies we IGNORE intraday stops in the "Output PnL" calculation if we just use the series.
        # OR `apply_risk_overlay` modifies the position series such that p[i] becomes 0.
        # If p[i] becomes 0, we assume exit at Open[i+1]? No, that's too late.

        # FIX: The Strategy Interface `apply_risk_overlay` is likely intended for "Signal Filtering" (don't take this trade)
        # rather than "Intraday Execution Simulation".
        # BUT "ATR stop" is listed.

        # "Backtest engine ... Execution: next-bar open".
        # If Execution is Next-Bar Open, then stops must be on Next-Bar?
        # If I enter at Open, and Hit Stop same day, I exit at StopPrice.

        # I will implement the loop in `Engine.run` and ignore `apply_risk_overlay` for PnL calculation details,
        # OR I will treat `apply_risk_overlay` as the source of truth for POSITIONS, and assume all trades happen at OPEN.
        # If `apply_risk_overlay` removed a position due to stop, it sets p[i]=0.
        # If p[i]=0 and p[i-1]=1, we exit at Open[i+1] (standard Next-Bar).
        # This means the "Stop" is effectively "Exit at Next Open if Stop condition met today".
        # This is a valid interpretation for "Execution: next-bar open".
        # It's conservative (slippage due to gap).

        # I will stick to "Execution at Next Bar Open" strictly.
        # Logic:
        # 1. Strategy generates signals (incorporating risk logic -> deciding to exit).
        # 2. Signals[i] determines target for Day i+1.
        # 3. Trade happens at Open[i+1].

        # So:
        # positions = strategy.apply_risk_overlay(...)
        # trade_diff = positions.shift(1) - positions.shift(2) ??
        # Let's say pos[i] is the signal generated at Close[i].
        # Target holding for Day i+1 is pos[i].
        # Current holding (from Day i) is pos[i-1].
        # Change = pos[i] - pos[i-1].
        # Execute at Open[i+1].

        # This is robust and fully vectorized-friendly.
        # PnL[i+1] = pos[i] * (Close[i+1] - Open[i+1]) ? No.
        # If we enter at Open[i+1] and hold to Close[i+1].
        # Return = (Close[i+1] - Open[i+1]) / Open[i+1].

        # Wait, holding overnight?
        # "Timeframe: Daily (1D)".
        # Usually means we hold positions over days.
        # PnL for Day d:
        #   Held from d-1 (Close) to d (Close).
        #   Total Return = (Close[d] - Close[d-1]) / Close[d-1].
        #   Our exposure was determined at Close[d-1].
        #   So Strategy PnL[d] = pos[d-1] * Return[d].
        #   Transaction Costs are applied when pos[d-1] != pos[d-2].
        #   Exec price = Open[d]?
        #   If we execute at Open[d], the return (Close[d-1] to Open[d]) is MISSED/AVOIDED?
        #   If we change position at Open[d]:
        #     Old position held Close[d-1] -> Open[d].
        #     New position held Open[d] -> Close[d].

        # Correct Model for "Next Bar Open" execution:
        # Day d:
        #   Gap Return = (Open[d] - Close[d-1]) / Close[d-1]
        #   Intraday Return = (Close[d] - Open[d]) / Open[d]
        #
        #   PnL[d] = (pos[d-2] * Gap Return * Capital) + (pos[d-1] * Intraday Return * Capital) - Costs
        #
        #   Wait, `pos[d-1]` is the signal from yesterday close, executed at Open[d].
        #   So `pos[d-1]` is the "New Position" held during Intraday d.
        #   `pos[d-2]` was the "Old Position" held overnight into Open[d].

        # Yes, this is the correct model.

        # I will implement this vectorized logic.

        # 3. Trades list extraction
        # We need to reconstruct individual trades for metrics.

        # positions = positions.shift(1).fillna(0) # Shift signal to get "Holding during Day" (Intraday)
        # Wait, let's trace carefully.
        # Signal[i] generated at Close[i].
        # Execute at Open[i+1].
        # Holding at Open[i+1] becomes Signal[i].
        # So `held_intraday` series = `positions.shift(1)`.

        # Gap exposure: Holding from Close[i] to Open[i+1] is Signal[i-1].
        # `held_overnight` series = `positions.shift(2)`.

        # Actually, simpler:
        # We have a series of "Target Positions" `S`.
        # S[i] is target for day i+1.
        # At Open[i+1], we move from S[i-1] to S[i].

        # Let's align DataFrame.
        # df index: i.
        # Signal S[i] (available at Close i).
        # We define `Pos[i]` as the position held during the "Body" of candle i.
        # `Pos[i] = S[i-1]`.

        signal = positions # This is the "End of Day Target" from strategy

        # Derived Series
        pos_intraday = signal.shift(1).fillna(0) # Held from Open[i] to Close[i]
        pos_overnight = signal.shift(2).fillna(0) # Held from Close[i-1] to Open[i]

        # Returns
        ret_gap = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
        ret_intra = (df["close"] - df["open"]) / df["open"]

        # Strategy Return components
        pnl_gap = pos_overnight * ret_gap
        pnl_intra = pos_intraday * ret_intra

        # Costs
        # Turnover at Open[i]: Change in position * Price
        # Delta = pos_intraday - pos_overnight
        # But wait, pos_overnight is effectively pos_intraday[i-1].
        # So Delta = pos_intraday[i] - pos_intraday[i-1].
        # turnover_qty = abs(Delta) * (Capital / Price[i-1]?)
        # Vectorized PnL is usually in % terms.
        # Cost in % = (CostVal / Capital).
        # CostVal ~ Delta * Price * CostBps.
        # As % of Capital: Delta * CostBps. (Since Delta is % exposure if pos is -1/1).

        # If we assume Fixed Capital allocation (compounding or not? Prompt says "equity curve", usually compounding).
        # Let's assume compounding.

        # Cost deduction:
        # trades_vol = abs(pos_intraday - pos_overnight)
        # cost_pct = trades_vol * (slippage_bps + fee_bps) / 10000

        # Total Daily Return = pnl_gap + pnl_intra - cost_pct

        # Equity Curve = (1 + Total Daily Return).cumprod() * initial_capital

        strat_ret = pnl_gap + pnl_intra

        # Calculate costs
        # We need to estimate cost pct
        # We use a simplified bps model for vectorization
        # BacktestCostModel has estimate_cost which returns Value.
        # We need BPS equivalent.
        # If cost_model has `all_in_cost_bps`, use it.
        # Else default to 15 bps per side?

        # I'll add `get_bps` to CostModel or just use a default for vectorized.
        # The prompt says "output trades table".
        # So I probably need to iterate to generate the trades table anyway.
        # If I iterate, I can do exact cost calc.

        # Hybrid: Vectorized for Equity Curve (fast), Iteration for Trades Table (detail)?
        # Or just iterate for everything to be safe and consistent.
        # Daily iteration is very fast.

        return self._run_iterative(positions, df, instrument_type)

    def _run_iterative(self, target_positions: pd.Series, df: pd.DataFrame, instrument_type: str):
        # target_positions[i] = Target for i+1.

        equity = [self.initial_capital]
        cash = self.initial_capital
        holdings_qty = 0

        trades = []
        equity_series = []

        # Align: target_positions index matches df index.
        # S[i] is decision at Close[i]. Exec at Open[i+1].

        # We loop from i=0 to N-1.
        # At step i (Day i):
        # 1. Update Portfolio Value at Open[i] (Gap).
        # 2. Execute trades at Open[i] to match Target[i-1].
        # 3. Update Portfolio Value at Close[i] (Intraday).
        # 4. Record Equity.

        dates = df.index
        opens = df["open"].values
        closes = df["close"].values
        targets = target_positions.values

        current_target = 0 # Initial target (before day 0)

        for i in range(len(df)):
            date = dates[i]
            open_price = opens[i]
            close_price = closes[i]

            # 1. Execute at Open
            # Target comes from i-1
            desired_pos_sign = targets[i-1] if i > 0 else 0

            # Calculate desired qty based on current equity?
            # Or fixed size?
            # Usually compounding: Use current equity to size.
            # Qty = (Equity * desired_pos_sign) / OpenPrice
            # We assume 100% allocation for -1/1.

            # Do we rebalance every day?
            # Vectorized implies constant rebalancing to 100%.
            # Realistically, we hold qty.
            # If target sign is same, do we adjust qty?
            # "Strategy generated positions" usually implies exposure %.
            # Let's assume rebalance to target % at Open.

            current_equity = cash + (holdings_qty * open_price)

            desired_val = current_equity * desired_pos_sign
            desired_qty = int(desired_val / open_price)

            qty_delta = desired_qty - holdings_qty

            if qty_delta != 0:
                side = "BUY" if qty_delta > 0 else "SELL"
                exec_price = open_price # + slippage logic? CostModel handles it?

                # Cost
                cost = self.cost_model.estimate_cost(open_price, abs(qty_delta), side, instrument_type)

                # Execute
                cash -= (qty_delta * open_price)
                cash -= cost
                holdings_qty = desired_qty

                # Record Trade
                trades.append({
                    "entry_date": date, # Actually this mixes Entry/Exit/Rebal
                    "side": side,
                    "qty": abs(qty_delta),
                    "price": open_price,
                    "cost": cost,
                    "type": "REBALANCE" # Simplified
                })

            # 2. Mark to Market at Close
            current_equity_close = cash + (holdings_qty * close_price)
            equity.append(current_equity_close)
            equity_series.append(current_equity_close)

        # Post-process trades to match "Entry/Exit" pairs format if needed?
        # The prompt asks for "trades table". Usually means "Round Trip".
        # Rebalancing makes this messy.
        # Simplified logic: Only change qty if Sign changes?
        # If sign is same (1 -> 1), we hold. No rebalance.

        # Refined Logic:
        # Only trade if `targets[i-1] != targets[i-2]`.
        # If holding 1 and target is 1, keep holding same Qty.
        # This prevents daily cost bleed from rebalancing.

        return self._run_iterative_no_rebalance(target_positions, df, instrument_type)

    def _run_iterative_no_rebalance(self, target_positions: pd.Series, df: pd.DataFrame, instrument_type: str):
        equity_curve = []
        trades_list = []

        cash = self.initial_capital
        qty = 0

        dates = df.index
        opens = df["open"].values
        closes = df["close"].values
        targets = target_positions.values

        # State
        current_signal = 0 # 0, 1, -1

        # Helper for trade matching
        open_trade = None # {entry_price, entry_date, qty, side}

        for i in range(len(df)):
            # Decision for TODAY (Day i) comes from YESTERDAY (Day i-1)
            target = targets[i-1] if i > 0 else 0

            # Execution at Open[i]
            price = opens[i]

            # Check for signal change
            if target != current_signal:
                # We need to change position

                # 1. Close existing if any
                if current_signal != 0:
                    # Exit
                    side = "SELL" if current_signal == 1 else "BUY"
                    cost = self.cost_model.estimate_cost(price, abs(qty), side, instrument_type)

                    cash_inflow = (qty * price) if side == "SELL" else -(abs(qty) * price) # Wait.
                    # If Long (qty > 0), Sell: Cash += qty * price
                    # If Short (qty < 0), Buy: Cash -= abs(qty) * price (Pay to cover) -> Wait, short selling math.
                    # Cash flow on Short Entry: +Price. Exit: -Price.

                    # Let's use standard Cash accounting.
                    # Buy: Cash -= Price * Qty
                    # Sell: Cash += Price * Qty

                    cash += (qty * price) # Works for Sell (qty>0 -> +) and Cover (qty<0, but cover means BUYing positive qty to offset? No.)
                    # If I am short (qty = -10), I need to BUY 10.
                    # Trade is BUY 10. Cash -= 10 * Price.
                    # My qty becomes 0.
                    # My logic: `qty` variable holds signed quantity.
                    # To close -10, change is +10.
                    # Cash change = -(+10 * price) = -10*price.

                    trade_qty = abs(qty)
                    cash -= ((-qty) * price) # This is effectively closing.
                    cash -= cost

                    # Record Trade Close
                    if open_trade:
                        pnl = (price - open_trade['entry_price']) * open_trade['qty'] * (1 if open_trade['side']=='BUY' else -1)
                        pnl -= (open_trade['cost'] + cost)
                        trades_list.append({
                            "symbol": "N/A",
                            "entry_date": open_trade['entry_date'],
                            "exit_date": dates[i],
                            "side": open_trade['side'],
                            "entry_price": open_trade['entry_price'],
                            "exit_price": price,
                            "qty": open_trade['qty'],
                            "pnl": pnl,
                            "return_pct": (pnl / (open_trade['entry_price'] * open_trade['qty']))
                        })
                        open_trade = None

                    qty = 0

                # 2. Open new if target != 0
                if target != 0:
                    # Enter
                    # Size based on current equity
                    curr_equity = cash # Since qty is 0
                    alloc_val = curr_equity # 100% allocation

                    # Calculate qty
                    # If Short, we can sell `alloc_val`.
                    new_qty = int(alloc_val / price)
                    if new_qty > 0:
                        side = "BUY" if target == 1 else "SELL"
                        cost = self.cost_model.estimate_cost(price, new_qty, side, instrument_type)

                        signed_qty = new_qty if target == 1 else -new_qty

                        cash -= (signed_qty * price)
                        cash -= cost

                        qty = signed_qty

                        open_trade = {
                            "entry_date": dates[i],
                            "entry_price": price,
                            "qty": new_qty,
                            "side": side,
                            "cost": cost
                        }

                current_signal = target

            # Mark to Market at Close[i]
            # Equity = Cash + (Qty * ClosePrice)
            current_equity = cash + (qty * closes[i])
            equity_curve.append(current_equity)

        return pd.Series(equity_curve, index=df.index), pd.DataFrame(trades_list)
