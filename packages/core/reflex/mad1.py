"""
MAD-1 (Market Anomaly Detection) - Level 10
===========================================

Level 10: Microstructure Analysis.

While Level 8 checked for simple velocity (price drops), Level 10 analyzes the
*microstructure* of the market. It detects invisible precursors to a crash:
- Spreads blowing out
- Liquidity evaporating
- Volatility spiking

Often milliseconds before the price actually collapses.
"""

import time
import math
from collections import deque
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("reflex_mad1")


class MAD1:
    """
    Market Anomaly Detection (Type 1) - Level 10.
    
    Detects market microstructure anomalies using statistical Z-scores:
    - Price velocity (legacy)
    - Spread blowouts
    - Liquidity evaporation
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        crash_threshold_pct: float = 1.0,
        window_seconds: int = 30
    ):
        """
        Initialize MAD-1.
        
        Args:
            config: Configuration dictionary with:
                - liquidity_drop_pct: Percentage drop in liquidity to trigger (default: 0.60 = 60%)
                - spread_sigma_threshold: Z-score threshold for spread (default: 3.0)
            crash_threshold_pct: Percentage change threshold for price (legacy, default: 1.0)
            window_seconds: Rolling window size in seconds (default: 30)
        """
        # Legacy parameters (for backward compatibility)
        if config is None:
            config = {}
        
        self.threshold = config.get("crash_threshold_pct", crash_threshold_pct) / 100.0
        self.window = config.get("window_seconds", window_seconds)
        
        # Level 10: Microstructure parameters
        self.liquidity_drop_pct = config.get("liquidity_drop_pct", 0.60)  # 60% drop triggers
        self.spread_sigma_threshold = config.get("spread_sigma_threshold", 3.0)  # 3-sigma spread
        
        # Data structures
        self.ticks = deque()  # Stores (timestamp, price, spread, liquidity)
        self.locked = False
        self.cause: Optional[str] = None  # Reason for trigger
        
        # Statistics for Z-score calculation
        self.spread_history: deque = deque(maxlen=100)  # Last 100 spreads
        self.liquidity_history: deque = deque(maxlen=100)  # Last 100 liquidity values
    
    def update(self, tick: Dict[str, Any]) -> bool:
        """
        Ingest a tick. Returns True if ANOMALY detected.
        
        Args:
            tick: Tick dictionary with:
                - last_price: Last traded price
                - depth: Order book depth with 'buy' and 'sell' arrays
                    Each array contains dicts with 'price' and 'quantity'
                OR a Tick object (will be converted)
        
        Returns:
            True if anomaly detected, False otherwise
        """
        if self.locked:
            return True  # Once triggered, stay triggered until manual reset
        
        # Handle Tick object (convert to dict)
        if hasattr(tick, 'last_price'):
            tick_dict = {
                'last_price': tick.last_price,
                'depth': {
                    'buy': [{'price': tick.bid, 'quantity': tick.bid_quantity}] if tick.bid > 0 else [],
                    'sell': [{'price': tick.ask, 'quantity': tick.ask_quantity}] if tick.ask > 0 else []
                }
            }
            tick = tick_dict
        
        # Extract data
        price = tick.get('last_price', 0.0)
        depth = tick.get('depth', {})
        
        # Calculate spread
        buy_side = depth.get('buy', [])
        sell_side = depth.get('sell', [])
        
        spread = 0.0
        liquidity = 0.0
        
        if buy_side and sell_side:
            best_bid = buy_side[0].get('price', 0.0)
            best_ask = sell_side[0].get('price', 0.0)
            spread = best_ask - best_bid
            
            # Calculate liquidity (sum of top 3 levels on each side)
            bid_liquidity = sum(level.get('quantity', 0) for level in buy_side[:3])
            ask_liquidity = sum(level.get('quantity', 0) for level in sell_side[:3])
            liquidity = (bid_liquidity + ask_liquidity) / 2.0  # Average
        
        now = time.time()
        
        # Store tick data
        self.ticks.append((now, price, spread, liquidity))
        
        # Update statistics
        if spread > 0:
            self.spread_history.append(spread)
        if liquidity > 0:
            self.liquidity_history.append(liquidity)
        
        # Prune old ticks
        while self.ticks and (now - self.ticks[0][0] > self.window):
            self.ticks.popleft()
        
        if not self.ticks or len(self.ticks) < 10:
            return False  # Need at least 10 ticks for meaningful analysis
        
        # Level 10: Check for microstructure anomalies
        
        # 1. Check Liquidity Vacuum
        if self._check_liquidity_collapse(liquidity):
            self.locked = True
            self.cause = "LIQUIDITY_VACUUM"
            logger.critical(
                f"🚨 MAD-1 TRIGGER: Liquidity collapsed! "
                f"Current: {liquidity:.0f}, Baseline: {self._get_baseline_liquidity():.0f}"
            )
            return True
        
        # 2. Check Spread Blowout (Z-score)
        if self._check_spread_blowout(spread):
            self.locked = True
            self.cause = "SPREAD_BLOWOUT"
            logger.critical(
                f"🚨 MAD-1 TRIGGER: Spread blowout detected! "
                f"Spread: {spread:.2f}, Z-score: {self._calculate_spread_zscore(spread):.2f}"
            )
            return True
        
        # 3. Legacy: Check Price Velocity (for backward compatibility)
        oldest_price = self.ticks[0][1]
        if oldest_price > 0:
            change = abs((price - oldest_price) / oldest_price)
            if change > self.threshold:
                self.locked = True
                self.cause = "PRICE_VELOCITY"
                logger.critical(
                    f"🚨 MAD-1 TRIGGER: Price moved {change*100:.2f}% in {self.window}s!"
                )
                return True
        
        return False
    
    def _check_liquidity_collapse(self, current_liquidity: float) -> bool:
        """
        Check if liquidity has collapsed.
        
        Args:
            current_liquidity: Current liquidity value
        
        Returns:
            True if liquidity collapse detected
        """
        if len(self.liquidity_history) < 20:
            return False  # Need baseline
        
        baseline = self._get_baseline_liquidity()
        if baseline <= 0:
            return False
        
        drop_pct = (baseline - current_liquidity) / baseline
        return drop_pct >= self.liquidity_drop_pct
    
    def _get_baseline_liquidity(self) -> float:
        """
        Get baseline liquidity (median of recent history).
        
        Returns:
            Median liquidity value
        """
        if not self.liquidity_history:
            return 0.0
        
        sorted_liquidity = sorted(self.liquidity_history)
        n = len(sorted_liquidity)
        if n % 2 == 0:
            return (sorted_liquidity[n//2 - 1] + sorted_liquidity[n//2]) / 2.0
        return sorted_liquidity[n//2]
    
    def _check_spread_blowout(self, current_spread: float) -> bool:
        """
        Check if spread has blown out using Z-score.
        
        Args:
            current_spread: Current spread value
        
        Returns:
            True if spread blowout detected
        """
        if len(self.spread_history) < 20:
            return False  # Need baseline
        
        z_score = self._calculate_spread_zscore(current_spread)
        return abs(z_score) >= self.spread_sigma_threshold
    
    def _calculate_spread_zscore(self, current_spread: float) -> float:
        """
        Calculate Z-score for spread.
        
        Args:
            current_spread: Current spread value
        
        Returns:
            Z-score
        """
        if not self.spread_history:
            return 0.0
        
        # Calculate mean and std dev
        spreads = list(self.spread_history)
        mean = sum(spreads) / len(spreads)
        
        variance = sum((x - mean) ** 2 for x in spreads) / len(spreads)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0001
        
        # Calculate Z-score
        if std_dev > 0:
            z_score = (current_spread - mean) / std_dev
            return z_score
        
        return 0.0
    
    def reset(self):
        """Reset MAD-1 (clear ticks and unlock)"""
        self.ticks.clear()
        self.spread_history.clear()
        self.liquidity_history.clear()
        self.locked = False
        self.cause = None
        logger.info("🔄 MAD-1 reset")
