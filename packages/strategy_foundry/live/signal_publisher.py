import json
import os
import pandas as pd
from datetime import datetime
import pytz

from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.live.market_hours import LiveMarketHours
from packages.strategy_foundry.data.loader import DataLoader

RESULT_FILE = "packages/strategy_foundry/results/live_signal.json"

class SignalPublisher:
    def __init__(self, instrument="NIFTY"):
        self.instrument = instrument
        self.champion_store = ChampionStore(instrument)
        self.market_hours = LiveMarketHours()
        self.loader = DataLoader()
        self.generator = StrategyGenerator()

    def publish(self):
        # 1. Check Market Hours
        if not self.market_hours.is_market_open():
            self._write_result("SKIPPED", "Market Closed")
            return

        # 2. Load Champion
        champion_data = self.champion_store.load_current_champion()
        if not champion_data:
            self._write_result("SKIPPED", "No Champion")
            return

        strategy = champion_data['strategy']

        # 3. Load Data
        # We need UP TO DATE data.
        # The loader uses Yahoo daily. Yahoo daily might NOT have today's bar until close.
        # For "Live Signal" (Next Open), we generate signal based on COMPLETED bars.
        # So we need data up to yesterday.
        # If we run this hourly during market, we are effectively predicting for *tomorrow* open?
        # Or if "Timeframe: Daily", signals are generated at Close (or after) for Next Open.

        # If we run hourly, and today is trading day:
        # We likely only have data up to Yesterday Close.
        # So the signal is for Today Open.
        # But Today Open has passed.

        # If we want to trade *tomorrow*, we wait for today close.
        # If we want to trade *today*, we needed signal yesterday.

        # The requirement: "Run hourly... Publish live_signal.json if eligible & market open".
        # If market is open, it means we are IN the session.
        # Signal based on Daily bars (yesterday close) is valid for Today.
        # But we can't enter at "Next Bar Open" (Today Open) because it passed.

        # However, the instructions say: "Execution: next-bar open".
        # And "Market hours: ... Mon-Fri, 09:15-15:30".

        # Maybe the signal is "Current Stance"?
        # "signal": -1|0|1

        # If the strategy says "Be Long Today", and we are in the middle of Today.
        # The signal should be 1.
        # The consumer (bridge) decides how to enter (e.g. at market/limit if missed open).

        # So, we take history (up to yesterday), generate positions.
        # The last position in the series corresponds to TODAY.
        # (Series index T means signal generated at T (Close) for T+1).
        # Wait, `generate_positions` logic:
        # `if signal_values[i-1] == 1: Enter Open[i]`.
        # So we want `pos_array[last]`.

        df = self.loader.get_data(self.instrument)
        # Ensure we have enough data
        if df.empty:
            self._write_result("SKIPPED", "No Data")
            return

        # 4. Run Strategy
        # We need to run on the whole history (or window) to get state (risk overlay is stateful).
        raw_signals = self.generator.generate_positions(df, strategy)
        positions = self.generator.apply_risk_overlay(df, raw_signals, strategy)

        # The dataframe `df` contains historical daily bars.
        # The last row `df.iloc[-1]` is the last completed day (Yesterday).
        # `positions.iloc[-1]` is the position state for Yesterday?

        # Let's trace `apply_risk_overlay`.
        # `dates` correspond to `df` index.
        # `pos_array[i]` is position held during bar i.
        # `entry_price` was `open_prices[i]`.

        # If `df` ends at Yesterday.
        # `pos_array[-1]` is position held Yesterday.
        # We need position for Today (Next Bar).

        # `apply_risk_overlay` iterates up to `n`.
        # It determines state for `i` based on `signal[i-1]` (Yesterday Close) and `in_trade` state.

        # But we don't have a row for "Today" in `df`.
        # So `apply_risk_overlay` stops at Yesterday.

        # We need to predict for T+1.
        # Logic:
        # 1. Are we `in_trade` at end of Yesterday?
        #    If yes, check exits (SL/TP) against... we don't have Today's prices yet.
        #    So we signal "Hold/1" (unless Time Stop at Open).
        # 2. If not `in_trade`, check `signal[-1]` (Yesterday Close).
        #    If 1, we signal "Enter/1".

        # So we effectively need to run one more step of the loop for "Today" with unknown OHLC.
        # But we can know the "Intent".

        # Let's peek into `apply_risk_overlay` logic or implement "Next Position" logic here.

        # Re-run generator?
        # `raw_signals` has signal at -1.
        last_signal = raw_signals.iloc[-1]

        # We need `in_trade` state.
        # `positions` series tells us if we were in trade Yesterday.
        was_in_trade = positions.iloc[-1] == 1

        # We need more state: Entry Price, Bars Held.
        # Since `apply_risk_overlay` doesn't return full state, we might need to modify it or re-simulate.
        # For MVP, let's assume we can infer or simpler logic.

        # If was_in_trade:
        #   Signal = 1 (Hold)
        #   (We can't check SL/TP without Today's price, so assumption is Hold until broker handles SL/TP or we update)
        #   Actually, the JSON output has "risk": {"stop":...}.
        #   So we should export the SL levels!

        # If not was_in_trade:
        #   If last_signal == 1:
        #     Signal = 1 (Enter)

        # To get the SL/TP levels, we really need the state from the loop.
        # I will modify `generate.py` or just copy the loop logic here briefly to extract state.

        # Let's do a quick re-simulation of the LAST trade to find state.
        # Find last 0->1 transition in `positions`.

        # Optimization:
        # `apply_risk_overlay` doesn't expose state.
        # But we can modify `StrategyGenerator` or just subclass/augment it?
        # Or parse `positions`?

        # If `positions` is 1 at end.
        # Find when it started.
        series = positions.values
        if series[-1] == 1:
            # Backtrack
            idx = len(series) - 1
            while idx >= 0 and series[idx] == 1:
                idx -= 1
            entry_idx = idx + 1
            # Entry details
            entry_price = df['open'].iloc[entry_idx]
            # We need ATR at entry (entry_idx-1)
            atr_series = self.generator.apply_risk_overlay.__globals__['IndicatorsAdapter'].atr(df, period=14).values
            entry_atr = atr_series[entry_idx-1]
            if pd.isna(entry_atr): entry_atr = entry_price * 0.01

            sl_dist = strategy.stop_loss_atr * entry_atr
            stop_loss = entry_price - sl_dist
            take_profit = entry_price + (strategy.take_profit_atr * entry_atr)

            current_signal = 1
        else:
            # Not in trade. Check for new entry.
            if last_signal == 1:
                # Potential Entry Today
                current_signal = 1
                # Estimate SL based on Yesterday ATR
                atr_series = self.generator.apply_risk_overlay.__globals__['IndicatorsAdapter'].atr(df, period=14).values
                last_atr = atr_series[-1]
                if pd.isna(last_atr): last_atr = df['close'].iloc[-1] * 0.01

                # We don't know Entry Price (Today Open).
                # Use Yesterday Close as proxy for reporting risk params?
                # Or output "ATR" distance.
                stop_loss = "OPEN - " + str(strategy.stop_loss_atr * last_atr)
                take_profit = "OPEN + " + str(strategy.take_profit_atr * last_atr)

                # JSON schema says "risk": {"stop": "ATR"...}
            else:
                current_signal = 0
                stop_loss = None
                take_profit = None

        # 5. Write Output
        self._write_result("OK", "Generated", {
            "timestamp_ist": datetime.now(pytz.timezone('Asia/Kolkata')).isoformat(),
            "champion_id": strategy.strategy_id,
            "instrument": self.instrument,
            "signal": int(current_signal),
            "rule_summary": str(strategy.entry_rules), # Improve string repr
            "risk": {
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "max_bars": strategy.max_bars_hold
            }
        })

    def _write_result(self, status, reason, data=None):
        out = {
            "status": status,
            "reason": reason,
            "timestamp_gen": datetime.now().isoformat()
        }
        if data:
            out.update(data)

        with open(RESULT_FILE, 'w') as f:
            json.dump(out, f, indent=2)

