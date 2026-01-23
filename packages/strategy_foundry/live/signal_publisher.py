# StrategyFoundry Implementation
# Strategy Foundry
import json
import yaml
import pandas as pd
from datetime import datetime
from pathlib import Path
import structlog
from typing import Dict, Any

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)

class SignalPublisher:
    """
    Publishes live signals based on champions.
    """

    def __init__(self):
        self.data_loader = DataLoader()
        self.champion_store = ChampionStore()
        self.market_guard = MarketHoursAdapter()
        self.output_path = Path("packages/strategy_foundry/results/live_signal.json")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load instrument map
        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            self.instrument_map = yaml.safe_load(f)

    def run(self):
        """
        Main execution method.
        """
        # 1. Check Market Hours
        # We publish skipped status if closed, but we might want to publish "Flat" signal if closing?
        # Requirement: "If market open AND champion live-eligible: write JSON"
        # "Else write SKIPPED JSON"

        if not self.market_guard.is_market_open():
             self._write_skipped("Market Closed")
             return

        # 2. Iterate Instruments
        # We need to pick the best champion across instruments or publish per instrument?
        # "Signal JSON schema" implies a SINGLE signal or maybe one file with one signal.
        # "champion_id": "..." suggests one active strategy.
        # Let's assume we pick the highest scoring eligible champion across NIFTY/SENSEX.

        best_signal = None
        best_score = -999.0

        for name, research_symbol in self.instrument_map.get("research", {}).items():
            champ_data = self.champion_store.load_champion(name)
            if not champ_data:
                continue

            metrics = champ_data.get("metrics", {})
            eligible, reason = Promoter.is_live_eligible(metrics)

            if not eligible:
                logger.info(f"Champion for {name} not eligible: {reason}")
                continue

            # Get latest data
            # Use 5m or 15m depending on what the champion uses?
            # Champion metrics usually have "metrics_15m" and "metrics_5m".
            # But the strategy itself is timeframe agnostic in grammar, but trained on both.
            # We should probably use the blended score to decide, but execution needs a specific timeframe.
            # Let's default to 15m for robustness unless 5m score is significantly better?
            # Or just use 15m.
            timeframe = "15m"

            df = self.data_loader.get_data(research_symbol, timeframe, force_refresh=True)
            if df is None or df.empty:
                continue

            # Check data freshness
            last_ts = df.index[-1]
            now = pd.Timestamp.now(tz="Asia/Kolkata")
            if (now - last_ts).total_seconds() > 30 * 60: # 30 mins stale
                logger.warning(f"Data for {name} is stale. Last: {last_ts}")
                continue

            # Generate Signal
            strategy = Strategy.from_dict(champ_data["strategy"])
            entries, exits = strategy.calculate_signals(df)

            # Look at LAST CLOSED bar signal
            # i.e. entries.iloc[-1]
            last_entry = entries.iloc[-1]
            last_exit = exits.iloc[-1]

            # Determine signal
            # If entry != 0 -> Signal
            # If exit == True -> Signal 0 (Flat)
            # This is simplistic. Real state requires knowing current position.
            # But "Signal First": we publish what the strategy says for *this bar*.

            signal_val = 0
            if last_exit:
                signal_val = 0
            elif last_entry != 0:
                signal_val = int(last_entry)
            else:
                # Hold / No Change
                # We should probably indicate "No Action" or maintain previous?
                # For this artifact, let's output the Direction (1, -1, 0).
                # If 0, it means "Don't Enter".
                signal_val = 0

            # Use blended score for selection
            score = metrics.get("score", 0)

            if score > best_score:
                best_score = score
                best_signal = {
                    "timestamp_ist": now.isoformat(),
                    "champion_id": champ_data["strategy"]["id"],
                    "timeframe": timeframe,
                    "instrument": name,
                    "proxy_symbol_paper": self.instrument_map["paper_proxy"].get(name),
                    "proxy_symbol_live": self.instrument_map["live_proxy"].get(name),
                    "signal": signal_val,
                    "rule_summary": json.dumps(champ_data["strategy"]["entry_blocks"]), # Simplified summary
                    "risk": strategy.get_risk_params(),
                    "status": "OK",
                    "reason": "Live Eligible"
                }

        if best_signal:
            self._write_json(best_signal)
        else:
            self._write_skipped("No eligible champion or data issues")

    def _write_skipped(self, reason: str):
        data = {
            "timestamp_ist": datetime.now().isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_json(data)

    def _write_json(self, data: Dict):
        with open(self.output_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Published signal: {data['status']}")
