"""Signal ranking and candidate scoring"""

import logging
from decimal import Decimal
from typing import Dict, List

from packages.core.models import RankedCandidate, Signal, TechnicalIndicators
from scipy import stats
import numpy as np

logger = logging.getLogger(__name__)


class RankingEngine:
    """Ranks trading signals based on multiple factors"""

    def __init__(self, weights: Dict[str, float], penalties: Dict[str, float], top_n: int = 5):
        self.weights = weights
        self.penalties = penalties
        self.top_n = top_n

    def rank_signals(
        self,
        signals: List[Signal],
        indicators_map: Dict[int, TechnicalIndicators],
        liquidity_scores: Dict[int, float],
        market_regime: str = "NORMAL",
    ) -> List[RankedCandidate]:
        """
        Rank signals and return top N candidates
        
        Args:
            signals: List of signals to rank
            indicators_map: Map of instrument_token -> indicators
            liquidity_scores: Map of instrument_token -> liquidity score
            market_regime: Current market regime
        
        Returns:
            List of ranked candidates (sorted by score)
        """
        if not signals:
            return []
        
        candidates = []
        
        for signal in signals:
            indicators = indicators_map.get(signal.instrument_token)
            liquidity = liquidity_scores.get(signal.instrument_token, 0.5)
            
            # Calculate feature scores
            feature_scores = self._calculate_feature_scores(signal, indicators, liquidity)
            
            # Calculate penalties
            penalty_scores = self._calculate_penalties(signal, indicators, liquidity)
            
            # Calculate total score
            total_score = self._calculate_total_score(feature_scores, penalty_scores)
            
            # Ensure score is between 0 and 1
            total_score = max(Decimal("0"), min(Decimal("1"), total_score))
            
            candidate = RankedCandidate(
                signal=signal,
                score=total_score,
                rank=0,  # Will be set after sorting
                feature_scores=feature_scores,
                penalties=penalty_scores,
                market_regime=market_regime,
                liquidity_score=Decimal(str(liquidity)),
                timestamp=signal.timestamp,
            )
            
            candidates.append(candidate)
        
        # Sort by score (descending)
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks
        for i, candidate in enumerate(candidates):
            candidate.rank = i + 1
        
        # Return top N
        return candidates[: self.top_n]

    def _calculate_feature_scores(
        self,
        signal: Signal,
        indicators: TechnicalIndicators | None,
        liquidity: float,
    ) -> Dict[str, Decimal]:
        """Calculate normalized feature scores"""
        scores = {}
        
        # Momentum score
        momentum_score = self._calculate_momentum_score(signal, indicators)
        scores["momentum"] = momentum_score * Decimal(str(self.weights.get("momentum", 0.25)))
        
        # Trend score
        trend_score = self._calculate_trend_score(signal, indicators)
        scores["trend"] = trend_score * Decimal(str(self.weights.get("trend", 0.25)))
        
        # Liquidity score
        liquidity_score = Decimal(str(liquidity))
        scores["liquidity"] = liquidity_score * Decimal(str(self.weights.get("liquidity", 0.20)))
        
        # Regime score
        regime_score = self._calculate_regime_score(signal, indicators)
        scores["regime"] = regime_score * Decimal(str(self.weights.get("regime", 0.15)))
        
        # R:R score
        rr_score = self._calculate_rr_score(signal)
        scores["rr"] = rr_score * Decimal(str(self.weights.get("rr", 0.15)))
        
        return scores

    def _calculate_momentum_score(
        self, signal: Signal, indicators: TechnicalIndicators | None
    ) -> Decimal:
        """Calculate momentum score (0-1)"""
        if not indicators or not indicators.rsi:
            return Decimal("0.5")
        
        rsi = float(indicators.rsi)
        
        # Normalize RSI to 0-1 scale
        # RSI 30-70 is normal range, outside is extreme
        if 30 <= rsi <= 70:
            # Middle range = moderate score
            score = 0.5 + ((rsi - 50) / 40) * 0.2
        elif rsi < 30:
            # Oversold = good for long, bad for short
            if "LONG" in signal.signal_type.value:
                score = 0.7 + ((30 - rsi) / 30) * 0.3
            else:
                score = 0.3
        else:  # rsi > 70
            # Overbought = good for short, bad for long
            if "SHORT" in signal.signal_type.value:
                score = 0.7 + ((rsi - 70) / 30) * 0.3
            else:
                score = 0.3
        
        return Decimal(str(score))

    def _calculate_trend_score(
        self, signal: Signal, indicators: TechnicalIndicators | None
    ) -> Decimal:
        """Calculate trend alignment score (0-1)"""
        if not indicators:
            return Decimal("0.5")
        
        score = 0.5
        
        # Check EMA alignment
        if indicators.ema_34 and indicators.ema_89:
            if "LONG" in signal.signal_type.value:
                if indicators.ema_34 > indicators.ema_89:
                    score += 0.2
            elif "SHORT" in signal.signal_type.value:
                if indicators.ema_34 < indicators.ema_89:
                    score += 0.2
        
        # Check Supertrend alignment
        if indicators.supertrend_direction:
            if "LONG" in signal.signal_type.value:
                if indicators.supertrend_direction > 0:
                    score += 0.2
            elif "SHORT" in signal.signal_type.value:
                if indicators.supertrend_direction < 0:
                    score += 0.2
        
        # Check ADX for trend strength
        if indicators.adx:
            adx = float(indicators.adx)
            if adx > 25:
                score += min(0.1, (adx - 25) / 100)
        
        return Decimal(str(min(1.0, score)))

    def _calculate_regime_score(
        self, signal: Signal, indicators: TechnicalIndicators | None
    ) -> Decimal:
        """Calculate market regime score (0-1)"""
        # TODO: Implement proper regime detection (volatility, IV rank, etc.)
        # For now, use ATR as a proxy
        if not indicators or not indicators.atr:
            return Decimal("0.5")
        
        # Higher ATR = higher volatility = potentially better opportunities
        # But also higher risk
        # This is a simplified version
        return Decimal("0.6")

    def _calculate_rr_score(self, signal: Signal) -> Decimal:
        """Calculate risk:reward score (0-1)"""
        rr = float(signal.expected_rr)
        
        # Normalize R:R ratio
        # R:R >= 2.0 is excellent (score 1.0)
        # R:R = 1.0 is minimum (score 0.3)
        if rr >= 2.0:
            score = 1.0
        elif rr >= 1.0:
            score = 0.3 + ((rr - 1.0) / 1.0) * 0.7
        else:
            score = 0.1
        
        return Decimal(str(score))

    def _calculate_penalties(
        self,
        signal: Signal,
        indicators: TechnicalIndicators | None,
        liquidity: float,
    ) -> Dict[str, Decimal]:
        """Calculate penalty scores"""
        penalties_dict = {}
        
        # Illiquidity penalty
        if liquidity < 0.3:
            penalties_dict["illiquid"] = Decimal(str(self.penalties.get("illiquid", -0.3)))
        
        # Far from VWAP penalty
        if indicators and indicators.vwap and signal.entry_price:
            vwap_deviation = abs(
                float(signal.entry_price - indicators.vwap) / float(indicators.vwap)
            )
            if vwap_deviation > 0.02:  # More than 2% from VWAP
                penalties_dict["far_from_vwap"] = Decimal(
                    str(self.penalties.get("far_from_vwap", -0.2))
                )
        
        # TODO: Add "into_news" penalty when event calendar is integrated
        
        return penalties_dict

    def _calculate_total_score(
        self, feature_scores: Dict[str, Decimal], penalties: Dict[str, Decimal]
    ) -> Decimal:
        """Calculate total score from features and penalties"""
        # Sum feature scores
        total = sum(feature_scores.values())
        
        # Apply penalties
        total += sum(penalties.values())
        
        return total


