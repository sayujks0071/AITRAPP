import json
import os
import structlog
from pathlib import Path
from datetime import datetime
import yaml
import pandas as pd
from typing import Dict
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.adapters.core_costs import get_default_costs

logger = structlog.get_logger(__name__)

RESULTS_DIR = Path(__file__).parent.parent / "results"
CONFIG_DIR = Path(__file__).parent.parent / "configs"

class SignalPublisher:
    def __init__(self):
        self.market_adapter = MarketHoursAdapter()
        with open(CONFIG_DIR / "foundry.yaml") as f:
            self.config = yaml.safe_load(f)
        with open(CONFIG_DIR / "instrument_map.yaml") as f:
            self.instrument_map = yaml.safe_load(f)
        self.loader = DataLoader()

    def run(self):
        # 1. Check Market Hours
        if not self.market_adapter.is_market_open():
            self._write_skipped("Market Closed")
            return

        # 2. Load Champion (Blended preference, or 15m)
        promoter = Promoter(self.config)
        # Try blended or specific?
        # For now, let's look for 15m champion as primary
        champ_data = promoter.load_champion("15m")
        if not champ_data:
            # Try 5m
            champ_data = promoter.load_champion("5m")

        if not champ_data:
            self._write_skipped("No Eligible Champion")
            return

        # 3. Generate Signal
        candidate = StrategyCandidate.from_json(champ_data["candidate"])
        timeframe = "15m" if "15m" in str(champ_data) else "5m" # Heuristic or store in JSON
        # Actually I didn't store timeframe in champion json explicitly, but filename has it.

        # Load Recent Data
        # We need enough data to warm up indicators
        symbol = "NIFTY" # Defaulting to NIFTY for now, should be configurable or iterated

        try:
            df = self.loader.fetch_data(symbol, timeframe, lookback_days=5) # 5 days enough for intraday?

            # Run engine for latest bar
            engine = BacktestEngine(df, get_default_costs())

            # We need to expose a way to get the LATEST signal without full backtest loop?
            # Engine has `_calculate_indicators` and `_generate_signals`.

            # Add indicators
            engine._calculate_indicators(df, candidate)
            signals = engine._generate_signals(df, candidate)

            # Last signal
            latest_signal = signals[-1]
            # Also check if we should be flat (EOD)
            # This is logic inside `_simulate_execution`.
            # We should replicate the "Should I be in a position?" logic.
            # Ideally, we run the simulation up to now to know state?
            # Or just "Entry Signal" vs "Exit Signal".
            # The foundry is generating entry signals.
            # Exits are managed by OCO/Execution engine usually.
            # But here we publish "Signal: 1" (Enter Long) or "Signal: 0" (Flat/Exit).

            # Simple approach: Publish the Entry Signal state.
            # If 1, it means "Enter Long condition met".
            # Receiver decides if already in pos.

            # Refined approach:
            # If we are close to EOD, force signal 0.
            now = datetime.now()
            if now.hour == 15 and now.minute >= 25:
                latest_signal = 0 # Force Flat

            # Proxies
            paper_proxy = self.instrument_map.get("paper_proxy", {}).get(symbol, "")
            live_proxy = self.instrument_map.get("live_proxy", {}).get(symbol, "")

            payload = {
                "timestamp_ist": datetime.now().isoformat(),
                "champion_id": candidate.id,
                "timeframe": timeframe,
                "instrument": symbol,
                "proxy_symbol_paper": paper_proxy,
                "proxy_symbol_live": live_proxy,
                "signal": int(latest_signal),
                "rule_summary": str(candidate.entry_logic),
                "risk": {
                    "stop": "ATR",
                    "params": candidate.params,
                    "flat_by": "15:25"
                },
                "status": "OK",
                "reason": "Signal Generated"
            }

            self._write_signal(payload)

        except Exception as e:
            logger.error("Signal Generation Failed", error=str(e))
            self._write_skipped(f"Error: {str(e)}")

    def _write_skipped(self, reason: str):
        payload = {
            "timestamp_ist": datetime.now().isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_signal(payload)

    def _write_signal(self, payload: Dict):
        path = RESULTS_DIR / "live_signal.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info("Published Live Signal", status=payload.get("status"))

if __name__ == "__main__":
    SignalPublisher().run()
