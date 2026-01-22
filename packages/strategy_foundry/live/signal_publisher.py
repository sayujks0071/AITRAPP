# Strategy Foundry
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

        # Iterate instruments to find best signal
        instruments = ["NIFTY", "SENSEX"]
        best_signal_data = None
        best_score = -1

        for instrument in instruments:
            # 2. Load Champion
            champion = self.store.load_current_champion(instrument)
            if not champion:
                continue

            spec = champion["spec"]
            score = champion.get("score", 0)

            # Target Timeframe: 1D
            target_tf = "1d"

            # 3. Fetch Data (Force Refresh for Live)
            df = self.loader.fetch_data(instrument, target_tf, force_refresh=True)
            if df.empty:
                continue

            # 4. Run Engine to get State
            res = self.engine.run(df, spec)
            final_pos = res["final_position"]

            # 5. Construct Signal
            signal_val = 1 if final_pos > 0 else 0 # Long Only default

            proxies = self._get_proxies(instrument)

            signal_data = {
                "timestamp_ist": now.isoformat(),
                "champion_id": spec.get("id"),
                "timeframe": target_tf,
                "instrument": instrument,
                "proxy_symbol_paper": proxies.get("paper"),
                "proxy_symbol_live": proxies.get("live"),
                "signal": signal_val,
                "rule_summary": f"{spec['strategy_type']} + {spec['filter_type']}",
                "risk": {
                    "stop_atr_mult": spec["exit_params"].get("sl_mult"),
                    "flat_by": spec.get("session_close_time")
                },
                "status": "OK",
                "reason": "Signal Generated"
            }

            # Priority Logic:
            # 1. Prefer Active Signal (1) over Flat (0)
            # 2. If both Active, prefer Higher Score
            # 3. If both Flat, prefer Higher Score (though irrelevant)

            if best_signal_data is None:
                best_signal_data = signal_data
                best_score = score
            else:
                current_active = signal_val != 0
                best_active = best_signal_data["signal"] != 0

                if current_active and not best_active:
                    best_signal_data = signal_data
                    best_score = score
                elif current_active == best_active:
                    if score > best_score:
                        best_signal_data = signal_data
                        best_score = score

        if best_signal_data:
            self._write_json(best_signal_data)
        else:
            self._write_skipped(now, "NO_CHAMPION_OR_DATA")

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
