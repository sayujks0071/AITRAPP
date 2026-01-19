"""
Live signal publisher.
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from packages.strategy_foundry.live.market_hours import LiveMarketHours
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.grammar import Strategy, EmaCrossEntry, RsiEntry, SupertrendEntry, AdxFilter, StrategyComponent
from packages.strategy_foundry.selection.promote import is_live_eligible

RESULTS_DIR = Path("packages/strategy_foundry/results")
LIVE_SIGNAL_FILE = RESULTS_DIR / "live_signal.json"

class SignalPublisher:
    def __init__(self):
        self.market_hours = LiveMarketHours()
        self.champion_store = ChampionStore()
        self.loader = DataLoader()

    def publish(self):
        """
        Main publish logic.
        """
        timestamp = self.market_hours.get_current_time_ist()

        # 1. Check Market Hours
        if not self.market_hours.is_market_open():
            self._write_skipped("Market Closed", timestamp)
            return

        # 2. Load Champion
        champ_data = self.champion_store.load_current_champion()
        if not champ_data:
            self._write_skipped("No Champion Found", timestamp)
            return

        # 3. Check Eligibility
        # We check the metrics stored in the champion file
        if not is_live_eligible(champ_data["metrics"]):
            self._write_skipped("Champion Not Eligible (Low Metrics)", timestamp)
            return

        # 4. Generate Signal
        # We need to reconstruct the strategy and run on latest data.
        # Ideally, we run on NIFTY or SENSEX depending on what the strategy was trained on?
        # The prompt says "Generate N candidates ... Output per candidate per instrument".
        # Usually we pick the best instrument too?
        # Or we run on NIFTY by default?
        # "Output leaderboards: top 20 for NIFTY and SENSEX".
        # The Champion JSON should probably say which instrument it excelled on?
        # The prompt schema has "instrument": "NIFTY|SENSEX".
        # Let's assume the champion is tied to an instrument or we evaluate on NIFTY.
        # For MVP, let's pick NIFTY.

        instrument = "NIFTY"
        df = self.loader.get_nifty()

        # Reconstruct strategy
        strat_def = champ_data["strategy"]
        strategy = self._reconstruct_strategy(strat_def)

        # Generate position
        # We need the LAST COMPLETED BAR's signal.
        # Since we are Daily, and running during the day, we need the signal generated at Yesterday's Close.
        # `generate_positions` returns a series.
        # `apply_risk_overlay` returns "End of Day Position".
        # If `final_pos[-1]` is the position for TODAY (based on yesterday close),
        # Wait. `final_pos` indices match DF.
        # `final_pos[i]` is position held at Close[i].
        # We trade at Open[i+1].
        # So for TODAY (Open[i+1]), we look at `final_pos[i]` (Yesterday).

        raw_signal = strategy.generate_positions(df)
        final_pos = strategy.apply_risk_overlay(df, raw_signal)

        # Get last valid position (Yesterday)
        # Verify DF dates.
        # If today is trading day, DF might contain Today's bar if Yahoo updated (live)?
        # Or only up to Yesterday.
        # We want the signal that dictates CURRENT exposure.
        # Exposure for Day T is determined by Data T-1.
        # So we look at the last row of `final_pos` if it corresponds to T-1.

        # Safety check on date
        last_date = df.index[-1]
        # If last_date is Today, we can't use it (session not closed).
        # We need Yesterday.
        # Yahoo Finance often provides live partial bar for current day.
        # We should exclude today's partial bar if present to be safe?
        # Or "Backtest engine: execution next-bar open".
        # If we have T-1 Close, we have Signal for T Open.

        # Identify T-1.
        # If last row is today, ignore it. Use T-1.
        # If last row is T-1, use it.

        # Assuming we can compare dates.
        today_date = pd.Timestamp.now(tz="Asia/Kolkata").date()

        if df.index[-1].date() == today_date:
            # Last row is today (partial).
            # Signal comes from T-1 (row -2).
            signal_idx = -2
        else:
            # Last row is yesterday (or earlier).
            signal_idx = -1

        target_pos = int(final_pos.iloc[signal_idx])

        # Construct JSON
        signal_data = {
            "timestamp_ist": timestamp,
            "champion_id": champ_data["id"],
            "instrument": instrument,
            "signal": target_pos,
            "rule_summary": strategy.describe(),
            "risk": champ_data["strategy"]["risk_params"],
            "status": "OK",
            "reason": "Signal Generated"
        }

        self._write_json(signal_data)

    def _write_skipped(self, reason: str, timestamp: str):
        data = {
            "timestamp_ist": timestamp,
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_json(data)

    def _write_json(self, data: Dict):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(LIVE_SIGNAL_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _reconstruct_strategy(self, data: Dict) -> Strategy:
        # Reconstruct from dict
        # We need to map strings to Classes

        entry_rules = []
        for r in data["entry_rules"]:
            name = r["name"]
            params = r["params"]
            if "EmaCross" in name:
                entry_rules.append(EmaCrossEntry(name, params))
            elif "Rsi" in name:
                entry_rules.append(RsiEntry(name, params))
            elif "Supertrend" in name:
                entry_rules.append(SupertrendEntry(name, params))

        filters = []
        for f in data["filters"]:
            name = f["name"]
            params = f["params"]
            if "Adx" in name:
                filters.append(AdxFilter(name, params))

        risk_params = data["risk_params"]

        return Strategy(entry_rules, filters, risk_params)
