"""Instrument synchronization and universe management"""
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import structlog
from kiteconnect import KiteConnect

from packages.core.config import Settings, UniverseConfig
from packages.core.models import Instrument, InstrumentType
from packages.core.utils.retry import retry_api_call

logger = structlog.get_logger(__name__)


class InstrumentManager:
    """Manages instrument data and universe"""
    
    def __init__(self, kite: KiteConnect, config: UniverseConfig, settings: Settings):
        self.kite = kite
        self.config = config
        self.settings = settings
        self.cache_enabled = os.getenv("INSTRUMENT_CACHE_ENABLED", "1") == "1"
        self.cache_dir = Path(os.getenv("INSTRUMENT_CACHE_DIR", "data/instruments"))
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self._instruments: Dict[int, Instrument] = {}
        self._symbols_to_tokens: Dict[str, int] = {}
        self._universe_tokens: Set[int] = set()
        self._fo_ban_list: Set[str] = set()
        
        # Metadata
        self.last_sync: Optional[datetime] = None

    def _cache_path(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.cache_dir / f"instruments_{today}.csv"

    def _load_cached_dataframe(self) -> Optional[pd.DataFrame]:
        """Load cached instruments CSV if enabled and present."""
        if not self.cache_enabled:
            return None
        path = self._cache_path()
        if not path.exists():
            return None
        usecols = [
            "instrument_token",
            "tradingsymbol",
            "name",
            "expiry",
            "strike",
            "tick_size",
            "lot_size",
            "exchange",
            "instrument_type",
            "segment",
            "isin",
            "freeze_quantity",
        ]
        dtype = {
            "instrument_token": "int64",
            "tradingsymbol": "string",
            "name": "string",
            "strike": "float64",
            "tick_size": "float64",
            "lot_size": "int64",
            "exchange": "string",
            "instrument_type": "string",
            "segment": "string",
            "isin": "string",
            "freeze_quantity": "float64",
        }
        try:
            df = pd.read_csv(
                path,
                usecols=usecols,
                dtype=dtype,
                parse_dates=["expiry"],
                low_memory=False,
            )
            logger.info("Loaded instruments from cache", path=str(path))
            return df
        except Exception as e:
            logger.warning(f"Failed to load instrument cache {path}: {e}")
            return None

    def _build_dataframe(self, instruments: List[Dict]) -> pd.DataFrame:
        """Create a memory-efficient DataFrame from instrument dicts."""
        if not instruments:
            return pd.DataFrame()
        df = pd.DataFrame(instruments)
        desired_cols = [
            "instrument_token",
            "tradingsymbol",
            "name",
            "expiry",
            "strike",
            "tick_size",
            "lot_size",
            "exchange",
            "instrument_type",
            "segment",
            "isin",
            "freeze_quantity",
        ]
        for col in desired_cols:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[desired_cols]
        df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
        return df

    def _write_cache(self, df: pd.DataFrame) -> None:
        """Persist dataframe to daily cache and prune stale files."""
        if not self.cache_enabled or df.empty:
            return
        path = self._cache_path()
        try:
            df.to_csv(path, index=False)
            logger.info("Instrument cache written", path=str(path))
            # Cleanup old caches
            for f in self.cache_dir.glob("instruments_*.csv"):
                if f != path:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Could not write instrument cache: {e}")
        
    @retry_api_call(retries=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def _fetch_instruments_with_retry(self, exchange: str) -> List[Dict]:
        """
        Fetch instruments from an exchange with retry logic.
        
        Critical for strategy initialization - if this fails, strategies can't find options.
        This is the "oxygen" of delta-based strategies.
        """
        return self.kite.instruments(exchange)
    
    @retry_api_call(retries=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def _fetch_quote_with_retry(self, instrument_key: str) -> Dict:
        """
        Fetch quote from Kite API with retry on network errors.
        
        Critical for spot price detection and strike capping.
        If this fails at 09:19:59, strategy is blind at critical entry moment.
        """
        return self.kite.quote(instrument_key)
    
    async def sync_instruments(self) -> bool:
        """
        Synchronize instrument data from Kite Connect.
        Fetches all instruments and caches them locally.
        """
        try:
            logger.info("Starting instrument synchronization")
            
            df = self._load_cached_dataframe()
            if df is None:
                # Fetch instruments from all relevant exchanges
                exchanges = ["NSE", "NFO", "BSE", "BFO", "MCX"]
                all_instruments = []
                
                for exchange in exchanges:
                    try:
                        instruments = self._fetch_instruments_with_retry(exchange)
                        if instruments:
                            all_instruments.extend(instruments)
                            logger.info(f"Fetched {len(instruments)} instruments from {exchange}")
                    except Exception as e:
                        logger.error(f"Failed to fetch instruments from {exchange} after retries: {e}")
                
                if not all_instruments:
                    logger.error("Instrument sync failed: no instruments fetched from any exchange")
                    return False
                
                df = self._build_dataframe(all_instruments)
                self._write_cache(df)
            
            # Parse and cache instruments
            self._parse_instruments(df.to_dict(orient="records"))
            
            self.last_sync = datetime.now()
            logger.info(f"Instrument sync complete. Total instruments: {len(self._instruments)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Instrument sync failed: {e}")
            return False
    
    def _parse_instruments(self, raw_instruments: List[Dict]) -> None:
        """Parse raw instrument data into Instrument objects"""
        self._instruments.clear()
        self._symbols_to_tokens.clear()
        
        for raw in raw_instruments:
            try:
                # Determine instrument type
                inst_type = self._map_instrument_type(raw.get("instrument_type", "EQ"))
                
                # Parse expiry
                expiry = None
                if raw.get("expiry"):
                    expiry = pd.to_datetime(raw["expiry"])
                
                # Create Instrument
                instrument = Instrument(
                    token=raw["instrument_token"],
                    symbol=raw["name"],
                    tradingsymbol=raw["tradingsymbol"],
                    exchange=raw["exchange"],
                    instrument_type=inst_type,
                    expiry=expiry,
                    strike=raw.get("strike"),
                    lot_size=raw.get("lot_size", 1),
                    tick_size=raw.get("tick_size", 0.05),
                    freeze_quantity=raw.get("freeze_quantity"),
                    segment=raw.get("segment"),
                    isin=raw.get("isin")
                )
                
                self._instruments[instrument.token] = instrument
                self._symbols_to_tokens[instrument.tradingsymbol] = instrument.token
                
            except Exception as e:
                logger.warning(f"Failed to parse instrument: {raw.get('tradingsymbol', 'unknown')} - {e}")
    
    def _map_instrument_type(self, raw_type: str) -> InstrumentType:
        """Map raw instrument type to InstrumentType enum"""
        mapping = {
            "EQ": InstrumentType.EQ,
            "FUT": InstrumentType.FUT,
            "CE": InstrumentType.CE,
            "PE": InstrumentType.PE,
        }
        return mapping.get(raw_type, InstrumentType.EQ)
    
    async def sync_fo_ban_list(self) -> None:
        """
        Synchronize F&O ban list from NSE.
        This list contains stocks currently under F&O ban due to high positions.
        """
        try:
            # In production, fetch from NSE website or Kite's margin API
            # For now, we'll maintain an empty list and update it manually
            # NSE publishes this daily at: https://www.nseindia.com/api/fo-ban-securities
            
            logger.info("Syncing F&O ban list")
            
            # Placeholder: In production, implement actual fetching logic
            # Example banned stocks (for demo purposes):
            # self._fo_ban_list = {"DELTACORP", "GNFC", "MANAPPURAM"}
            
            self._fo_ban_list.clear()
            logger.info(f"F&O ban list synced. {len(self._fo_ban_list)} symbols banned")
            
        except Exception as e:
            logger.error(f"Failed to sync F&O ban list: {e}")
    
    def is_fo_banned(self, symbol: str) -> bool:
        """Check if a symbol is currently under F&O ban"""
        return symbol in self._fo_ban_list
    
    async def build_universe(self) -> List[int]:
        """
        Build trading universe based on configuration.
        Returns list of instrument tokens to subscribe to.
        """
        try:
            logger.info("Building trading universe")
            
            universe_tokens = set()
            
            # 1. Add index instruments (futures + options)
            for index_name in self.config.indices:
                tokens = self._get_index_instruments(index_name)
                universe_tokens.update(tokens)
                # Detailed logging is done inside _get_index_instruments()
            
            # 2. Add liquid F&O stocks
            if self.config.fo_stocks_liquidity_rank_top_n > 0:
                fo_tokens = await self._get_liquid_fo_stocks(
                    self.config.fo_stocks_liquidity_rank_top_n
                )
                universe_tokens.update(fo_tokens)
                logger.info(f"Added {len(fo_tokens)} liquid F&O stocks")

            # 3. Add MCX contracts (phase 1)
            if self.config.mcx_symbols:
                mcx_tokens = await self._get_mcx_contracts()
                universe_tokens.update(mcx_tokens)
                logger.info(f"Added {len(mcx_tokens)} MCX contracts", symbols=self.config.mcx_symbols)
            
            self._universe_tokens = universe_tokens
            
            # Summary log (detailed per-index logging done in _get_index_instruments)
            indices_str = ", ".join(self.config.indices)
            mcx_str = ", ".join(self.config.mcx_symbols) if self.config.mcx_symbols else "none"
            logger.info(
                f"Universe built: {len(universe_tokens)} tokens for {indices_str} (fut+opts) + MCX: {mcx_str}"
            )
            
            return list(universe_tokens)
            
        except Exception as e:
            logger.error(f"Failed to build universe: {e}")
            return []
    
    def _get_index_instruments(self, index_name: str) -> Set[int]:
        """Get instruments for a specific index"""
        tokens = set()
        fut_count = 0
        opt_count = 0
        
        # Map index names to tradingsymbols (supports both short names and full trading symbols)
        index_map = {
            "NIFTY": "NIFTY",
            "NIFTY 50": "NIFTY",  # Support full trading symbol
            "BANKNIFTY": "BANKNIFTY",
            "NIFTY BANK": "BANKNIFTY",  # Support full trading symbol
            "FINNIFTY": "FINNIFTY",
            "NIFTY FIN SERVICE": "FINNIFTY"  # Support full trading symbol
        }
        
        base_symbol = index_map.get(index_name)
        if not base_symbol:
            logger.warning(f"Unknown index: {index_name}")
            return tokens
        
        # Get current time (used for expiry filtering)
        now = datetime.now()
        
        # Get spot index token and try to get current spot price
        spot_token = None
        spot_price = None

        # Map NFO symbols to NSE spot symbols for instrument lookup
        spot_symbol_map = {
            "NIFTY": "NIFTY 50",
            "BANKNIFTY": "NIFTY BANK",
            "FINNIFTY": "NIFTY FIN SERVICE"
        }
        nse_spot_symbol = spot_symbol_map.get(base_symbol, base_symbol)
        
        # If index_name is already a full trading symbol, use it directly
        if index_name in ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE"]:
            nse_spot_symbol = index_name

        for token, inst in self._instruments.items():
            if inst.tradingsymbol == nse_spot_symbol and inst.exchange == "NSE" and inst.instrument_type == InstrumentType.EQ:
                tokens.add(token)
                spot_token = token
                break
        
        # Try to get spot price from Kite API (for strike capping)
        # This is best-effort; if it fails, we use defaults
        if spot_token and self.kite:
            try:
                # Try spot index first (with retry)
                quote = self._fetch_quote_with_retry(f"NSE:{nse_spot_symbol}")
                if quote and f'NSE:{nse_spot_symbol}' in quote and quote[f'NSE:{nse_spot_symbol}'].get('last_price'):
                    spot_price = quote[f'NSE:{nse_spot_symbol}']['last_price']
                    logger.info(f"Got spot price for {base_symbol} from NSE: {spot_price}")
            except Exception as e:
                logger.warning(f"Could not get spot price from NSE for {base_symbol}: {e}")
                # If quote fails, try nearest future as proxy
                try:
                    for token, inst in self._instruments.items():
                        if (inst.symbol == base_symbol and inst.exchange == "NFO" and 
                            inst.is_future and inst.expiry and 
                            inst.expiry >= now):
                            fut_quote = self._fetch_quote_with_retry(f"NFO:{inst.tradingsymbol}")
                            if fut_quote and 'NFO' in fut_quote and fut_quote['NFO'].get('last_price'):
                                spot_price = fut_quote['NFO']['last_price']
                                logger.debug(f"Got spot price for {base_symbol} from future: {spot_price}")
                                break
                except Exception as e2:
                    logger.debug(f"Could not get spot price from futures for {base_symbol}: {e2}")
        
        # If still no spot price, use a reasonable default based on index
        if not spot_price:
            default_spots = {"NIFTY": 20000, "BANKNIFTY": 45000, "FINNIFTY": 20000}
            spot_price = default_spots.get(base_symbol, 20000)
            logger.debug(f"Using default spot price for {base_symbol}: {spot_price}")
        
        # Strike range: ±12% of spot (covers ±10-15% requirement)
        strike_range_pct = 0.12
        min_strike = spot_price * (1 - strike_range_pct)
        max_strike = spot_price * (1 + strike_range_pct)
        
        for token, inst in self._instruments.items():
            if inst.symbol == base_symbol and inst.exchange == "NFO":
                if inst.is_future and inst.expiry:
                    # Include futures expiring within next 60 days
                    if inst.expiry <= now + timedelta(days=60):
                        tokens.add(token)
                        fut_count += 1
                elif inst.is_option and inst.expiry:
                    # Include options expiring within next 30 days (for OptionsRanker)
                    # Only include strikes within ±12% of spot to limit universe size
                    if inst.expiry <= now + timedelta(days=30):
                        if inst.strike and min_strike <= inst.strike <= max_strike:
                            tokens.add(token)
                            opt_count += 1
        
        logger.info(
            f"Universe built: {len(tokens)} tokens for {index_name} "
            f"(spot={spot_price:.0f}, fut={fut_count}, opts={opt_count}, "
            f"strikes={min_strike:.0f}-{max_strike:.0f})"
        )
        
        return tokens

    async def _get_mcx_contracts(self) -> Set[int]:
        """
        Select MCX futures (and optional options) for configured symbols.
        
        - Picks nearest-dated future per symbol within max DTE.
        - Optionally adds ATM +/- N strikes within a % band of the reference price.
        """
        tokens: Set[int] = set()
        if not self.config.mcx_symbols:
            return tokens

        now = datetime.now()
        max_dte = timedelta(days=max(1, int(self.config.mcx_max_dte_days)))
        include_opts = bool(self.config.mcx_include_options)
        strike_range_pct = float(self.config.mcx_strike_range_pct)
        strikes_from_atm = int(self.config.mcx_strikes_from_atm)

        for symbol in self.config.mcx_symbols:
            # Collect all MCX instruments for this symbol
            mcx_contracts = [
                inst for inst in self._instruments.values()
                if inst.exchange == "MCX" and inst.symbol == symbol
            ]
            if not mcx_contracts:
                logger.warning("MCX symbol not found in instruments", symbol=symbol)
                continue

            # Nearest future within max DTE
            futures = [
                inst for inst in mcx_contracts
                if inst.is_future and inst.expiry and inst.expiry >= now and inst.expiry <= now + max_dte
            ]
            nearest_future = sorted(futures, key=lambda x: x.expiry)[0] if futures else None
            ref_price = None

            if nearest_future:
                tokens.add(nearest_future.token)
                # Try to fetch a reference price from the future; fall back to strike mid later
                if self.kite:
                    try:
                        quote = self._fetch_quote_with_retry(f"MCX:{nearest_future.tradingsymbol}")
                        if quote and f"MCX:{nearest_future.tradingsymbol}" in quote:
                            q = quote[f"MCX:{nearest_future.tradingsymbol}"]
                            ref_price = q.get("last_price") or q.get("ohlc", {}).get("close")
                    except Exception as e:
                        logger.debug("MCX future quote failed", symbol=symbol, error=str(e))

            if not include_opts:
                continue

            options = [
                inst for inst in mcx_contracts
                if inst.is_option and inst.expiry and inst.expiry >= now and inst.expiry <= now + max_dte
            ]
            if not options:
                continue

            # If no ref price yet, derive from mid strikes
            if ref_price is None:
                strikes = sorted([opt.strike for opt in options if opt.strike])
                if strikes:
                    ref_price = strikes[len(strikes) // 2]

            if not ref_price:
                logger.debug("Skipping MCX options: no ref price", symbol=symbol)
                continue

            min_strike = ref_price * (1 - strike_range_pct)
            max_strike = ref_price * (1 + strike_range_pct)

            # Filter options within band and nearest strikes_from_atm on each side
            filtered_opts = [
                opt for opt in options
                if opt.strike and min_strike <= opt.strike <= max_strike
            ]
            # Keep closest strikes around ref_price
            filtered_opts.sort(key=lambda o: abs(o.strike - ref_price))
            limited_opts = filtered_opts[: max(1, strikes_from_atm * 2 + 1)]

            for opt in limited_opts:
                tokens.add(opt.token)

            logger.info(
                "Selected MCX contracts",
                symbol=symbol,
                fut=nearest_future.tradingsymbol if nearest_future else None,
                options=len(limited_opts),
                ref_price=ref_price
            )

        return tokens
    
    async def _get_liquid_fo_stocks(self, top_n: int) -> Set[int]:
        """
        Get most liquid F&O stocks.
        Filters by turnover, excludes banned stocks.
        """
        tokens = set()
        
        try:
            # Get all unique F&O stock symbols
            fo_stocks = set()
            for token, inst in self._instruments.items():
                if inst.exchange == "NFO" and inst.symbol not in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                    fo_stocks.add(inst.symbol)
            
            # Exclude F&O banned stocks
            if self.config.exclude_fo_ban:
                fo_stocks = {s for s in fo_stocks if not self.is_fo_banned(s)}
            
            # In production, fetch turnover data and rank
            # For now, select first top_n stocks alphabetically (placeholder)
            selected_stocks = sorted(list(fo_stocks))[:top_n]
            
            # Get current month futures for selected stocks
            now = datetime.now()
            for symbol in selected_stocks:
                for token, inst in self._instruments.items():
                    if inst.symbol == symbol and inst.exchange == "NFO" and inst.is_future:
                        if inst.expiry and inst.expiry <= now + timedelta(days=30):
                            tokens.add(token)
                            break
            
            logger.info(f"Selected {len(selected_stocks)} liquid F&O stocks")
            
        except Exception as e:
            logger.error(f"Failed to get liquid F&O stocks: {e}")
        
        return tokens
    
    def get_instrument(self, token: int) -> Optional[Instrument]:
        """Get instrument by token"""
        return self._instruments.get(token)
    
    def get_instrument_by_symbol(self, tradingsymbol: str) -> Optional[Instrument]:
        """Get instrument by trading symbol"""
        token = self._symbols_to_tokens.get(tradingsymbol)
        if token:
            return self._instruments.get(token)
        return None
    
    def get_universe_tokens(self) -> List[int]:
        """Get current universe tokens"""
        return list(self._universe_tokens)
    
    def get_options_chain(
        self,
        symbol: str,
        expiry: Optional[datetime] = None,
        strikes_from_atm: int = 5
    ) -> List[Instrument]:
        """
        Get options chain for a symbol.
        
        Args:
            symbol: Underlying symbol (e.g., "NIFTY", "BANKNIFTY")
            expiry: Specific expiry date (None for nearest)
            strikes_from_atm: Number of strikes above and below ATM to include
        
        Returns:
            List of option instruments
        """
        options = []
        
        # Find all options for this symbol
        symbol_options = [
            inst for inst in self._instruments.values()
            if inst.symbol == symbol and inst.is_option and inst.exchange == "NFO"
        ]
        
        if not symbol_options:
            return options
        
        # Filter by expiry
        if expiry is None:
            # Get nearest expiry
            expiries = sorted([opt.expiry for opt in symbol_options if opt.expiry])
            if expiries:
                expiry = expiries[0]
        
        if expiry:
            symbol_options = [opt for opt in symbol_options if opt.expiry == expiry]
        
        # Get ATM strike (would need current spot price in production)
        # For now, get middle strikes
        strikes = sorted(set([opt.strike for opt in symbol_options if opt.strike]))
        if len(strikes) > 2 * strikes_from_atm:
            mid_idx = len(strikes) // 2
            selected_strikes = strikes[mid_idx - strikes_from_atm: mid_idx + strikes_from_atm + 1]
        else:
            selected_strikes = strikes
        
        # Filter by strikes
        options = [
            opt for opt in symbol_options
            if opt.strike in selected_strikes
        ]
        
        return options
    
    def get_nearest_expiry(self, symbol: str) -> Optional[datetime]:
        """Get nearest expiry date for a symbol"""
        expiries = []
        
        for inst in self._instruments.values():
            if inst.symbol == symbol and inst.expiry and inst.exchange == "NFO":
                expiries.append(inst.expiry)
        
        if expiries:
            return min(expiries)
        
        return None
    
    def filter_options_by_liquidity(
        self,
        options: List[Instrument],
        min_oi: int = 20000,
        max_spread_pct: float = 0.5
    ) -> List[Instrument]:
        """
        Filter options by liquidity criteria.
        
        Note: OI and spread require live market data.
        This is a placeholder that returns all options.
        In production, fetch market data and filter accordingly.
        """
        # In production:
        # 1. Fetch quotes for all option tokens
        # 2. Filter by OI >= min_oi
        # 3. Filter by bid-ask spread <= max_spread_pct of mid
        
        return options
