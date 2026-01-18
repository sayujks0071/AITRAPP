import json
import os
import yaml
from datetime import datetime
import pytz
from packages.strategy_foundry.adapters.core_market_hours import MarketSchedule
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec

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

        # 2. Load Champion
        champion = self.store.load_current_champion()
        if not champion:
            self._write_skipped(now, "NO_CHAMPION")
            return

        spec = champion["spec"]
        # Determine timeframe and instrument to run
        # Ideally champion spec should store which timeframe it won on or we run the blended logic.
        # But for simplicity, let's assume we run the Primary Timeframe (5m) if available, else 15m.
        # The champion metrics might have score_5m and score_15m.
        # Let's pick 5m if valid, else 15m.

        # NOTE: The current generator/ranker structure produces a champion which is a SPEC.
        # The spec doesn't hardcode timeframe. The metrics do.
        metrics = champion.get("metrics", {})

        # Decide timeframe
        # If score_5m exists and is good, use 5m.
        # Actually, let's look at the metrics keys. "metrics" in champion store is probably a dict of { "5m": {...}, "15m": {...} }?
        # My Ranker/ChampionStore logic was:
        # ChampionStore.save_new_champion(candidate_spec, metrics, score, ...)
        # So 'metrics' is the full dict.

        target_tf = "5m"
        # Fallback logic could be better, but assuming 5m is primary as per requirements.

        # Instrument: "NIFTY" (Default for now, lab focuses on Index)
        instrument = "NIFTY"

        # 3. Fetch Data (Force Refresh for Live)
        df = self.loader.fetch_data(instrument, target_tf, force_refresh=True)
        if df.empty:
            self._write_skipped(now, "DATA_FETCH_FAILED")
            return

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
