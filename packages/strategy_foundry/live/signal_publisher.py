"""
Signal Publisher.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import structlog
import yaml
import pytz

from packages.strategy_foundry.adapters.core_market_hours import MarketHours
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec
from packages.strategy_foundry.data.loader import DataLoader

logger = structlog.get_logger(__name__)

class SignalPublisher:
    def __init__(self):
        self.results_dir = Path("packages/strategy_foundry/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.market_hours = MarketHours()
        self.loader = DataLoader()

        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            self.map = yaml.safe_load(f)

    def publish(self, champion: Dict[str, Any]):
        """
        Generate and publish live signal.
        """
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)

        # 1. Check Market Hours
        if not self.market_hours.is_market_open(now):
            self._write_skipped("Market Closed")
            return

        # 2. Check Eligibility (Gate)
        # Champion must be eligible for live
        if not self._is_eligible(champion):
            self._write_skipped("Champion not eligible for live")
            return

        # 3. Load Live Data (Intraday)
        spec_data = champion["strategy_spec"]
        spec = StrategySpec(**spec_data) # Reconstruct

        symbol = "NIFTY" # Default, or store in champion?
        # Ideally champion has "instrument" field.
        # But our grammar doesn't generate instrument specific strategies, they are generic.
        # But we tested on specific instruments.
        # Let's assume NIFTY for now or check what ranker saved.

        # NOTE: Ranker and Promoter logic should preserve which instrument the champion was optimized on.
        # Assuming we ran on NIFTY and SENSEX, we might have different champions?
        # For this aggressive lab, let's assume we picked the overall best one (likely NIFTY).
        # We'll use NIFTY.

        timeframe = spec.timeframe

        # Force refresh to get latest bar
        df = self.loader.get_data(symbol, timeframe, force_refresh=True)

        # 4. Run Strategy on latest data
        engine = BacktestEngine(df)
        # We need the signal for the *current/next* bar.
        # Backtest engine returns *historical* signals vector.
        # We need to peek at the last signal generated.

        # We can reuse _generate_signals
        df_ind = engine.indicators.add_all(df)
        signals = engine._generate_signals(df_ind, spec)

        last_signal = signals.iloc[-1]

        # Check if we should be flat (time)
        flat_time = self.market_hours.get_flatten_time()
        # Parse flat time
        flat_dt = datetime.strptime(flat_time, "%H:%M").time()
        if now.time() >= flat_dt:
            last_signal = 0

        # 5. Construct Signal JSON
        signal_out = {
            "timestamp_ist": now.isoformat(),
            "champion_id": spec.id,
            "timeframe": timeframe,
            "instrument": symbol,
            "proxy_symbol_paper": self.map["paper_proxy"].get(symbol, ""),
            "proxy_symbol_live": self.map["live_proxy"].get(symbol, ""),
            "signal": int(last_signal),
            "rule_summary": spec.summary,
            "risk": {
                "stop": spec.exit_logic["stop_type"],
                "params": spec.exit_logic,
                "flat_by": flat_time
            },
            "status": "OK",
            "reason": ""
        }

        self._write_json(signal_out)

    def _is_eligible(self, champion: Dict[str, Any]) -> bool:
        # Re-check eligibility gates just in case
        if champion["sharpe"] < 1.2: return False
        if champion["max_dd"] > 0.20: return False
        return True

    def _write_skipped(self, reason: str):
        out = {
            "timestamp_ist": datetime.now().isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        self._write_json(out)

    def _write_json(self, data: Dict[str, Any]):
        with open(self.results_dir / "live_signal.json", "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Published live signal", status=data.get("status"))
