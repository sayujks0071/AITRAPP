"""
Live Signal Publisher.
"""
import json
import os
from datetime import datetime
from packages.strategy_foundry.configs.config import load_instrument_map
from packages.strategy_foundry.adapters.core_market_hours import FoundryMarketHours, IST

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

class SignalPublisher:
    def __init__(self):
        self.instrument_map = load_instrument_map()
        self.market_hours = FoundryMarketHours()

    def publish(self, champion: dict, signal: int, reason: str = ""):
        """
        Publish signal artifact.
        """
        os.makedirs(RESULTS_DIR, exist_ok=True)

        now = datetime.now(IST)
        is_open = self.market_hours.is_market_open(now)

        status = "OK"
        if not is_open:
            status = "SKIPPED"
            reason = "Market Closed"
        elif champion is None:
            status = "SKIPPED"
            reason = reason or "No Eligible Champion"

        output = {
            "timestamp_ist": now.isoformat(),
            "champion_id": champion.get("id") if champion else None,
            "timeframe": champion.get("timeframe") if champion else None,
            "instrument": "NIFTY", # TODO: Dynamic
            "proxy_symbol_paper": self.instrument_map.get("paper_proxy", {}).get("NIFTY"),
            "proxy_symbol_live": self.instrument_map.get("live_proxy", {}).get("NIFTY"),
            "signal": signal,
            "rule_summary": champion.get("rule_summary") if champion else "",
            "risk": champion.get("risk_config", {"stop": "ATR", "flat_by": "15:25"}) if champion else {},
            "status": status,
            "reason": reason
        }

        path = os.path.join(RESULTS_DIR, "live_signal.json")
        with open(path, "w") as f:
            json.dump(output, f, indent=2)

        return output
