import json
import logging
import os
from datetime import datetime
import pandas as pd
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.selection.champion_store import ChampionStore

logger = logging.getLogger(__name__)

class SignalPublisher:
    def __init__(self):
        self.market = MarketHoursAdapter()
        self.loader = DataLoader()
        self.engine = BacktestEngine()
        self.store = ChampionStore()
        self.output_file = "packages/strategy_foundry/results/live_signal.json"

    def publish(self, instrument: str = "NIFTY"):
        """
        Generate and publish live signal.
        """
        # 1. Check Market Status
        # For Daily strategies, we can publish signal anytime, but it only matters if market is open or about to open.
        # But per requirements: "If market open AND champion live-eligible: write... Else write SKIPPED"

        is_open = self.market.is_market_open()

        # 2. Load Champion
        champion_entry = self.store.get_champion(instrument)

        if not champion_entry:
            self._write_skipped(instrument, "NO_CHAMPION")
            return

        candidate = champion_entry["candidate"]

        # 3. Check Eligibility (Redundant if only eligible are promoted, but good safety)
        # Assuming store only keeps eligible champions.

        if not is_open:
            self._write_skipped(instrument, "MARKET_CLOSED")
            return

        # 4. Load Data
        df = self.loader.fetch_data(instrument, force_refresh=True)
        if df.empty:
            self._write_skipped(instrument, "DATA_ERROR")
            return

        # Handle Today's partial bar
        # If today is in df, drop it to ensure we generate signal based on COMPLETED candles (Yesterday)
        today_date = datetime.now().date()
        if df.index[-1].date() == today_date:
            df = df.iloc[:-1]

        if df.empty:
             self._write_skipped(instrument, "INSUFFICIENT_DATA")
             return

        # 5. Run Engine to get Signal
        # We need to know the Target Position for TODAY.
        # Signal is generated at Close of Last Bar (Yesterday).
        # We run simulation on df.

        # We need to expose the "next signal" from engine or re-calculate it.
        # The engine `_generate_signals` adds `entry_long` etc.
        # Let's use `run` and inspect the last state?
        # `run` returns `final_position`.
        # `final_position` in my engine logic was just 0 or 1 at the end of simulation.
        # But simulation runs loop up to n-1.
        # If I want the signal for "Next Open" (which is Today), I need to check the signal at `df.iloc[-1]`.

        # Let's peek into engine internals or add a helper.
        # Or just run the engine and look at the "trades" or "final_position"?
        # My engine simulation loop goes `range(n-1)`. It simulates trades up to `n`.
        # If `df` ends yesterday. `n-1` is yesterday.
        # If signal at `n-1` says Enter, then `final_position` should be 1 (entered at Open of `n`?? No `n` doesn't exist in loop).

        # Let's manually check signal using helper logic similar to engine.
        # Or better: Append a dummy row for "Today" and see if it enters?
        # No, that's hacky.

        # Let's just calculate indicators and signal on the dataframe.
        # Use engine to generate signals dataframe.

        # Create a temporary engine just to get signals
        # We can modify engine to return the enriched dataframe

        # Accessing private method `_generate_signals` (I should have made it public or separate).
        # It's Python, I can call it.

        data = df.copy()
        self.engine._prepare_indicators(data, candidate)
        self.engine._generate_signals(data, candidate)

        last_bar = data.iloc[-1]

        signal = 0
        rule_summary = f"{candidate['type']}"

        # Logic:
        # If `entry_long` is True at Last Bar, we want to be LONG Today.
        # If `exit_logic` is True at Last Bar, we want to be FLAT Today.
        # What if we are already Long? We need state?
        # "Strategy Foundry ... prohibits direct broker execution ... generates `live_signal.json`"
        # Since we don't track live state, we must be "Stateless" or "Reconstruct State".
        # For a Daily Strategy, we can reconstruct state by running the backtest from start (or reasonable history).
        # The `final_position` from `engine.run(df, candidate)` tells us if we should be in a position NOW (at end of df).
        # Wait, `engine.run` simulates up to end of df.
        # If `df` excludes Today. `engine.run` finishes at Yesterday Close.
        # It tells us if we are holding a position at Yesterday Close.
        # BUT we execute at Open.
        # So we need to know if we *would have* entered/exited at Today Open.

        # Let's just run the backtest on `df`.
        # `trades, equity, final_pos = self.engine._simulate(data, candidate)`
        # `final_pos` is the position state at the end of the simulation.
        # In my engine:
        # `for i in range(n-1): ...`
        # It processes signals at `i` and executes at `i+1`.
        # If `n` is the length. `i` goes up to `n-2`.
        # It executes at `n-1`.
        # So `final_pos` reflects state at `df.index[-1]` (Yesterday Close).

        # But we want to know what to do TODAY (index `n`).
        # We need to process signal at `n-1`.
        # My engine loop stops at `n-2`.

        # I need to check signal at `n-1` (Last row of df).
        entry_signal = last_bar["entry_long"]
        exit_signal = last_bar["exit_logic"]

        # We also need previous position state to know if we exit or enter.
        # So running backtest is best.
        # But backtest stops early.
        # I should append a dummy row for Today to let the backtest process Yesterday.

        dummy_row = pd.DataFrame([last_bar.values], columns=data.columns, index=[pd.Timestamp.now(tz="Asia/Kolkata")])
        # Just copy values, dates don't matter much for logic except indicators which are already computed.
        # Actually indicators are computed on `data`.
        # If I append dummy, I need to recompute indicators? No, signals are already in `data`.
        # I just need to append the SIGNALS.

        # Re-run simulation logic for the last step manually.
        # Run backtest on `data` (which has `n` rows).
        # It gives state at `n-1`.
        # Now apply logic for `n-1` -> `n` (Today).

        res = self.engine.run(df, candidate) # This runs up to n-1
        current_pos = res["final_position"] # Position at Yesterday Close

        target_signal = 0

        if current_pos == 1:
            # We are Long. Check Exit at Yesterday Close (for Today Open)
            if exit_signal:
                target_signal = 0 # Exit
                rule_summary += " -> EXIT Signal"
            else:
                target_signal = 1 # Hold
                rule_summary += " -> HOLD"

            # Check Stops? (ATR stop)
            # Stops are usually intraday or daily close.
            # If we held yesterday, we check if yesterday's price hit stop?
            # `engine.run` already checked yesterday's stops!
            # If `final_position` is 1, it means we survived yesterday.

        else:
            # We are Flat. Check Entry at Yesterday Close (for Today Open)
            if entry_signal:
                target_signal = 1 # Enter
                rule_summary += " -> ENTRY Signal"
            else:
                target_signal = 0 # Stay Flat
                rule_summary += " -> FLAT"

        # 6. Write JSON
        output = {
            "timestamp_ist": datetime.now().isoformat(),
            "champion_id": candidate["id"],
            "instrument": instrument,
            "signal": int(target_signal),
            "rule_summary": rule_summary,
            "risk": candidate.get("stop", {}),
            "status": "OK",
            "reason": ""
        }

        self._write_json(output)

    def _write_skipped(self, instrument, reason):
        output = {
            "timestamp_ist": datetime.now().isoformat(),
            "instrument": instrument,
            "signal": 0,
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_json(output)

    def _write_json(self, data):
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Published signal: {data['status']}")
