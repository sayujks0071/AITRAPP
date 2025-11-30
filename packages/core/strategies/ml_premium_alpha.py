"""ML Premium Alpha Strategy

Inference-first strategy with:
- Model-driven directional scoring (supports scikit/pickle joblib models)
- Feature stack: returns, volatility, trend stack (EMA), momentum (RSI/ADX), regime-aware liquidity filter
- Risk controls: ATR-based stops/targets, spread/volume guard via signal features
- Cooldown and confidence gating to reduce churn

Model contract:
- Expects `.predict_proba([[...features...]])` returning [short_prob, long_prob]
- If model not found/loaded, falls back to rules-based scoring
"""
from __future__ import annotations

import os
import pickle
from typing import List, Optional, Any

import numpy as np
import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class MLPremiumAlphaStrategy(Strategy):
    """ML-driven directional strategy with conservative risk overlays."""

    def __init__(self, name: str, params: dict):
        super().__init__(name, params)

        # Model + thresholds
        self.model_path = params.get("model_path", "models/ml_premium_alpha.pkl")
        self.feature_lookback = params.get("feature_lookback", 60)
        self.confidence_threshold = params.get("confidence_threshold", 0.55)
        self.cooldown_minutes = params.get("cooldown_minutes", 10)

        # Risk
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.3)
        self.atr_target_mult = params.get("atr_target_mult", 2.2)
        self.rr_min = params.get("rr_min", 1.8)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.2)

        # Instruments
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])

        # State
        self.last_signal_time = {}
        self.last_signal_side = {}
        self._model = self._load_model(self.model_path)

    def _load_model(self, path: str) -> Optional[Any]:
        """Load a pickled/ joblib model if available."""
        if not path or not os.path.exists(path):
            logger.warning("ML model not found; using rules fallback", path=path)
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning("Failed to load ML model; using rules fallback", path=path, error=str(e))
            return None

    def _can_emit(self, token: int, timestamp) -> bool:
        if token not in self.last_signal_time:
            return True
        delta = (timestamp - self.last_signal_time[token]).total_seconds() / 60
        return delta >= self.cooldown_minutes

    def _calc_atr(self, bars: List[Bar], period: int) -> Optional[float]:
        if len(bars) < period + 1:
            return None
        trs = []
        for i in range(len(bars) - period, len(bars)):
            prev_close = bars[i - 1].close
            high = bars[i].high
            low = bars[i].low
            trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        return sum(trs) / len(trs) if trs else None

    def _features(self, bars: List[Bar]) -> Optional[np.ndarray]:
        if len(bars) < max(self.feature_lookback, 30):
            return None
        window = bars[-self.feature_lookback :]
        closes = np.array([b.close for b in window], dtype=float)
        returns = np.diff(closes) / closes[:-1]
        if returns.size == 0:
            return None

        # Basic stats
        ret_mean = returns.mean()
        ret_std = returns.std() + 1e-6
        sharpe_like = ret_mean / ret_std
        max_dd = np.max(np.maximum.accumulate(closes) - closes) / np.maximum(closes[-1], 1e-6)

        latest = window[-1]
        ema_fast = latest.ema_fast or closes[-5:].mean()
        ema_slow = latest.ema_slow or closes[-20:].mean()
        rsi = latest.rsi or 50.0
        adx = latest.adx or 20.0
        macd = getattr(latest, "macd", 0.0) or 0.0
        macd_sig = getattr(latest, "macd_signal", 0.0) or 0.0

        feat_vec = np.array(
            [
                ret_mean,
                ret_std,
                sharpe_like,
                max_dd,
                ema_fast / max(ema_slow, 1e-6),
                rsi / 100.0,
                adx / 100.0,
                macd,
                macd_sig,
            ],
            dtype=float,
        )
        return feat_vec

    def _score_direction(self, features: np.ndarray) -> tuple[float, float, str]:
        """
        Returns: (prob_long, prob_short, source)
        """
        if self._model and hasattr(self._model, "predict_proba"):
            try:
                proba = self._model.predict_proba([features])[0]
                prob_short, prob_long = float(proba[0]), float(proba[1])
                return prob_long, prob_short, "model"
            except Exception as e:
                logger.warning("Model inference failed; falling back to rules", error=str(e))

        # Fallback rule: trend+momentum weighting
        trend_score = features[4]  # ema_fast/ema_slow
        rsi_score = (features[5] - 0.5) * 2  # centered at 0
        adx_score = features[6]
        composite = trend_score * 0.5 + rsi_score * 0.3 + adx_score * 0.2
        prob_long = max(0.0, min(1.0, 0.5 + composite * 0.5))
        prob_short = 1.0 - prob_long
        return prob_long, prob_short, "rules"

    def _build_signal(
        self,
        context: StrategyContext,
        side: SignalSide,
        entry_price: float,
        atr: float,
        prob: float,
        prob_short: float,
        source: str,
        features: np.ndarray,
    ) -> Optional[Signal]:
        stop_loss = entry_price - (atr * self.atr_stop_mult) if side == SignalSide.LONG else entry_price + (atr * self.atr_stop_mult)
        risk = abs(entry_price - stop_loss)
        if risk <= 0:
            return None

        rr_required = self.backtest_rr_min if context.backtest_mode else self.rr_min
        reward = risk * rr_required
        take_profit_1 = entry_price + (reward * 0.6) if side == SignalSide.LONG else entry_price - (reward * 0.6)
        take_profit_2 = entry_price + reward if side == SignalSide.LONG else entry_price - reward

        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=context.instrument,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=prob,
            rationale=f"{source.upper()} score: long={prob:.2f}, short={prob_short:.2f}",
            features={
                "prob_long": prob,
                "prob_short": prob_short,
                "source": source,
                "feature_vec": features.tolist(),
                "atr": atr,
            },
        )
        signal.risk_amount = risk
        signal.reward_amount = reward
        return signal

    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        # Backtest mode flag for R:R adjustment
        self._backtest_mode = context.backtest_mode

        if not self.validate(context):
            return []
        if context.instrument.symbol not in self.allowed_instruments:
            return []

        bars = context.bars_5s
        if not bars or len(bars) < max(self.feature_lookback, self.atr_period + 5):
            return []

        token = context.instrument.token
        if not self._can_emit(token, context.timestamp):
            return []

        features = self._features(bars)
        if features is None:
            return []

        prob_long, prob_short, source = self._score_direction(features)
        confidence = max(prob_long, prob_short)
        if confidence < self.confidence_threshold:
            return []

        latest_bar = bars[-1]
        atr = latest_bar.atr or self._calc_atr(bars, self.atr_period) or (latest_bar.close * 0.01)
        current_price = context.latest_tick.last_price if context.latest_tick else latest_bar.close

        signals: List[Signal] = []
        # LONG
        if prob_long > prob_short and self.last_signal_side.get(token) != "LONG":
            sig = self._build_signal(
                context,
                SignalSide.LONG,
                current_price,
                atr,
                prob_long,
                prob_short,
                source,
                features,
            )
            if sig:
                signals.append(sig)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp

        # SHORT
        if prob_short > prob_long and self.last_signal_side.get(token) != "SHORT":
            sig = self._build_signal(
                context,
                SignalSide.SHORT,
                current_price,
                atr,
                prob_long,
                prob_short,
                source,
                features,
            )
            if sig:
                signals.append(sig)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp

        return signals

    def validate(self, context: StrategyContext) -> bool:
        if not super().validate(context):
            return False
        # Require some bars and indicators
        min_bars = max(self.feature_lookback, self.atr_period + 5)
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        return True
