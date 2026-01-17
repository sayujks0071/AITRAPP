import json
import os
from datetime import datetime
import structlog
from packages.strategy_foundry.adapters.core_market_hours import IST

logger = structlog.get_logger(__name__)

class SignalPublisher:
    def __init__(self, output_path: str = "packages/strategy_foundry/results/live_signal.json"):
        self.output_path = output_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def publish(self, signal_data: dict):
        """
        Publish signal artifact.
        """
        try:
            # Enforce timestamp
            signal_data["timestamp_ist"] = datetime.now(IST).isoformat()

            with open(self.output_path, "w") as f:
                json.dump(signal_data, f, indent=2)

            logger.info("Published live signal", path=self.output_path, signal=signal_data.get("signal"))

        except Exception as e:
            logger.error("Failed to publish signal", error=str(e))

    def publish_skipped(self, reason: str):
        self.publish({
            "status": "SKIPPED",
            "reason": reason,
            "signal": 0
        })
