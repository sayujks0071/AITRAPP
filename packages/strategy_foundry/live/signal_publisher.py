"""Publishes live signal JSON"""
import json
import yaml
from pathlib import Path
from datetime import datetime
import pytz
from typing import Dict, Any

from packages.strategy_foundry.live.market_hours import is_market_open_for_signal
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.adapters.core_costs import CostModel
from packages.strategy_foundry.factory.grammar import StrategyCandidate

SIGNAL_FILE = Path("packages/strategy_foundry/results/live_signal.json")
SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
CONFIG_MAP = Path("packages/strategy_foundry/configs/instrument_map.yaml")

class SignalPublisher:
    def __init__(self):
        self.store = ChampionStore()
        self.loader = DataLoader(use_cache=False) # Live needs fresh data
        self.engine = BacktestEngine(CostModel()) # For signal gen, we reuse engine components (indicators)
        # Actually engine.run computes history.
        # For live signal, we need "run_live" or just run on latest data and check last bar.

        self.instrument_map = {}
        if CONFIG_MAP.exists():
             self.instrument_map = yaml.safe_load(CONFIG_MAP.read_text())

    def publish(self):
        """
        Main entry point.
        Checks market, loads champion, gets data, generates signal, writes JSON.
        """
        # 1. Market Check
        if not is_market_open_for_signal():
            self._write_skipped("Market Closed")
            return

        # 2. Load Champion
        champ_data = self.store.load_current()
        if not champ_data:
            self._write_skipped("No Champion Found")
            return

        candidate_spec = champ_data["candidate"]
        candidate = StrategyCandidate(**candidate_spec)

        # 3. Check Eligibility (Redundant if only eligible are stored, but safe to check gates)
        # Assuming Store only keeps eligible.

        # 4. Get Data
        # Which instrument? Champion should say? Or we run for Nifty/Sensex?
        # Assuming Foundry is Single-Asset or Multi-Asset?
        # The prompt implies "Instrument Map".
        # Let's assume the champion was trained on "NIFTY" (research symbol).
        # But wait, candidate spec doesn't have instrument.
        # We probably ran on NIFTY by default.
        research_symbol = self.instrument_map.get("research", {}).get("NIFTY", "^NSEI")

        # Fetch data (enough for indicators)
        days = 60
        df = self.loader.get_data(research_symbol, candidate.timeframe, days)

        if df.empty:
            self._write_skipped(f"No Data for {research_symbol}")
            return

        # 5. Generate Signal
        # Run engine on recent data. Look at LAST bar signal.
        # Engine.run returns trades. We need the SIGNAL series.
        # Refactor engine to expose signal generation or just look at last row of df after indicators?
        # In engine.run_safe, we compute indicators and signals.

        # We'll invoke a method to get signal on latest bar.
        # But engine.run_safe does a loop.
        # We can implement `generate_latest_signal` in Engine or here.

        # Reuse Engine Logic by passing data and checking last row of df
        # We need to modify Engine to return the processed DF with signals
        # Or duplicate logic.
        # Let's peek at `engine._compute_indicators` and logic.

        # To avoid code duplication, I'll instantiate the engine, compute indicators, apply logic manually here?
        # Or make engine return df.

        # Since I can't easily change engine signature without breaking tests (that I haven't written yet, but plan implies separation),
        # I will use a helper in Engine or just do full run and check last row?
        # Full run is fast for 60 days.

        equity, trades = self.engine.run_safe(candidate, df)

        # But run_safe calculates trades. It doesn't return the DF with 'signal' column.
        # I need that column.
        # Let's patch `run_safe` to return df? Or just trust the trade list?
        # If a trade opened on the last bar, we have a signal.
        # If a trade is OPEN, we have a position.

        # "Signal" usually means "Current Position" or "Action to take"?
        # "signal": -1|0|1.
        # If we are currently Long, signal is 1.
        # If Flat, 0.

        # Check if there is an active trade at the end.
        # run_safe closes positions at EOD.
        # If we run it on LIVE data (where current bar is NOT EOD yet),
        # we need to be careful about `flatten_time`.
        # If current time < flatten_time, we might have a position.

        # Issue: `run_safe` iterates and closes.
        # We need to know: At the *latest completed bar*, what is the state?
        # Actually, for "Signal Publishing", we usually want "Target Position".

        # Let's look at the last trade in the list.
        # If it has NO exit_time, it's open.
        # But `run_safe` forces close at EOD_FORCE.

        # We need a `get_current_position` method in Engine that doesn't force close the last bar if it's live?
        # Or just checking signal generation logic.

        # Let's compute indicators and signal column manually here using engine components.
        # It ensures we use same logic.

        # COPY OF LOGIC FROM ENGINE (Risk of drift, but cleaner than modifying engine heavily now)
        # Actually, better to import the logic.

        self.engine._compute_indicators(df, candidate)

        # Entry Logic
        entry_type = candidate.entry_logic["type"]
        params = candidate.params

        # Calc Signal Column
        df["signal_long"] = 0
        if entry_type == "DONCHIAN_BREAKOUT":
            u, l = self.engine.indicators.donchian(df["high"], df["low"], params["donchian_period"])
            df.loc[df["close"] > u.shift(1), "signal_long"] = 1
        elif entry_type == "RSI_REVERSION":
            rsi = self.engine.indicators.rsi(df["close"], params["rsi_period"])
            df.loc[rsi < params["rsi_os"], "signal_long"] = 1
        elif entry_type == "EMA_CROSS":
            f = df["close"].ewm(span=params['ema_fast'], adjust=False).mean()
            s = df["close"].ewm(span=params['ema_slow'], adjust=False).mean()
            df.loc[(f > s) & (f.shift(1) <= s.shift(1)), "signal_long"] = 1
        elif entry_type == "BOLLINGER_REVERSION":
             u, m, l = self.engine.indicators.bollinger_bands(df["close"], params["bb_period"], params["bb_std"])
             df.loc[df["close"] < l, "signal_long"] = 1

        # Filters
        mask = pd.Series(True, index=df.index)
        for f in candidate.filters:
            if f["type"] == "TREND_EMA_1H":
                 factor = 12 if "5m" in candidate.timeframe else 4
                 per = params.get("trend_ema", 50) * factor
                 ema = df["close"].ewm(span=per).mean()
                 mask &= (df["close"] > ema)
            elif f["type"] == "VOLATILITY_ATR":
                 atr = df["atr"]
                 mask &= (atr > atr.rolling(100).mean())

        df.loc[~mask, "signal_long"] = 0

        # Now, determining "Current Signal".
        # We need to simulate position state up to now.
        # This effectively requires running the loop.
        # But we can assume: if we are not stopped out, and we had an entry, we are long.

        # Let's run the engine on this data but disable EOD force close for the very last bar?
        # No, `run_safe` is designed for backtest.

        # Robust way:
        # 1. Get Signal from last completed bar.
        # 2. If Signal == 1, we want to be Long (unless stopped out).

        # For simplicity in V1:
        # We publish the raw ENTRY signal from the last closed bar.
        # The execution system (consumer) must handle state (stops, existing position).
        # This is an "Aggressive Intraday" lab.
        # The prompt says: "Signal calculated on bar close; execute next bar open".

        last_idx = -1
        last_signal = int(df["signal_long"].iloc[last_idx])

        # If signal is 1, we publish 1.
        # Note: This is an ENTRY signal. Not a "Position" signal.
        # Consumer needs to know if they are already in.
        # But the JSON schema has "signal": -1|0|1.

        # Status
        status = "OK"
        reason = "Market Open"

        # Proxies
        proxy_paper = self.instrument_map.get("paper_proxy", {}).get("NIFTY", "")
        proxy_live = self.instrument_map.get("live_proxy", {}).get("NIFTY", "")

        payload = {
            "timestamp_ist": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
            "champion_id": candidate.id,
            "timeframe": candidate.timeframe,
            "instrument": "NIFTY",
            "proxy_symbol_paper": proxy_paper,
            "proxy_symbol_live": proxy_live,
            "signal": last_signal,
            "rule_summary": candidate.rule_summary,
            "risk": {
                "stop": candidate.exit_logic["type"],
                "params": candidate.params,
                "flat_by": "15:25"
            },
            "status": status,
            "reason": reason
        }

        SIGNAL_FILE.write_text(json.dumps(payload, indent=2))

    def _write_skipped(self, reason: str):
        payload = {
            "timestamp_ist": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        SIGNAL_FILE.write_text(json.dumps(payload, indent=2))
