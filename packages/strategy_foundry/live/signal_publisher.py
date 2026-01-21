import json
import os
from datetime import datetime

import pytz
import yaml

from packages.strategy_foundry.adapters.core_market_hours import MarketSchedule
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.selection.champion_store import ChampionStore


class SignalPublisher:
    def __init__(self):
        self.schedule = MarketSchedule()
        self.store = ChampionStore()
        self.loader = DataLoader()
        self.engine = BacktestEngine()
        self.output_path = "packages/strategy_foundry/results/live_signal.json"

        # Load Config for proxies
        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            self.map_config = yaml.safe_load(f)

    def publish(self):
        # 1. Check Market Hours
        now = datetime.now(pytz.timezone("Asia/Kolkata"))
        if not self.schedule.is_open_now():
             self._write_skipped(now, "MARKET_CLOSED")
             return

        # 2. Iterate Instruments
        instruments = ["NIFTY", "SENSEX"]
        candidates = []

        for instrument in instruments:
            champion = self.store.load_current_champion(instrument)
            if not champion:
                continue

            spec = champion["spec"]
            target_tf = "5m"

            # 3. Fetch Data (Force Refresh for Live)
            df = self.loader.fetch_data(instrument, target_tf, force_refresh=True)
            if df.empty:
                continue

            # 4. Run Engine to get State
            res = self.engine.run(df, spec)
            final_pos = res["final_position"]
            signal_val = 1 if final_pos > 0 else 0

            # Only consider if there is an active signal (1 or -1 if short allowed)
            # Actually, we should publish state even if Flat (0), but if we want to pick "The One",
            # we likely prioritize active signals.
            # But "status": "OK" with signal 0 is also valid "Flat" signal.

            candidates.append({
                "instrument": instrument,
                "champion": champion,
                "signal": signal_val,
                "score": champion.get("score", 0)
            })

        if not candidates:
            self._write_skipped(now, "NO_DATA_OR_CHAMPIONS")
            return

        # 5. Pick Best
        # Priority: Active Signal > Higher Score
        # Filter active signals
        active = [c for c in candidates if c["signal"] != 0]

        if active:
            # Pick highest score among active
            selected = max(active, key=lambda x: x["score"])
        else:
            # All flat, pick highest score champion to report flat state
            selected = max(candidates, key=lambda x: x["score"])

        # 6. Construct Signal
        spec = selected["champion"]["spec"]
        instrument = selected["instrument"]
        proxies = self._get_proxies(instrument)

        signal_data = {
            "timestamp_ist": now.isoformat(),
            "champion_id": spec.get("id"),
            "timeframe": "5m",
            "instrument": instrument,
            "proxy_symbol_paper": proxies.get("paper"),
            "proxy_symbol_live": proxies.get("live"),
            "signal": selected["signal"],
            "rule_summary": f"{spec['strategy_type']} + {spec['filter_type']}",
            "risk": {
                "stop_atr_mult": spec["exit_params"].get("sl_mult"),
                "flat_by": spec.get("session_close_time")
            },
            "status": "OK",
            "reason": "Signal Generated"
        }

        self._write_json(signal_data)

    def _get_proxies(self, instrument):
        return {
            "paper": self.map_config.get("paper_proxy", {}).get(instrument),
            "live": self.map_config.get("live_proxy", {}).get(instrument)
        }

    def _write_skipped(self, now, reason):
        data = {
            "timestamp_ist": now.isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_json(data)

    def _write_json(self, data):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    SignalPublisher().publish()
