import os
import json
import structlog
from datetime import datetime
import pytz
from typing import Dict, Any

from ..adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)

SIGNAL_FILE = os.path.join(os.path.dirname(__file__), "../results/live_signal.json")
IST = pytz.timezone("Asia/Kolkata")

class SignalPublisher:
    def __init__(self):
        self.market = MarketHoursAdapter()

    def publish(self, champion_data: Dict[str, Any], signal: int, instrument: str):
        """
        Publish signal JSON.
        """
        now = datetime.now(IST)

        # Market Check
        is_open = self.market.is_market_open(now)

        payload = {
            "timestamp_ist": now.isoformat(),
            "champion_id": champion_data["candidate"]["id"] if champion_data else "NONE",
            "instrument": instrument,
            "signal": signal,
            "rule_summary": champion_data["candidate"]["rule_summary"] if champion_data else "",
            "risk": champion_data["candidate"]["params"] if champion_data else {},
            "status": "OK" if is_open else "SKIPPED",
            "reason": "Market Closed" if not is_open else ""
        }

        # Ensure dir
        os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

        with open(SIGNAL_FILE, "w") as f:
            json.dump(payload, f, indent=2)

        logger.info("Published signal", status=payload["status"], signal=signal)
