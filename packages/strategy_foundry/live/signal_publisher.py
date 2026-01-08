import json
import datetime
import pytz
from pathlib import Path
from typing import Dict, Any, Optional
from ..adapters.core_market_hours import MarketHoursAdapter
import structlog

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class SignalPublisher:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.market = MarketHoursAdapter()

    def publish(self, champion: Optional[Dict[str, Any]], signal: int, instrument: str = "NIFTY"):
        timestamp = datetime.datetime.now(IST).isoformat()

        # Default payload
        payload = {
            "timestamp_ist": timestamp,
            "champion_id": champion['id'] if champion else None,
            "instrument": instrument,
            "signal": 0,
            "rule_summary": champion['rule_summary'] if champion else None,
            "risk": {},
            "status": "SKIPPED",
            "reason": "Unknown"
        }

        # 1. Check Market Hours
        if not self.market.is_market_open():
            payload['reason'] = "Market Closed"
            self._write(payload)
            return

        # 2. Check Champion Existence
        if not champion:
            payload['reason'] = "No Champion"
            self._write(payload)
            return

        # 3. Check Live Eligibility
        if not self._is_eligible(champion):
            payload['reason'] = "Champion not eligible for live"
            self._write(payload)
            return

        # 4. Publish Signal
        payload['signal'] = signal
        payload['status'] = "OK"
        payload['risk'] = {"stop": "ATR", "params": {"mult": 2.0}} # Hardcoded/Extracted from params
        payload['reason'] = "Signal Generated"

        self._write(payload)
        logger.info(f"Published signal: {signal} for {instrument}")

    def _is_eligible(self, champion: Dict[str, Any]) -> bool:
        metrics = champion.get('metrics', {})

        if metrics.get('sharpe', 0) < 1.0:
            return False
        if metrics.get('max_dd', 1.0) > 0.25:
            return False
        if metrics.get('positive_folds', 0) < 3:
            return False

        return True

    def _write(self, payload: Dict[str, Any]):
        file_path = self.output_dir / "live_signal.json"
        with open(file_path, 'w') as f:
            json.dump(payload, f, indent=2)
