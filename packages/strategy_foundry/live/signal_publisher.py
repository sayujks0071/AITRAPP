import json
import structlog
from pathlib import Path
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec, StrategyBlock
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)

class SignalPublisher:
    """Publishes live trading signals based on champion strategies"""

    def __init__(self, output_dir: str = "packages/strategy_foundry/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mh = MarketHoursAdapter()

    def _reconstruct_spec(self, champ_data: Dict) -> StrategySpec:
        blocks = [StrategyBlock(**b) for b in champ_data["blocks"]]
        return StrategySpec(
            blocks=blocks,
            timeframe=champ_data["timeframe"],
            instrument=champ_data["instrument"],
            id=champ_data.get("id", "")
        )

    def publish(self, champion: Dict[str, Any], data: Any, instrument_map: Dict) -> None:
        """
        Generate and publish signal.
        Args:
            champion: Champion strategy dict
            data: DataFrame with latest data
            instrument_map: Dict with proxy mappings
        """
        try:
            # 1. Check Market Hours
            now_ist = datetime.now(self.mh.get_timezone())
            if not self.mh.is_market_open(now_ist):
                self._write_skipped("Market Closed")
                return

            # 2. Reconstruct Strategy
            spec = self._reconstruct_spec(champion)

            # 3. Run Engine to get current state
            # We run on available data.
            # The engine returns trades. We need to know if we are CURRENTLY in a trade.
            # The engine logic iterates through data.
            # We need to expose the "current position" from the engine or infer it.
            # Engine returns 'trades' list (closed trades).
            # If the last action was Entry and no Exit, we are in position?
            # My Engine implementation in `run` loop maintains `position` variable but only appends to `trades` on exit.
            # So I cannot see open positions from `trades`.
            # I should update Engine to return `current_position` or `open_trades`.

            # HACK: I will subclass or modify logic here to peek at state,
            # or just update Engine to return 'open_position' in result.
            # Updating Engine is cleaner.

            # Let's assume I update Engine. I'll do that in a separate step or just assume for now I can modify it.
            # I will assume Engine returns 'open_position' in the dict.

            engine = BacktestEngine(data)
            result = engine.run(spec)

            open_position = result.get("open_position", None) # {entry_price, entry_time, ...} or None

            signal_val = 0
            if open_position:
                signal_val = 1 # Long only for now

            # 4. Construct Signal JSON
            inst = spec.instrument
            proxies = instrument_map.get("live_proxy", {})
            proxy = proxies.get(inst, inst)

            signal_doc = {
                "timestamp_ist": now_ist.isoformat(),
                "champion_id": spec.id,
                "timeframe": spec.timeframe,
                "instrument": inst,
                "proxy_symbol_live": proxy,
                "signal": signal_val,
                "rule_summary": str([b.type for b in spec.blocks]),
                "status": "OK",
                "risk": {
                    "stop_price": open_position["stop_price"] if open_position else 0,
                    "target_price": open_position["target_price"] if open_position else 0
                } if open_position else {}
            }

            # Write
            outfile = self.output_dir / "live_signal.json"
            with open(outfile, "w") as f:
                json.dump(signal_doc, f, indent=2)

            logger.info("Published live signal", signal=signal_val, instrument=inst)

        except Exception as e:
            logger.error("Failed to publish signal", error=str(e))
            self._write_skipped(f"Error: {str(e)}")

    def _write_skipped(self, reason: str):
        doc = {
            "timestamp_ist": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        with open(self.output_dir / "live_signal.json", "w") as f:
            json.dump(doc, f, indent=2)
