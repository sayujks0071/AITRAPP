"""
Reflex System - The Nervous System
===================================

Connects MAD-1 to the Emergency Brake and manages the tick stream.
Zero-latency loop that processes live ticks.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any, Callable

from packages.core.reflex.mad1 import MAD1
from packages.core.reflex.brake import EmergencyBrake
from packages.core.models import Tick

logger = logging.getLogger("reflex")


class ReflexSystem:
    """
    Reflex System - Zero-latency emergency response system.
    
    Connects MAD-1 (Market Anomaly Detection) to Emergency Brake.
    Processes ticks in real-time and triggers emergency actions when anomalies are detected.
    """
    
    def __init__(
        self,
        mad1: MAD1,
        brake: EmergencyBrake,
        enabled: bool = True
    ):
        """
        Initialize Reflex System.
        
        Args:
            mad1: MAD-1 instance for anomaly detection
            brake: EmergencyBrake instance for emergency actions
            enabled: Whether the reflex system is enabled
        """
        self.mad1 = mad1
        self.brake = brake
        self.enabled = enabled
        
        # Statistics
        self.ticks_processed = 0
        self.crashes_detected = 0
        self.last_crash_time: Optional[datetime] = None
        
        # Callback for external monitoring
        self.on_crash_callback: Optional[Callable] = None
    
    def on_tick(self, tick: Tick) -> None:
        """
        Process a tick through the reflex system.
        
        This is the zero-latency entry point. Called directly from market data stream.
        
        Args:
            tick: Market tick data
        """
        if not self.enabled:
            return
        
        self.ticks_processed += 1
        
        # Level 10: Pass full tick dictionary to MAD-1 for microstructure analysis
        # Convert Tick object to dictionary format for MAD-1
        tick_dict = {
            'last_price': tick.last_price,
            'depth': {
                'buy': [{'price': tick.bid, 'quantity': tick.bid_quantity}] if tick.bid > 0 else [],
                'sell': [{'price': tick.ask, 'quantity': tick.ask_quantity}] if tick.ask > 0 else []
            }
        }
        
        # Check for anomaly using MAD-1 (Level 10: microstructure analysis)
        crash_detected = self.mad1.update(tick_dict)
        
        if crash_detected:
            self._handle_crash(tick)
    
    def on_tick_raw(self, token: int, price: float, timestamp: Optional[datetime] = None, 
                    bid: float = 0.0, ask: float = 0.0, bid_qty: int = 0, ask_qty: int = 0) -> None:
        """
        Process a raw tick (alternative entry point).
        
        Args:
            token: Instrument token
            price: Current price
            timestamp: Tick timestamp (defaults to now)
            bid: Best bid price
            ask: Best ask price
            bid_qty: Best bid quantity
            ask_qty: Best ask quantity
        """
        if not self.enabled:
            return
        
        self.ticks_processed += 1
        
        # Level 10: Pass full tick dictionary to MAD-1
        tick_dict = {
            'last_price': price,
            'depth': {
                'buy': [{'price': bid, 'quantity': bid_qty}] if bid > 0 else [],
                'sell': [{'price': ask, 'quantity': ask_qty}] if ask > 0 else []
            }
        }
        
        # Check for anomaly using MAD-1
        crash_detected = self.mad1.update(tick_dict)
        
        if crash_detected:
            # Create a minimal tick for crash handling
            tick = Tick(
                token=token,
                timestamp=timestamp or datetime.now(),
                last_price=price,
                bid=bid,
                ask=ask,
                bid_quantity=bid_qty,
                ask_quantity=ask_qty
            )
            self._handle_crash(tick)
    
    def _handle_crash(self, tick: Tick) -> None:
        """
        Handle crash detection - trigger emergency brake.
        
        Args:
            tick: Tick that triggered the crash
        """
        self.crashes_detected += 1
        self.last_crash_time = datetime.now()
        
        logger.critical(
            f"🚨 REFLEX SYSTEM: Crash detected on token {tick.token} "
            f"at price {tick.last_price:.2f}. Pulling emergency brake!"
        )
        
        # Trigger emergency brake asynchronously
        # Use asyncio.create_task to avoid blocking
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.brake.pull(reason=f"CRASH_DETECTED_TOKEN_{tick.token}")
                )
            else:
                # If no event loop, run synchronously (not ideal but better than nothing)
                asyncio.run(self.brake.pull(reason=f"CRASH_DETECTED_TOKEN_{tick.token}"))
        except RuntimeError:
            # No event loop available, create one
            asyncio.run(self.brake.pull(reason=f"CRASH_DETECTED_TOKEN_{tick.token}"))
        
        # Call external callback if set
        if self.on_crash_callback:
            try:
                self.on_crash_callback(tick, self.crashes_detected)
            except Exception as e:
                logger.error(f"Error in crash callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get reflex system statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "enabled": self.enabled,
            "ticks_processed": self.ticks_processed,
            "crashes_detected": self.crashes_detected,
            "last_crash_time": self.last_crash_time.isoformat() if self.last_crash_time else None,
            "brake_engaged": self.brake.is_engaged,
            "mad1_locked": self.mad1.locked,
            "velocity": self.get_velocity()
        }
    
    def enable(self):
        """Enable the reflex system"""
        self.enabled = True
        logger.info("✅ Reflex System enabled")
    
    def disable(self):
        """Disable the reflex system"""
        self.enabled = False
        logger.warning("⚠️ Reflex System disabled")
    
    def reset(self):
        """Reset reflex system (clear history, reset brake)"""
        self.mad1.reset()
        self.brake.reset()
        self.ticks_processed = 0
        self.crashes_detected = 0
        self.last_crash_time = None
        logger.info("🔄 Reflex System reset")
    
    def get_velocity(self) -> Optional[float]:
        """
        Get current price velocity (for monitoring).
        
        Returns:
            Velocity in %/second, or None if insufficient data
        """
        if not self.mad1.ticks or len(self.mad1.ticks) < 2:
            return None
        
        import time
        now = time.time()
        # Tick structure: (timestamp, price, spread, liquidity)
        oldest_ts, oldest_price = self.mad1.ticks[0][0], self.mad1.ticks[0][1]
        latest_ts, latest_price = self.mad1.ticks[-1][0], self.mad1.ticks[-1][1]
        
        if oldest_price <= 0:
            return None
        
        change_pct = ((latest_price - oldest_price) / oldest_price) * 100
        time_diff = now - oldest_ts
        
        if time_diff > 0:
            return change_pct / time_diff
        
        return None

