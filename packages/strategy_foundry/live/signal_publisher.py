"""Signal Publisher"""
import json
import os
from datetime import datetime
import structlog
from pathlib import Path
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursGuard

logger = structlog.get_logger(__name__)

class SignalPublisher:
    def __init__(self, output_dir: str = "packages/strategy_foundry/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mh = MarketHoursGuard()

    def publish(self, champion_data: dict, current_signal: int, instrument: str, reason: str = ""):
        """
        Publish signal JSON.
        """
        # Load instrument map
        with open("packages/strategy_foundry/configs/instrument_map.yaml") as f:
            imap = import_yaml(f) # Need yaml import

        # Determine Status
        status = "OK"
        if current_signal == 0:
            status = "NEUTRAL"

        # Check market hours
        if not self.mh.is_market_open():
             status = "SKIPPED"
             reason = "Market Closed"

        # Create Payload
        payload = {
            "timestamp_ist": datetime.now().astimezone().isoformat(),
            "champion_id": champion_data.get("id"),
            "timeframe": champion_data.get("timeframe"),
            "instrument": instrument,
            "proxy_symbol_paper": imap["paper_proxy"].get(instrument),
            "proxy_symbol_live": imap["live_proxy"].get(instrument),
            "signal": current_signal,
            "rule_summary": champion_data.get("rule_summary"),
            "status": status,
            "reason": reason
        }

        # Save
        with open(self.output_dir / "live_signal.json", "w") as f:
            json.dump(payload, f, indent=2)

        logger.info("Published signal", status=status, signal=current_signal)

def import_yaml(f):
    import yaml
    return yaml.safe_load(f)
