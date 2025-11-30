"""WebSocket market data streaming and aggregation"""
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import structlog
from kiteconnect import KiteTicker

from packages.core.config import Settings
from packages.core.models import Bar, Tick
from packages.core.indicators import IndicatorCalculator
from packages.core.kite_ws import SafeKiteTicker

logger = structlog.get_logger(__name__)


class TickAggregator:
    """Aggregates ticks into bars with configurable windows"""
    
    def __init__(self, token: int, window_seconds: int = 1):
        self.token = token
        self.window_seconds = window_seconds
        
        # Current bar being built
        self.current_bar: Optional[Bar] = None
        self.current_window_start: Optional[datetime] = None
        
        # Historical bars
        self.bars: deque = deque(maxlen=500)  # Keep last 500 bars
        
    def add_tick(self, tick: Tick) -> Optional[Bar]:
        """
        Add a tick and potentially emit a completed bar.
        
        Returns:
            Completed bar if window closed, None otherwise
        """
        # Initialize window if needed
        if self.current_window_start is None:
            self.current_window_start = self._floor_timestamp(tick.timestamp)
            self.current_bar = Bar(
                token=self.token,
                timestamp=self.current_window_start,
                open=tick.last_price,
                high=tick.last_price,
                low=tick.last_price,
                close=tick.last_price,
                volume=tick.last_quantity,
                oi=tick.oi
            )
            return None
        
        # Check if we need to close current window
        expected_window_start = self._floor_timestamp(tick.timestamp)
        
        if expected_window_start > self.current_window_start:
            # Close current bar
            completed_bar = self.current_bar
            if completed_bar:
                self.bars.append(completed_bar)
            
            # Start new bar
            self.current_window_start = expected_window_start
            self.current_bar = Bar(
                token=self.token,
                timestamp=self.current_window_start,
                open=tick.last_price,
                high=tick.last_price,
                low=tick.last_price,
                close=tick.last_price,
                volume=tick.last_quantity,
                oi=tick.oi
            )
            
            return completed_bar
        
        # Update current bar
        if self.current_bar:
            self.current_bar.high = max(self.current_bar.high, tick.last_price)
            self.current_bar.low = min(self.current_bar.low, tick.last_price)
            self.current_bar.close = tick.last_price
            self.current_bar.volume += tick.last_quantity
            self.current_bar.oi = tick.oi
        
        return None
    
    def _floor_timestamp(self, timestamp: datetime) -> datetime:
        """Floor timestamp to window boundary"""
        epoch = timestamp.timestamp()
        floored_epoch = (epoch // self.window_seconds) * self.window_seconds
        return datetime.fromtimestamp(floored_epoch)
    
    def get_bars(self, n: int = 100) -> List[Bar]:
        """Get last n bars"""
        return list(self.bars)[-n:]
    
    def get_latest_bar(self) -> Optional[Bar]:
        """Get most recent completed bar"""
        if self.bars:
            return self.bars[-1]
        return None


class MarketDataStream:
    """
    Manages WebSocket connection to Kite ticker and aggregates ticks into bars.
    Computes technical indicators on bars.
    """
    
    def __init__(
        self,
        settings: Settings,
        window_seconds: List[int] = [1, 5],
        on_bar_callback: Optional[Callable] = None
    ):
        self.settings = settings
        self.window_seconds = window_seconds
        self.on_bar_callback = on_bar_callback
        self.heartbeat_callback: Optional[Callable[[], None]] = None
        
        # Kite WebSocket client
        self.kws: Optional[KiteTicker] = None
        self.safe_kws: Optional[SafeKiteTicker] = None
        
        # Aggregators per token per window
        self.aggregators: Dict[int, Dict[int, TickAggregator]] = defaultdict(dict)
        
        # Indicator calculator
        self.indicator_calc = IndicatorCalculator()
        
        # Subscribed tokens
        self.subscribed_tokens: List[int] = []
        
        # Connection state
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.settings.ws_max_reconnect_attempts
        
        # Latest ticks
        self.latest_ticks: Dict[int, Tick] = {}
        self.last_tick_time: Optional[datetime] = None
        
        # Liveness monitor
        self._liveness_stop: Optional[threading.Event] = None
        self._liveness_thread: Optional[threading.Thread] = None
        
    def initialize(self) -> None:
        """Initialize KiteTicker client"""
        self.kws = KiteTicker(
            self.settings.kite_api_key,
            self.settings.kite_access_token
        )
        
        # Wrap in SafeKiteTicker for graceful shutdown
        self.safe_kws = SafeKiteTicker(self.kws)
        
        # Assign callbacks
        self.kws.on_connect = self._on_connect
        self.kws.on_ticks = self._on_ticks
        self.kws.on_close = self._on_close
        self.kws.on_error = self._on_error
        self.kws.on_reconnect = self._on_reconnect
        self.kws.on_noreconnect = self._on_noreconnect
    
    def _on_connect(self, ws: Any, response: Any) -> None:
        """Callback on successful connection"""
        logger.info("WebSocket connected", response=response)
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # Touch heartbeat immediately on connection
        from packages.core.heartbeats import touch_marketdata
        touch_marketdata()
        
        # Resubscribe to tokens if any
        if self.subscribed_tokens:
            logger.info(f"Resubscribing to {len(self.subscribed_tokens)} tokens after reconnection")
            self.subscribe(self.subscribed_tokens)
        else:
            logger.info("No tokens to resubscribe (will subscribe on next universe update)")
    
    def _on_ticks(self, ws: Any, ticks: List[Dict]) -> None:
        """Callback when ticks are received"""
        from packages.core.heartbeats import touch_marketdata
        touch_marketdata()
        try:
            self.last_tick_time = datetime.utcnow()
            for raw_tick in ticks:
                # Parse tick
                tick = self._parse_tick(raw_tick)
                if not tick:
                    continue
                
                # Store latest tick
                self.latest_ticks[tick.token] = tick
                
                # REFLEX SYSTEM (Level 8) - Process tick through reflex engine
                # This happens BEFORE aggregation to ensure zero-latency crash detection
                if hasattr(self, 'reflex_engine') and self.reflex_engine:
                    try:
                        self.reflex_engine.on_tick(tick)
                    except Exception as e:
                        logger.error(f"Error in reflex engine: {e}", exc_info=True)
                
                # Update heartbeat if provided
                if self.heartbeat_callback:
                    try:
                        self.heartbeat_callback()
                    except Exception:
                        pass
                
                # Aggregate into bars for each window
                if tick.token in self.aggregators:
                    for window_sec, aggregator in self.aggregators[tick.token].items():
                        completed_bar = aggregator.add_tick(tick)
                        
                        if completed_bar:
                            # Compute indicators
                            self._compute_indicators(tick.token, window_sec)
                            
                            # Callback
                            if self.on_bar_callback:
                                bars = aggregator.get_bars(100)
                                asyncio.create_task(
                                    self.on_bar_callback(tick.token, window_sec, bars)
                                )
        
        except Exception as e:
            logger.error("Error processing ticks", error=str(e))
    
    def _parse_tick(self, raw_tick: Dict) -> Optional[Tick]:
        """Parse raw tick data into Tick object"""
        try:
            return Tick(
                token=raw_tick["instrument_token"],
                timestamp=datetime.now(),  # Kite doesn't provide tick timestamp
                last_price=raw_tick.get("last_price", 0.0),
                last_quantity=raw_tick.get("last_quantity", 0),
                volume=raw_tick.get("volume", 0),
                bid=raw_tick.get("depth", {}).get("buy", [{}])[0].get("price", 0.0) if raw_tick.get("depth") else 0.0,
                ask=raw_tick.get("depth", {}).get("sell", [{}])[0].get("price", 0.0) if raw_tick.get("depth") else 0.0,
                bid_quantity=raw_tick.get("depth", {}).get("buy", [{}])[0].get("quantity", 0) if raw_tick.get("depth") else 0,
                ask_quantity=raw_tick.get("depth", {}).get("sell", [{}])[0].get("quantity", 0) if raw_tick.get("depth") else 0,
                open=raw_tick.get("ohlc", {}).get("open", 0.0),
                high=raw_tick.get("ohlc", {}).get("high", 0.0),
                low=raw_tick.get("ohlc", {}).get("low", 0.0),
                close=raw_tick.get("ohlc", {}).get("close", 0.0),
                oi=raw_tick.get("oi", 0),
                oi_day_high=raw_tick.get("oi_day_high", 0),
                oi_day_low=raw_tick.get("oi_day_low", 0)
            )
        except Exception as e:
            logger.warning("Failed to parse tick", error=str(e), tick=raw_tick)
            return None
    
    def _compute_indicators(self, token: int, window_sec: int) -> None:
        """Compute technical indicators for a token's bars"""
        try:
            aggregator = self.aggregators[token][window_sec]
            bars = aggregator.get_bars(200)  # Get enough bars for indicators
            
            if len(bars) < 50:  # Need minimum bars
                return
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume
                }
                for b in bars
            ])
            
            # Compute indicators
            indicators = self.indicator_calc.compute_all(df)
            
            # Attach indicators to latest bar
            if bars:
                latest_bar = bars[-1]
                latest_bar.vwap = indicators.get("vwap")
                latest_bar.atr = indicators.get("atr")
                latest_bar.rsi = indicators.get("rsi")
                latest_bar.adx = indicators.get("adx")
                latest_bar.ema_fast = indicators.get("ema_fast")
                latest_bar.ema_slow = indicators.get("ema_slow")
                latest_bar.supertrend = indicators.get("supertrend")
                latest_bar.supertrend_direction = indicators.get("supertrend_direction")
                latest_bar.macd = indicators.get("macd")
                latest_bar.macd_signal = indicators.get("macd_signal")
                latest_bar.macd_histogram = indicators.get("macd_histogram")
                latest_bar.bb_upper = indicators.get("bb_upper")
                latest_bar.bb_middle = indicators.get("bb_middle")
                latest_bar.bb_lower = indicators.get("bb_lower")
                latest_bar.stoch_k = indicators.get("stoch_k")
                latest_bar.stoch_d = indicators.get("stoch_d")
                latest_bar.cci = indicators.get("cci")
                latest_bar.sar = indicators.get("sar")
                latest_bar.ichi_tenkan = indicators.get("ichi_tenkan")
                latest_bar.ichi_kijun = indicators.get("ichi_kijun")
                latest_bar.ichi_senkou_a = indicators.get("ichi_senkou_a")
                latest_bar.ichi_senkou_b = indicators.get("ichi_senkou_b")
                latest_bar.pivot = indicators.get("pivot")
                latest_bar.pivot_r1 = indicators.get("pivot_r1")
                latest_bar.pivot_r2 = indicators.get("pivot_r2")
                latest_bar.pivot_s1 = indicators.get("pivot_s1")
                latest_bar.pivot_s2 = indicators.get("pivot_s2")
        
        except Exception as e:
            logger.error("Failed to compute indicators", token=token, error=str(e))
    
    def _on_close(self, ws: Any, code: int, reason: str) -> None:
        """Callback on connection close"""
        logger.warning("WebSocket closed", code=code, reason=reason)
        self.is_connected = False
    
    def _on_error(self, ws: Any, code: int, reason: str) -> None:
        """Callback on error"""
        logger.error("WebSocket error", code=code, reason=reason)
        if code == 403:
            logger.critical(
                "❌ WebSocket 403 Forbidden - This usually means WebSocket streaming is not enabled for your Kite app. "
                "Go to https://developers.kite.trade/apps and enable 'Websocket streaming' for API key: %s",
                self.settings.kite_api_key
            )
    
    def _on_reconnect(self, ws: Any, attempts: int) -> None:
        """Callback on reconnection attempt"""
        logger.info("WebSocket reconnecting", attempt=attempts)
        self.reconnect_attempts = attempts
    
    def _on_noreconnect(self, ws: Any) -> None:
        """Callback when max reconnection attempts reached"""
        logger.error("WebSocket max reconnection attempts reached")
        self.is_connected = False
    
    def subscribe(self, tokens: List[int], mode: str = "full") -> None:
        """
        Subscribe to instrument tokens.
        
        Args:
            tokens: List of instrument tokens
            mode: 'ltp', 'quote', or 'full'
        """
        if not self.kws or not self.is_connected:
            logger.warning("Cannot subscribe, WebSocket not connected")
            return
        
        try:
            # Create aggregators for new tokens
            for token in tokens:
                if token not in self.aggregators:
                    self.aggregators[token] = {}
                    for window_sec in self.window_seconds:
                        self.aggregators[token][window_sec] = TickAggregator(token, window_sec)
            
            # Subscribe
            self.kws.subscribe(tokens)
            
            # Set mode
            mode_map = {"ltp": self.kws.MODE_LTP, "quote": self.kws.MODE_QUOTE, "full": self.kws.MODE_FULL}
            self.kws.set_mode(mode_map.get(mode, self.kws.MODE_FULL), tokens)
            
            self.subscribed_tokens.extend([t for t in tokens if t not in self.subscribed_tokens])
            
            logger.info(f"Subscribed to {len(tokens)} instruments in {mode} mode")
        
        except Exception as e:
            logger.error("Failed to subscribe", error=str(e))
    
    def unsubscribe(self, tokens: List[int]) -> None:
        """Unsubscribe from instrument tokens"""
        if not self.kws or not self.is_connected:
            return
        
        try:
            self.kws.unsubscribe(tokens)
            self.subscribed_tokens = [t for t in self.subscribed_tokens if t not in tokens]
            
            # Clean up aggregators
            for token in tokens:
                if token in self.aggregators:
                    del self.aggregators[token]
            
            logger.info(f"Unsubscribed from {len(tokens)} instruments")
        
        except Exception as e:
            logger.error("Failed to unsubscribe", error=str(e))
    
    def get_latest_tick(self, token: int) -> Optional[Tick]:
        """Get latest tick for a token"""
        return self.latest_ticks.get(token)
    
    def get_bars(self, token: int, window_sec: int, n: int = 100) -> List[Bar]:
        """Get bars for a token and window"""
        if token in self.aggregators and window_sec in self.aggregators[token]:
            return self.aggregators[token][window_sec].get_bars(n)
        return []
    
    def get_latest_bar(self, token: int, window_sec: int) -> Optional[Bar]:
        """Get latest completed bar for a token and window"""
        if token in self.aggregators and window_sec in self.aggregators[token]:
            return self.aggregators[token][window_sec].get_latest_bar()
        return None
    
    def start(self) -> None:
        """Start WebSocket connection"""
        if not self.kws:
            self.initialize()
        
        # Verify token is set
        if not self.settings.kite_access_token:
            logger.error("Cannot start WebSocket: KITE_ACCESS_TOKEN not set")
            self.is_connected = False
            return
        
        if not self.settings.kite_api_key:
            logger.error("Cannot start WebSocket: KITE_API_KEY not set")
            self.is_connected = False
            return
        
        logger.info(
            "Starting WebSocket connection",
            api_key=self.settings.kite_api_key[:10] + "...",
            token_set=bool(self.settings.kite_access_token)
        )
        
        try:
            # Run in separate thread
            self.kws.connect(threaded=True)
            logger.info("WebSocket connect() called, waiting for connection callback...")
            
            # Start liveness watchdog to detect stale sockets
            self._start_liveness_monitor()
            
            # Note: Connection is asynchronous, is_connected will be set by _on_connect callback
            # We can't block here, but we log that we've initiated the connection
        except Exception as e:
            logger.error(f"Failed to start WebSocket connection: {e}", exc_info=True)
            self.is_connected = False
            raise
    
    def stop(self) -> None:
        """Stop WebSocket connection"""
        if self.safe_kws:
            logger.info("Stopping WebSocket connection")
            self.safe_kws.stop()
            self.is_connected = False
            self.kws = None
            self.safe_kws = None
        elif self.kws:
            # Fallback if safe_kws not initialized
            logger.info("Stopping WebSocket connection (fallback)")
            try:
                if hasattr(self.kws, 'close'):
                    self.kws.close()
                elif hasattr(self.kws, 'stop'):
                    self.kws.stop()
            except Exception as e:
                logger.warning(f"Error stopping WebSocket: {e}")
            finally:
                self.is_connected = False
                self.kws = None
        
        # Stop liveness monitor
        if self._liveness_stop:
            self._liveness_stop.set()
        if self._liveness_thread and self._liveness_thread.is_alive():
            self._liveness_thread.join(timeout=2)
        self._liveness_stop = None
        self._liveness_thread = None

    # ------------------------------------------------------------------
    # Liveness / stale-tick monitoring
    # ------------------------------------------------------------------
    def _start_liveness_monitor(self, stale_seconds: float = 10.0, check_interval: float = 5.0) -> None:
        """Start background thread to detect stale tick streams."""
        if self._liveness_thread and self._liveness_thread.is_alive():
            return
        self._liveness_stop = threading.Event()
        self._liveness_thread = threading.Thread(
            target=self._liveness_watchdog,
            args=(stale_seconds, check_interval),
            daemon=True
        )
        self._liveness_thread.start()

    def _liveness_watchdog(self, stale_seconds: float, check_interval: float) -> None:
        """Watch for stale ticks and force reconnect if needed."""
        while self._liveness_stop and not self._liveness_stop.is_set():
            try:
                if self.is_connected and self.last_tick_time:
                    elapsed = (datetime.utcnow() - self.last_tick_time).total_seconds()
                    if elapsed > stale_seconds:
                        logger.warning(
                            "Tick stream stale; forcing WebSocket reconnect",
                            elapsed_seconds=elapsed
                        )
                        self._force_reconnect()
                        # avoid immediate re-trigger
                        self.last_tick_time = datetime.utcnow()
            except Exception as e:
                logger.warning("Liveness watchdog error", error=str(e))
            # Sleep outside of try to avoid tight loop on errors
            if self._liveness_stop and self._liveness_stop.wait(timeout=check_interval):
                break

    def _force_reconnect(self) -> None:
        """Force a reconnect when ticks are stale."""
        try:
            self.stop()
        except Exception as e:
            logger.warning("Error stopping stale WebSocket", error=str(e))
        try:
            self.start()
        except Exception as e:
            logger.error("Error restarting WebSocket after stale detection", error=str(e))
