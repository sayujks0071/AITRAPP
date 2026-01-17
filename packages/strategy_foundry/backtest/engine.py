from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, time
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate, Operator, IndicatorDef
from packages.strategy_foundry.adapters.core_indicators import VectorIndicatorCalculator
from packages.strategy_foundry.adapters.core_market_hours import FoundryMarketHours

logger = structlog.get_logger(__name__)

class BacktestEngine:
    """
    Vectorized backtest engine for Strategy Foundry candidates.
    """
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0):
        self.data = data
        self.initial_capital = initial_capital
        self.calculator = VectorIndicatorCalculator()
        self.market_hours = FoundryMarketHours()

    def run(self, candidate: StrategyCandidate) -> Dict[str, Any]:
        """
        Run backtest for a single candidate.
        """
        try:
            signals = self._generate_signals(candidate)
            trades = self._simulate_execution(signals, candidate.rule.risk_params)
            metrics = self._calculate_metrics(trades)
            return {
                "trades": trades,
                "metrics": metrics,
                "equity_curve": [] # TODO: generate equity curve
            }
        except Exception as e:
            logger.error(f"Backtest failed for {candidate.id}", error=str(e))
            return {}

    def _generate_signals(self, candidate: StrategyCandidate) -> pd.Series:
        """
        Evaluate entry conditions to generate raw entry signals.
        """
        df = self.data
        conditions = candidate.rule.entry_conditions

        # Start with all True
        entries = pd.Series(True, index=df.index)

        for cond in conditions:
            val_a = self._resolve_indicator(cond.indicator_a)
            val_b = self._resolve_indicator(cond.indicator_b)

            if cond.operator == Operator.GT:
                entries &= (val_a > val_b)
            elif cond.operator == Operator.LT:
                entries &= (val_a < val_b)
            elif cond.operator == Operator.CROSS_UP:
                # Vectorized cross up: (prev_a < prev_b) & (curr_a > curr_b)
                prev_a = pd.Series(val_a).shift(1)
                prev_b = pd.Series(val_b).shift(1) if isinstance(val_b, (pd.Series, np.ndarray)) else val_b
                entries &= (prev_a < prev_b) & (val_a > val_b)
            # ... handle other operators

        return entries

    def _resolve_indicator(self, indicator: Any) -> Any:
        if not isinstance(indicator, IndicatorDef):
            return indicator # Scalar

        name = indicator.name
        params = indicator.params

        if name == "close": return self.data["close"]
        if name == "open": return self.data["open"]
        if name == "high": return self.data["high"]
        if name == "low": return self.data["low"]

        # Call calculator methods
        # Map name to method
        if name == "ema":
            return self.calculator.ema_series(self.data["close"], params.get("period", 14))
        if name == "rsi":
            # Hack: Calculator usually takes fixed params in init, but we need dynamic.
            # We updated VectorIndicatorCalculator to allow this or we create new instance?
            # Creating new instance is slow.
            # Better: use the public methods we exposed/verified in adapter
            calc = VectorIndicatorCalculator(rsi_period=params.get("period", 14))
            return calc.rsi_series(self.data)
        if name == "adx":
            calc = VectorIndicatorCalculator(adx_period=params.get("period", 14))
            return calc.adx_series(self.data)
        if name == "donchian_upper":
            calc = VectorIndicatorCalculator()
            u, l = calc.donchian_series(self.data, params.get("period", 20))
            return u

        return pd.Series(0, index=self.data.index) # Fallback

    def _simulate_execution(self, entry_signals: pd.Series, risk_params: Dict) -> pd.DataFrame:
        """
        Event-driven simulation over vectorized signals to handle path-dependent logic (stops, profit targets).
        """
        trades = []
        position = 0
        entry_price = 0.0
        entry_time = None

        df = self.data
        atr = self.calculator.atr_series(df, tr=self.calculator.tr_series(df))

        sl_mult = risk_params.get("sl_atr", 2.0)
        tp_mult = risk_params.get("tp_atr", 4.0)

        # Iterate
        # Note: This is slow in Python. For "Aggressive" Foundry, we might want Numba or vectorization
        # but the prompt asked for "realistic" execution (no lookahead, session boundaries).
        # A simple loop is safest for correctness first.

        times = df.index
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        signals = entry_signals.values
        atrs = atr # numpy array

        market_open = time(9, 15)
        market_flat = time(15, 25)

        for i in range(1, len(df)):
            current_time = times[i]
            t = current_time.time()

            # 1. Check Exits if in position
            if position != 0:
                # Check stops/targets
                # Simple assumption: check against High/Low of current bar
                # BUT: we execute at OPEN or during bar?
                # "Signal calculated on bar close; execute next bar open" -> Standard
                # Intra-bar stops: hit if Low < SL (for long)

                # EOD Exit
                if t >= market_flat:
                    # Close at Open of this bar (if we decide EOD happens then) or Close?
                    # Usually "Flat by 15:25" means we exit AT 15:25 candle.
                    exit_px = opens[i]
                    pnl = (exit_px - entry_price) * position
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_px,
                        "pnl": pnl,
                        "reason": "EOD"
                    })
                    position = 0
                    continue

                # Stop Loss
                sl_price = entry_price - (sl_mult * entry_atr) # Long only for now
                tp_price = entry_price + (tp_mult * entry_atr)

                # Check Low for SL
                if lows[i] <= sl_price:
                    exit_px = sl_price # Slippage?
                    pnl = (exit_px - entry_price) * position
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_px,
                        "pnl": pnl,
                        "reason": "SL"
                    })
                    position = 0
                    continue

                # Check High for TP
                if highs[i] >= tp_price:
                    exit_px = tp_price
                    pnl = (exit_px - entry_price) * position
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_px,
                        "pnl": pnl,
                        "reason": "TP"
                    })
                    position = 0
                    continue

            # 2. Check Entries if flat
            # Signal from PREVIOUS bar close (i-1) triggers entry at CURRENT bar Open (i)
            # Ensure within market hours
            if position == 0:
                if t >= market_open and t < market_flat:
                    if signals[i-1]:
                        position = 1 # Fixed size 1 for simplicity in this loop
                        entry_price = opens[i]
                        entry_time = current_time
                        entry_atr = atrs[i-1] if not np.isnan(atrs[i-1]) else (entry_price * 0.01)

        return pd.DataFrame(trades)

    def _calculate_metrics(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        if trades_df.empty:
            return {
                "total_return": 0.0,
                "sharpe": 0.0,
                "trades": 0,
                "win_rate": 0.0
            }

        total_pnl = trades_df["pnl"].sum()
        win_rate = len(trades_df[trades_df["pnl"] > 0]) / len(trades_df)

        return {
            "total_return": total_pnl, # Absolute, need percentage
            "sharpe": 0.0, # Placeholder
            "trades": len(trades_df),
            "win_rate": win_rate
        }
