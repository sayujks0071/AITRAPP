"""
Live Signal Publisher
Publishes trade signals to JSON artifact.
"""
import json
from datetime import datetime
from pathlib import Path
from packages.strategy_foundry.adapters.core_market_hours import IST, MarketHoursGuard

OUTPUT_FILE = Path("packages/strategy_foundry/results/live_signal.json")

class SignalPublisher:
    @staticmethod
    def publish(signal_data: dict):
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp if missing
        if "timestamp_ist" not in signal_data:
            signal_data["timestamp_ist"] = datetime.now(IST).isoformat()

        with open(OUTPUT_FILE, 'w') as f:
            json.dump(signal_data, f, indent=2)

    @staticmethod
    def publish_skipped(reason: str):
        SignalPublisher.publish({
            "status": "SKIPPED",
            "reason": reason,
            "timestamp_ist": datetime.now(IST).isoformat()
        })
