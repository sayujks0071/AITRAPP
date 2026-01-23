import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import structlog
import yaml
import pytz

from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class SignalPublisher:
    def __init__(self):
        self.store = ChampionStore()
        self.loader = DataLoader()

        # Load configs
        with open("packages/strategy_foundry/configs/foundry.yaml", "r") as f:
            self.config = yaml.safe_load(f)

        self.engine = BacktestEngine(
            initial_capital=self.config["backtest"]["initial_capital"],
            cost_bps=self.config["backtest"]["cost_bps"],
            slippage_bps=self.config["backtest"]["slippage_bps"]
        )
        self.market_hours = MarketHoursAdapter()
        self.output_file = Path("packages/strategy_foundry/results/live_signal.json")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # Load instrument map
        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            self.instrument_map = yaml.safe_load(f)

    def run(self):
        """
        Main execution method.
        """
        # 1. Check Market Hours
        if not self.market_hours.is_market_open():
             self._write_skipped("Market Closed")
             return

        # 2. Iterate Instruments
        best_champion = None
        best_signal_data = None
        best_score = -999.0

        instruments = ["NIFTY", "SENSEX"]

        for instrument in instruments:
            champion_data = self.store.load_champion(instrument)
            if not champion_data:
                continue

            score = champion_data.get("score", 0.0)

            # Get Candidate
            candidate_dict = champion_data["candidate"]
            candidate = StrategyCandidate(**candidate_dict)

            # Fetch Data
            symbol = self.instrument_map["research"][instrument]
            timeframe = "5m" # Defaulting to 5m for live execution granularity

            # Force fresh download to get latest bar
            data = self.loader.get_data(symbol, timeframe, days=60, use_cache=False)
            if data.empty:
                logger.error("No data for live signal", symbol=symbol)
                continue

            # Run Backtest (Replay)
            results = self.engine.run(candidate, data)

            open_pos = results.get("open_position")

            # Determine Signal
            signal_val = 0
            risk_info = {}
            status = "OK"

            if open_pos:
                signal_val = 1 # Long
                risk_info = {
                    "stop": open_pos["stop_loss"],
                    "tp": open_pos["take_profit"],
                    "flat_by": "15:25",
                    "entry_price": open_pos["entry_price"]
                }
            else:
                # Check for New Entry
                # We need to access the signal array which is internal to engine.run
                # But engine.run doesn't return signal array.
                # However, we can reconstruct it or expose it.
                # Or simpler: Check if open_pos is None.
                # If None, we are Flat.
                # Did we generate a signal on the LAST bar?
                # If so, we should ENTER at NEXT OPEN (which is now/soon).

                # To check this efficiently without modifying run return signature again:
                # Re-calculate signals locally.
                indicators = self.engine._calculate_indicators(data, candidate)
                signals = self.engine._generate_entry_signals(data, indicators, candidate)

                if signals[-1]: # Signal at Close[-1] -> Enter Open[+1]
                     signal_val = 1
                     risk_info = {
                         "stop": "ATR", # Dynamic
                         "params": candidate.exit.params,
                         "flat_by": "15:25"
                     }
                else:
                    signal_val = 0 # Flat

            # Store if best score (or just process all? Requirement: "publishes a live signal JSON... for the highest-scoring candidate" implied?)
            # Prompt says: "The SignalPublisher ... iterates through champions... and publishes a single live_signal.json for the highest-scoring candidate."

            if score > best_score:
                best_score = score
                best_champion = champion_data
                best_signal_data = {
                    "timestamp_ist": datetime.now(IST).isoformat(),
                    "champion_id": candidate.id,
                    "timeframe": timeframe,
                    "instrument": instrument,
                    "proxy_symbol_paper": self.instrument_map["paper_proxy"].get(instrument),
                    "proxy_symbol_live": self.instrument_map["live_proxy"].get(instrument),
                    "signal": signal_val,
                    "rule_summary": candidate.get_summary(),
                    "risk": risk_info,
                    "status": "OK",
                    "reason": "Market Open, Signal Generated"
                }

        if best_signal_data:
            self._write_json(best_signal_data)
        else:
            self._write_skipped("No champions or No Data")

    def _write_skipped(self, reason: str):
        data = {
            "status": "SKIPPED",
            "reason": reason,
            "timestamp_ist": datetime.now(IST).isoformat()
        }
        self._write_json(data)

    def _write_json(self, data: Dict):
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Published live signal", status=data.get("status"))

if __name__ == "__main__":
    SignalPublisher().run()
