"""Live Signal Publisher"""
import json
import structlog
from datetime import datetime
from pathlib import Path
from packages.strategy_foundry.adapters.core_market_hours import FoundryMarketHours
from packages.strategy_foundry.selection.ranker import ChampionStore
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import EntryType

logger = structlog.get_logger(__name__)

class SignalPublisher:
    def __init__(self):
        self.market = FoundryMarketHours()
        self.store = ChampionStore()
        self.loader = DataLoader()
        self.output_path = Path("packages/strategy_foundry/results/live_signal.json")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self):
        # 1. Check Market Hours
        if not self.market.is_market_open():
            self._write_skipped("Market Closed")
            return

        # 2. Load Champion
        champ = self.store.load_current()
        if not champ:
            self._write_skipped("No Champion")
            return

        # 3. Check Eligibility (Sanity)
        metrics = champ["metrics"]
        if metrics["sharpe"] < 1.2 or metrics["max_drawdown"] > 0.20:
            self._write_skipped(f"Champion ineligible: Sharpe={metrics['sharpe']:.2f} DD={metrics['max_drawdown']:.2f}")
            return

        # 4. Generate Signal
        symbol = "NIFTY"
        timeframe = champ["timeframe"]

        df = self.loader.get_data(symbol, timeframe, force_refresh=True)
        if df.empty or len(df) < 50:
            self._write_skipped("No Data")
            return

        from packages.strategy_foundry.factory.grammar import StrategyCandidate
        c_dict = champ["candidate"]
        candidate = StrategyCandidate(
            id=c_dict["id"],
            source_grammar=c_dict["source_grammar"],
            entry_block=c_dict["entry"],
            filter_blocks=c_dict["filters"],
            exit_blocks=c_dict["exits"]
        )

        engine = BacktestEngine(df)
        df_ind = engine._prepare_indicators(candidate)

        # Check Signal on last COMPLETED bar.
        # Yahoo live data includes the forming candle as the last row.
        # We look at [-2] for the last closed bar signal, to execute on [-1] (current open).
        # Or more accurately: Strategy checks signal at Close[-1], enters Open[0].
        # In live terms: We need signal from Close[FinishedBar].
        # If Yahoo's last row is [Forming], then [FinishedBar] is [-2].
        # If Yahoo's last row is [Finished] (e.g. at 09:20 we get 09:15 bar), then it is [-1].
        # But Yahoo usually provides "realtime" forming bar.

        # Safe approach: Check signal on [-2] and [-3] to detect crossover completed at [-2].
        last_completed_idx = -2
        prev_idx = -3

        last_row = df_ind.iloc[last_completed_idx]
        prev_row = df_ind.iloc[prev_idx]

        # Evaluate Entry Logic
        entry = False
        e = candidate.entry_block
        p = e["params"]

        if e["type"] == EntryType.EMA_CROSS:
            fast = last_row[f"ema_{p['fast']}"]
            slow = last_row[f"ema_{p['slow']}"]
            p_fast = prev_row[f"ema_{p['fast']}"]
            p_slow = prev_row[f"ema_{p['slow']}"]
            # Cross UP
            entry = (fast > slow) and (p_fast <= p_slow)

        elif e["type"] == EntryType.RSI_OVERSOLD:
            entry = last_row["rsi"] < p["threshold"]

        elif e["type"] == EntryType.DONCHIAN_BREAKOUT:
            entry = last_row["close"] > last_row["donchian_high"]

        # Apply Filters (on last completed bar)
        for f in candidate.filter_blocks:
            # Simplified regime check (e.g. SMA)
            if "regime_sma" in last_row:
                if last_row["close"] <= last_row["regime_sma"]:
                    entry = False

        signal_val = 1 if entry else 0

        out = {
            "timestamp_ist": datetime.now().isoformat(),
            "champion_id": candidate.id,
            "timeframe": timeframe,
            "instrument": symbol,
            "signal": signal_val,
            "status": "OK",
            "rule_summary": str(c_dict),
            "data_timestamp": str(last_row.name)
        }

        with open(self.output_path, "w") as f:
            json.dump(out, f, indent=2)

    def _write_skipped(self, reason):
        out = {
            "timestamp_ist": datetime.now().isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        with open(self.output_path, "w") as f:
            json.dump(out, f, indent=2)
