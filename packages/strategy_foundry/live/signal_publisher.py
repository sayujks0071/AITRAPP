"""Publish live signals"""
import json
import os
import pytz
from datetime import datetime
from typing import Dict, Optional
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursGuard # Use core via adapter? No, directly.
from packages.core.market_hours import MarketHoursGuard
import yaml

class SignalPublisher:
    def __init__(self, results_dir: str = "packages/strategy_foundry/results"):
        self.results_dir = results_dir
        self.live_signal_path = os.path.join(results_dir, "live_signal.json")
        self.market_guard = MarketHoursGuard()
        self.ist = pytz.timezone("Asia/Kolkata")

        # Load instrument map
        self.instrument_map = {}
        try:
            with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
                self.instrument_map = yaml.safe_load(f)
        except Exception:
            pass

    def publish(self, champion_data: Dict, current_signal: int, reason: str = ""):
        """
        Publish signal JSON.
        """
        now = datetime.now(self.ist)

        # Check market hours
        is_open = self.market_guard.is_market_open(now)

        # Determine status
        status = "OK"
        if not is_open:
            status = "SKIPPED"
            reason = "Market Closed"
        elif current_signal == 0 and not reason:
            # Flat is a valid signal, but maybe we want to be explicit
            pass

        # Get proxies
        cand = champion_data["candidate"]
        # candidate doesn't store instrument, logic does.
        # Assuming we ran champion on NIFTY/SENSEX?
        # Ideally champion stores which instrument it was trained on or we support multiple.
        # For simplicity, let's assume NIFTY default or passed in args.
        # But `champion_data` from store is generic.
        # We need to know which instrument to signal for.

        # Let's assume we are running for NIFTY primary.
        instrument = "NIFTY"

        payload = {
            "timestamp_ist": now.isoformat(),
            "champion_id": cand.get("id"),
            "timeframe": cand.get("timeframe"),
            "instrument": instrument,
            "proxy_symbol_paper": self.instrument_map.get("paper_proxy", {}).get(instrument),
            "proxy_symbol_live": self.instrument_map.get("live_proxy", {}).get(instrument),
            "signal": current_signal,
            "rule_summary": StrategyCandidate.from_dict(cand).describe(),
            "risk": {
                "flat_by": "15:25",
                # Extract ATR stop if present
            },
            "status": status,
            "reason": reason
        }

        with open(self.live_signal_path, "w") as f:
            json.dump(payload, f, indent=2)

    def publish_skipped(self, reason: str):
        now = datetime.now(self.ist)
        payload = {
            "timestamp_ist": now.isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        with open(self.live_signal_path, "w") as f:
            json.dump(payload, f, indent=2)

