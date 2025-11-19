"""
Shared Delta-Based Option-Chain Selector

Used by:
  - IntradayShortStrangleV1
  - TrendCreditSpreadV1

Provides consistent delta-based strike selection across strategies.

Connects:
  1. Instrument Manager (What exists?)
  2. Greeks Engine (What is the Delta?)
  3. Broker (What is the Price?)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple, Literal
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)

Side = Literal["CALL", "PUT"]


@dataclass
class OptionCandidate:
    """Represents an option contract candidate with Greeks"""
    symbol: str
    token: int
    strike: float
    side: Side
    expiry: str  # ISO date string or datetime
    ltp: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    iv: Optional[float] = None


class DeltaOptionSelector:
    """
    Shared intelligence for Option Selection.
    
    Connects:
      1. Instrument Manager (What exists?)
      2. Greeks Engine (What is the Delta?)
      3. Broker (What is the Price?)
    """

    def __init__(
        self,
        instrument_manager: Any,
        broker_client: Any,
        greeks_engine: Optional[Any] = None,
    ):
        self.instrument_manager = instrument_manager
        self.greeks_engine = greeks_engine
        self.broker = broker_client

    def _get_options_from_manager(
        self,
        underlying: str,
        expiry_kind: str = "nearest",
        max_dte: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get raw option instruments from instrument manager.
        
        Returns list of dicts with: {symbol, token, strike, side, expiry, tradingsymbol, exchange}
        """
        options = []
        now = datetime.now()
        
        # Try to use instrument_manager.get_options() if available
        if hasattr(self.instrument_manager, 'get_options'):
            try:
                raw_opts = self.instrument_manager.get_options(underlying, expiry_kind)
                if raw_opts:
                    return raw_opts
            except Exception as e:
                logger.debug(f"[DeltaOptionSelector] get_options() failed: {e}, falling back to manual scan")
        
        # Fallback: manual scan of _instruments
        if not hasattr(self.instrument_manager, '_instruments'):
            logger.warning(f"[DeltaOptionSelector] Instrument manager has no _instruments attribute")
            return options
        
        for token, inst in self.instrument_manager._instruments.items():
            if inst.symbol != underlying:
                continue
            
            if not inst.is_option:
                continue
            
            # Filter by expiry
            if inst.expiry:
                dte = (inst.expiry.date() - now.date()).days
                if dte < 0 or dte > max_dte:
                    continue
            else:
                continue
            
            # Determine side
            side: Side = "CALL" if inst.instrument_type.value == "CE" else "PUT"
            
            # Format expiry as ISO string
            expiry_str = inst.expiry.isoformat() if isinstance(inst.expiry, datetime) else str(inst.expiry)
            
            options.append({
                "symbol": inst.symbol,
                "token": inst.token,
                "tradingsymbol": inst.tradingsymbol,
                "strike": inst.strike or 0.0,
                "side": side,
                "expiry": expiry_str,
                "exchange": inst.exchange,
            })
        
        # Filter by expiry_kind
        if expiry_kind == "nearest" and options:
            # Get nearest expiry
            expiries = [opt["expiry"] for opt in options if opt["expiry"]]
            if expiries:
                # Parse and find nearest
                parsed_expiries = []
                for exp_str in expiries:
                    try:
                        if isinstance(exp_str, str):
                            parsed_expiries.append(datetime.fromisoformat(exp_str.replace('Z', '+00:00')))
                        else:
                            parsed_expiries.append(exp_str)
                    except:
                        continue
                if parsed_expiries:
                    nearest_expiry = min(parsed_expiries)
                    nearest_str = nearest_expiry.isoformat()
                    options = [opt for opt in options if opt["expiry"] == nearest_str or opt["expiry"] == nearest_expiry]
        
        return options

    async def _get_candidates(
        self,
        underlying: str,
        expiry_kind: str = "nearest"
    ) -> List[OptionCandidate]:
        """
        Get option candidates with Greeks and LTP attached.
        
        Batch fetches Greeks & LTP in parallel if engines support async.
        """
        # 1. Get raw option symbols
        raw_opts = self._get_options_from_manager(underlying, expiry_kind)
        if not raw_opts:
            return []
        
        # 2. Batch fetch Greeks & LTP
        tokens = [opt['token'] for opt in raw_opts]
        
        # Get Greeks (sync or async)
        greeks_map = {}
        if self.greeks_engine and hasattr(self.greeks_engine, 'get_greeks_for_tokens'):
            try:
                if hasattr(self.greeks_engine.get_greeks_for_tokens, '__call__'):
                    # Check if it's async
                    import inspect
                    if inspect.iscoroutinefunction(self.greeks_engine.get_greeks_for_tokens):
                        greeks_map = await self.greeks_engine.get_greeks_for_tokens(tokens)
                    else:
                        greeks_map = self.greeks_engine.get_greeks_for_tokens(tokens)
            except Exception as e:
                logger.debug(f"[DeltaOptionSelector] Greeks fetch failed: {e}")
        
        # Get LTP (async if broker supports it)
        ltp_map = {}
        try:
            if self.broker:
                # Try async get_ltp first
                if hasattr(self.broker, 'get_ltp'):
                    import inspect
                    if inspect.iscoroutinefunction(self.broker.get_ltp):
                        # Async method
                        token_strings = [str(t) for t in tokens]
                        ltp_response = await self.broker.get_ltp(token_strings)
                        if isinstance(ltp_response, dict):
                            ltp_map = ltp_response
                    else:
                        # Sync method - try to use it
                        # Build instrument keys for Kite-style LTP
                        instrument_keys = []
                        for opt in raw_opts:
                            exchange = opt.get('exchange', 'NFO')
                            tradingsymbol = opt.get('tradingsymbol', '')
                            if tradingsymbol:
                                instrument_keys.append(f"{exchange}:{tradingsymbol}")
                        
                        if instrument_keys and hasattr(self.broker, 'ltp'):
                            bulk_ltp = self.broker.ltp(instrument_keys)
                            # Convert to token-based map
                            for opt in raw_opts:
                                key = f"{opt.get('exchange', 'NFO')}:{opt.get('tradingsymbol', '')}"
                                if key in bulk_ltp:
                                    price_data = bulk_ltp[key]
                                    if isinstance(price_data, dict):
                                        ltp_map[str(opt['token'])] = {'last_price': price_data.get('last_price', 0.0)}
                                    else:
                                        ltp_map[str(opt['token'])] = {'last_price': float(price_data) if price_data else 0.0}
        except Exception as e:
            logger.debug(f"[DeltaOptionSelector] LTP fetch failed: {e}")
        
        # 3. Build candidates
        candidates = []
        for opt in raw_opts:
            token = opt['token']
            t_str = str(token)
            
            # Get Greeks
            greeks = greeks_map.get(token, {})
            if not greeks and isinstance(greeks_map, dict):
                # Try string key
                greeks = greeks_map.get(t_str, {})
            
            # Get LTP
            ltp_data = ltp_map.get(t_str, {})
            if not ltp_data and isinstance(ltp_map, dict):
                # Try direct token key
                ltp_data = ltp_map.get(token, {})
            
            if isinstance(ltp_data, dict):
                ltp = ltp_data.get('last_price', 0.0)
            else:
                ltp = float(ltp_data) if ltp_data else 0.0
            
            # Fallback: approximate delta if not available
            delta = greeks.get('delta')
            if delta is None:
                # Could add spot-based approximation here if needed
                pass
            
            candidates.append(OptionCandidate(
                symbol=opt['symbol'],
                token=token,
                strike=float(opt['strike']),
                side=opt['side'],  # CALL/PUT
                expiry=opt['expiry'],
                ltp=ltp,
                delta=delta,
                gamma=greeks.get('gamma'),
                vega=greeks.get('vega'),
                theta=greeks.get('theta'),
                iv=greeks.get('iv'),
            ))
        
        return candidates

    def _closest_by_delta(
        self,
        candidates: List[OptionCandidate],
        target: float,
        side: Side
    ) -> Optional[OptionCandidate]:
        """
        Find the option candidate closest to target_delta for the given side.
        
        Put delta is usually negative, we compare absolute diff.
        """
        subset = [c for c in candidates if c.side == side and c.delta is not None]
        if not subset:
            return None
        
        # Put delta is usually negative, we compare absolute diff
        target_abs = abs(target)
        # Sort by distance to target delta
        best = min(subset, key=lambda c: abs(abs(c.delta) - target_abs))
        return best

    async def select_strangle(
        self,
        underlying: str,
        target_delta: float = 0.25,
        expiry_kind: str = "nearest"
    ) -> Optional[Tuple[OptionCandidate, OptionCandidate]]:
        """
        Finds a balanced Strangle: CE ~ delta and PE ~ -delta.
        
        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            target_delta: Target absolute delta for each leg (e.g., 0.25)
            expiry_kind: "nearest", "next", etc.
        
        Returns:
            Tuple of (call_candidate, put_candidate) or None if not found
        """
        try:
            candidates = await self._get_candidates(underlying, expiry_kind)
            if not candidates:
                logger.warning(f"[DeltaOptionSelector] No candidates for {underlying}")
                return None
            
            ce = self._closest_by_delta(candidates, target_delta, "CALL")
            pe = self._closest_by_delta(candidates, target_delta, "PUT")
            
            if ce and pe:
                logger.debug(
                    f"[DeltaOptionSelector] Selected strangle for {underlying}",
                    ce_strike=ce.strike,
                    ce_delta=ce.delta,
                    pe_strike=pe.strike,
                    pe_delta=pe.delta,
                    expiry=ce.expiry
                )
                return ce, pe
            
            logger.warning(
                f"[DeltaOptionSelector] Could not find both legs for {underlying}, "
                f"ce={bool(ce)}, pe={bool(pe)}"
            )
            return None
        except Exception as e:
            logger.error(
                f"[DeltaOptionSelector] Error in select_strangle for {underlying}: {e}",
                exc_info=True
            )
            return None

    async def select_credit_spread(
        self,
        underlying: str,
        direction: Literal["BULL_PUT", "BEAR_CALL"],
        target_delta_short: float = 0.25,
        width_points: float = 100.0,
        expiry_kind: str = "nearest"
    ) -> Optional[Tuple[OptionCandidate, OptionCandidate]]:
        """
        Finds a vertical spread based on delta and width.
        
        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            direction: "BULL_PUT" or "BEAR_CALL"
            target_delta_short: Target delta for short leg (e.g., 0.25)
            width_points: Minimum strike distance between legs (e.g., 100 points)
            expiry_kind: "nearest", "next", etc.
        
        Returns:
            Tuple of (short_leg, long_leg) or None if not found
        """
        try:
            candidates = await self._get_candidates(underlying, expiry_kind)
            if not candidates:
                logger.warning(f"[DeltaOptionSelector] No candidates for {underlying}")
                return None
            
            if direction == "BULL_PUT":
                short = self._closest_by_delta(candidates, target_delta_short, "PUT")
                if not short:
                    return None
                
                # Long Leg: Further OTM (Lower Strike for Puts)
                longs = [
                    c for c in candidates
                    if c.side == "PUT" and c.expiry == short.expiry and c.strike <= (short.strike - width_points)
                ]
                if not longs:
                    logger.warning(
                        f"[DeltaOptionSelector] No long PUT leg found for BULL_PUT spread "
                        f"(short strike: {short.strike}, width: {width_points})"
                    )
                    return None
                long = max(longs, key=lambda c: c.strike)  # Closest valid strike
            
            elif direction == "BEAR_CALL":
                short = self._closest_by_delta(candidates, target_delta_short, "CALL")
                if not short:
                    return None
                
                # Long Leg: Further OTM (Higher Strike for Calls)
                longs = [
                    c for c in candidates
                    if c.side == "CALL" and c.expiry == short.expiry and c.strike >= (short.strike + width_points)
                ]
                if not longs:
                    logger.warning(
                        f"[DeltaOptionSelector] No long CALL leg found for BEAR_CALL spread "
                        f"(short strike: {short.strike}, width: {width_points})"
                    )
                    return None
                long = min(longs, key=lambda c: c.strike)  # Closest valid strike
            
            else:
                logger.error(f"[DeltaOptionSelector] Unknown direction: {direction}")
                return None
            
            logger.debug(
                f"[DeltaOptionSelector] Selected {direction} spread for {underlying}",
                short_strike=short.strike,
                short_delta=short.delta,
                long_strike=long.strike,
                long_delta=long.delta,
                width=abs(long.strike - short.strike),
                expiry=short.expiry
            )
            
            return short, long
        except Exception as e:
            logger.error(
                f"[DeltaOptionSelector] Error in select_credit_spread for {underlying}: {e}",
                exc_info=True
            )
            return None

