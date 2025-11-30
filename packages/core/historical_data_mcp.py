"""
Historical Data Provider using Kite MCP
========================================

Fetches real historical data from Kite Connect via MCP for:
1. Backtesting strategies
2. Paper trading simulation (replay mode)
3. Live trading context enrichment

Usage:
    provider = HistoricalDataMCPProvider(mcp_client=mcp)
    candles = provider.fetch_candles(
        instrument_token=256265,
        from_date="2025-11-20 09:15:00",
        to_date="2025-11-20 15:30:00",
        interval="5minute"
    )
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import structlog

from packages.core.models import Bar, Instrument

logger = structlog.get_logger(__name__)


class HistoricalDataMCPProvider:
    """
    Fetches historical OHLC data from Kite Connect via MCP.

    Features:
    - Real market data (not synthetic)
    - Multiple timeframes (1min to daily)
    - Option OI data included
    - Date range queries
    - Instrument search integration
    """

    def __init__(self, kite_mcp_adapter=None):
        """
        Initialize the historical data provider.

        Args:
            kite_mcp_adapter: KiteMCPAdapter instance for making MCP calls
        """
        self.adapter = kite_mcp_adapter
        self._instrument_cache: Dict[str, int] = {}

        logger.info("📊 HistoricalDataMCPProvider initialized")

    def search_instrument(self, query: str) -> List[Dict]:
        """
        Search for instruments to get their tokens.

        Args:
            query: Search query (e.g., "NIFTY", "NSE:INFY")

        Returns:
            List of matching instruments with tokens

        Example:
            instruments = provider.search_instrument("NIFTY")
            # [{'instrument_token': 256265, 'tradingsymbol': 'NIFTY 50', ...}]
        """
        if not self.adapter or not self.adapter.mcp:
            raise RuntimeError("MCP client not available")

        try:
            result = self.adapter.mcp.call_tool("search_instruments", {
                "query": query,
                "filter_on": "tradingsymbol"
            })

            if isinstance(result, str):
                result = json.loads(result)

            logger.debug(f"Found {len(result)} instruments for query: {query}")
            return result

        except Exception as e:
            logger.error(f"Instrument search failed: {e}", query=query)
            return []

    def get_instrument_token(self, exchange: str, symbol: str) -> Optional[int]:
        """
        Get instrument token for exchange:symbol.

        Args:
            exchange: Exchange code (NSE, NFO, BSE, BFO)
            symbol: Trading symbol

        Returns:
            Instrument token or None if not found

        Example:
            token = provider.get_instrument_token("NSE", "INFY")
        """
        cache_key = f"{exchange}:{symbol}"

        if cache_key in self._instrument_cache:
            return self._instrument_cache[cache_key]

        # Search for instrument
        instruments = self.search_instrument(cache_key)

        if instruments:
            token = instruments[0].get("instrument_token")
            self._instrument_cache[cache_key] = token
            return token

        logger.warning(f"Instrument not found: {cache_key}")
        return None

    def fetch_candles(
        self,
        instrument_token: int,
        from_date: str,
        to_date: str,
        interval: str = "5minute",
        continuous: bool = False,
        oi: bool = True
    ) -> List[Dict]:
        """
        Fetch historical OHLC candles from Kite Connect.

        Args:
            instrument_token: Instrument token (from search_instrument)
            from_date: Start date in "YYYY-MM-DD HH:MM:SS" format
            to_date: End date in "YYYY-MM-DD HH:MM:SS" format
            interval: Candle interval (minute, 3minute, 5minute, 15minute, 30minute, 60minute, day)
            continuous: Use continuous data for F&O (default: False)
            oi: Include Open Interest data (default: True)

        Returns:
            List of candle dictionaries with OHLC + OI data

        Example:
            candles = provider.fetch_candles(
                instrument_token=256265,
                from_date="2025-11-26 09:15:00",
                to_date="2025-11-26 15:30:00",
                interval="5minute"
            )
        """
        if not self.adapter or not self.adapter.mcp:
            raise RuntimeError("MCP client not available")

        try:
            logger.info(
                "Fetching historical data",
                token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )

            result = self.adapter.mcp.call_tool("get_historical_data", {
                "instrument_token": instrument_token,
                "from_date": from_date,
                "to_date": to_date,
                "interval": interval,
                "continuous": continuous,
                "oi": oi
            })

            if isinstance(result, str):
                result = json.loads(result)

            candles = result.get("data", {}).get("candles", [])

            logger.info(f"Fetched {len(candles)} candles", interval=interval)
            return candles

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return []

    def fetch_bars(
        self,
        instrument: Instrument,
        from_date: datetime,
        to_date: datetime,
        interval: str = "5minute"
    ) -> List[Bar]:
        """
        Fetch historical data as Bar objects (for backtesting).

        Args:
            instrument: Instrument object
            from_date: Start datetime
            to_date: End datetime
            interval: Candle interval

        Returns:
            List of Bar objects ready for strategy consumption

        Example:
            bars = provider.fetch_bars(
                instrument=nifty_instrument,
                from_date=datetime(2025, 11, 26, 9, 15),
                to_date=datetime(2025, 11, 26, 15, 30),
                interval="5minute"
            )
        """
        # Format dates for Kite API
        from_str = from_date.strftime("%Y-%m-%d %H:%M:%S")
        to_str = to_date.strftime("%Y-%m-%d %H:%M:%S")

        # Fetch candles
        candles = self.fetch_candles(
            instrument_token=instrument.token,
            from_date=from_str,
            to_date=to_str,
            interval=interval,
            oi=True
        )

        # Convert to Bar objects
        bars = []
        for candle in candles:
            try:
                # Candle format: [timestamp, open, high, low, close, volume, oi]
                timestamp = datetime.fromisoformat(candle[0].replace('Z', '+00:00'))

                bar = Bar(
                    instrument=instrument,
                    timestamp=timestamp,
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=int(candle[5]) if len(candle) > 5 else 0,
                    oi=int(candle[6]) if len(candle) > 6 else 0
                )
                bars.append(bar)

            except Exception as e:
                logger.warning(f"Failed to parse candle: {e}", candle=candle)
                continue

        logger.info(f"Converted {len(bars)} candles to Bar objects")
        return bars

    def fetch_multiple_instruments(
        self,
        instruments: List[Instrument],
        from_date: datetime,
        to_date: datetime,
        interval: str = "5minute"
    ) -> Dict[int, List[Bar]]:
        """
        Fetch historical data for multiple instruments.

        Args:
            instruments: List of Instrument objects
            from_date: Start datetime
            to_date: End datetime
            interval: Candle interval

        Returns:
            Dictionary mapping instrument token to list of Bars

        Example:
            data = provider.fetch_multiple_instruments(
                instruments=[nifty_ce, nifty_pe],
                from_date=datetime(2025, 11, 26, 9, 15),
                to_date=datetime(2025, 11, 26, 15, 30),
                interval="5minute"
            )
            # {256265: [Bar, Bar, ...], 256266: [Bar, Bar, ...]}
        """
        result = {}

        for instrument in instruments:
            try:
                bars = self.fetch_bars(
                    instrument=instrument,
                    from_date=from_date,
                    to_date=to_date,
                    interval=interval
                )
                result[instrument.token] = bars

            except Exception as e:
                logger.error(
                    f"Failed to fetch data for instrument",
                    instrument=instrument.tradingsymbol,
                    error=str(e)
                )
                result[instrument.token] = []

        return result

    def fetch_date_range(
        self,
        instrument_token: int,
        days: int = 7,
        interval: str = "5minute",
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Fetch historical data for the last N days.

        Args:
            instrument_token: Instrument token
            days: Number of days to fetch (default: 7, max: 60 for minute data)
            interval: Candle interval
            end_date: End date (default: now)

        Returns:
            List of candle dictionaries

        Example:
            # Get last 7 days of 5-minute data
            candles = provider.fetch_date_range(
                instrument_token=256265,
                days=7,
                interval="5minute"
            )
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=days)

        return self.fetch_candles(
            instrument_token=instrument_token,
            from_date=start_date.strftime("%Y-%m-%d %H:%M:%S"),
            to_date=end_date.strftime("%Y-%m-%d %H:%M:%S"),
            interval=interval
        )

    def get_latest_quote(self, instruments: List[str]) -> Dict:
        """
        Get real-time quotes (for live trading context).

        Args:
            instruments: List of exchange:symbol strings

        Returns:
            Quote data dictionary

        Example:
            quotes = provider.get_latest_quote(["NSE:INFY", "NSE:SBIN"])
        """
        if not self.adapter or not self.adapter.mcp:
            raise RuntimeError("MCP client not available")

        try:
            result = self.adapter.mcp.call_tool("get_quotes", {
                "instruments": instruments
            })

            if isinstance(result, str):
                result = json.loads(result)

            return result

        except Exception as e:
            logger.error(f"Failed to fetch quotes: {e}")
            return {}


# Example Usage Functions

def example_backtest_with_mcp():
    """
    Example: Run a backtest using real Kite historical data via MCP.
    """
    from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
    from packages.core.hivemind.mcp_client import MCPClient

    # Initialize MCP client
    mcp_client = MCPClient(server_url="http://localhost:8080")
    adapter = KiteMCPAdapter(mcp_client=mcp_client)

    # Initialize historical data provider
    provider = HistoricalDataMCPProvider(kite_mcp_adapter=adapter)

    # Search for NIFTY
    instruments = provider.search_instrument("NIFTY 50")
    nifty_token = instruments[0]["instrument_token"]

    # Fetch last 7 days of data
    candles = provider.fetch_date_range(
        instrument_token=nifty_token,
        days=7,
        interval="5minute"
    )

    logger.info(f"Backtest data ready: {len(candles)} candles")

    # Now feed this data to BacktestEngine or strategies
    # ... your backtest logic here ...


def example_paper_trading_replay():
    """
    Example: Replay today's market data for paper trading simulation.
    """
    from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
    from packages.core.hivemind.mcp_client import MCPClient

    # Initialize
    mcp_client = MCPClient(server_url="http://localhost:8080")
    adapter = KiteMCPAdapter(mcp_client=mcp_client)
    provider = HistoricalDataMCPProvider(kite_mcp_adapter=adapter)

    # Get today's data for NIFTY options
    today = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    end_time = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)

    # Fetch NIFTY CE/PE data
    instruments = provider.search_instrument("NIFTY")

    for instrument in instruments[:10]:  # First 10 instruments
        bars = provider.fetch_candles(
            instrument_token=instrument["instrument_token"],
            from_date=today.strftime("%Y-%m-%d %H:%M:%S"),
            to_date=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            interval="1minute"
        )

        # Feed bars to paper trading simulator one by one (replay mode)
        for bar in bars:
            # Simulate tick-by-tick replay
            # ... your paper trading logic here ...
            pass


if __name__ == "__main__":
    # Example: Quick test
    logger.info("HistoricalDataMCPProvider module loaded")
