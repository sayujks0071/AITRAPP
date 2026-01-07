"""
Live Signal Publisher
"""
import json
import structlog
from pathlib import Path
from datetime import datetime
from packages.strategy_foundry.adapters.core_market_hours import IST

logger = structlog.get_logger(__name__)

RESULTS_DIR = Path("packages/strategy_foundry/results")

class SignalPublisher:
    @staticmethod
    def publish(signal_data: dict):
        """
        Publish signal JSON.
        """
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = RESULTS_DIR / "live_signal.json"

        payload = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            **signal_data
        }

        with open(file_path, 'w') as f:
            json.dump(payload, f, indent=2)

        logger.info("Published live signal", signal=signal_data)

    @staticmethod
    def publish_skipped(reason: str):
        """
        Publish SKIPPED signal.
        """
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = RESULTS_DIR / "live_signal.json"

        payload = {
            "timestamp_ist": datetime.now(IST).isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }

        with open(file_path, 'w') as f:
            json.dump(payload, f, indent=2)

        logger.info("Published skipped signal", reason=reason)