class FeatureNormalizer:
    """Normalizes features using z-score and percentile methods"""

    def __init__(self):
        self.feature_history: Dict[str, List[float]] = {}
        self.max_history = 1000

    def normalize_zscore(self, feature_name: str, value: float) -> float:
        """
        Normalize using z-score
        
        Returns value between -3 and 3 (usually)
        """
        if feature_name not in self.feature_history:
            self.feature_history[feature_name] = []
        
        history = self.feature_history[feature_name]
        history.append(value)
        
        # Keep only recent history
        if len(history) > self.max_history:
            history.pop(0)
        
        if len(history) < 2:
            return 0.0
        
        mean = np.mean(history)
        std = np.std(history)
        
        if std == 0:
            return 0.0
        
        z_score = (value - mean) / std
        return float(z_score)

    def normalize_percentile(self, feature_name: str, value: float) -> float:
        """
        Normalize using percentile rank
        
        Returns value between 0 and 1
        """
        if feature_name not in self.feature_history:
            self.feature_history[feature_name] = []
        
        history = self.feature_history[feature_name]
        history.append(value)
        
        if len(history) > self.max_history:
            history.pop(0)
        
        if len(history) < 2:
            return 0.5
        
        percentile = stats.percentileofscore(history, value) / 100.0
        return percentile

