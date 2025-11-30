"""Historical data loader for NSE options CSV files"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import structlog

from packages.core.models import Bar, Instrument, InstrumentType, Tick

logger = structlog.get_logger(__name__)


class HistoricalDataLoader:
    """
    Loads historical options data from NSE CSV files.
    
    Expected CSV format:
    Symbol, Date, Expiry, Option type, Strike Price, Open, High, Low, Close,
    LTP, Settle Price, No. of contracts, Turnover, Premium Turnover,
    Open Int, Change in OI, Underlying Value
    """
    
    def __init__(self, data_dir: str = "docs/NSE OPINONS DATA"):
        self.data_dir = Path(data_dir)
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def load_file(
        self,
        symbol: str,
        option_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load historical data from CSV file.
        
        Args:
            symbol: NIFTY or BANKNIFTY
            option_type: CE or PE
            start_date: Filter start date (optional)
            end_date: Filter end date (optional)
        
        Returns:
            DataFrame with historical data
        """
        # Construct filename
        filename = f"OPTIDX_{symbol}_{option_type}_12-Aug-2025_TO_12-Nov-2025.csv"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Historical data file not found: {filepath}")
        
        # Check cache
        cache_key = f"{symbol}_{option_type}"
        if cache_key in self._cache:
            df = self._cache[cache_key].copy()
        else:
            # Load CSV
            logger.info(f"Loading historical data from {filename}")
            
            # Read CSV first, then clean column names, then parse dates
            df = pd.read_csv(
                filepath,
                skipinitialspace=True
            )
            
            # Clean column names (remove extra spaces and commas)
            df.columns = df.columns.str.strip().str.replace(',', '')
            
            # Parse date columns after cleaning
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y', errors='coerce')
            if 'Expiry' in df.columns:
                df['Expiry'] = pd.to_datetime(df['Expiry'], format='%d-%b-%Y', errors='coerce')
            
            # Convert numeric columns
            numeric_cols = [
                'Strike Price', 'Open', 'High', 'Low', 'Close', 'LTP',
                'Settle Price', 'No. of contracts', 'Turnover * in  ₹ Lakhs',
                'Premium Turnover ** in   ₹ Lakhs', 'Open Int',
                'Change in OI', 'Underlying Value'
            ]
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Cache
            self._cache[cache_key] = df
        
        # Filter by date range
        if start_date:
            df = df[df['Date'] >= start_date]
        if end_date:
            df = df[df['Date'] <= end_date]
        
        # Sort by date
        df = df.sort_values('Date')
        
        logger.info(
            f"Loaded {len(df)} records for {symbol} {option_type}",
            date_range=(df['Date'].min(), df['Date'].max()) if len(df) > 0 else None
        )
        
        return df
    
    def get_options_chain(
        self,
        symbol: str,
        date: datetime,
        expiry: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get options chain for a specific date.
        
        Args:
            symbol: NIFTY or BANKNIFTY
            date: Trading date
            expiry: Specific expiry (None for all)
        
        Returns:
            DataFrame with CE and PE options for the date
        """
        # Load both CE and PE
        ce_df = self.load_file(symbol, "CE")
        pe_df = self.load_file(symbol, "PE")
        
        # Filter by date
        ce_df = ce_df[ce_df['Date'] == date]
        pe_df = pe_df[pe_df['Date'] == date]
        
        # Filter by expiry if specified
        if expiry:
            ce_df = ce_df[ce_df['Expiry'] == expiry]
            pe_df = pe_df[pe_df['Expiry'] == expiry]
        
        # Combine
        ce_df['Option type'] = 'CE'
        pe_df['Option type'] = 'PE'
        
        chain = pd.concat([ce_df, pe_df], ignore_index=True)
        chain = chain.sort_values(['Strike Price', 'Option type'])
        
        return chain
    
    def get_strike_data(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get historical data for a specific strike.
        
        Args:
            symbol: NIFTY or BANKNIFTY
            option_type: CE or PE
            strike: Strike price
            start_date: Filter start date
            end_date: Filter end date
        
        Returns:
            DataFrame with time series for the strike
        """
        df = self.load_file(symbol, option_type, start_date, end_date)
        
        # Filter by strike
        df = df[df['Strike Price'] == strike]
        
        return df.sort_values('Date')
    
    def convert_to_bars(
        self,
        df: pd.DataFrame,
        symbol: str,
        strike: float,
        option_type: str
    ) -> List[Bar]:
        """
        Convert historical DataFrame to Bar objects.
        
        Args:
            df: Historical data DataFrame
            symbol: Underlying symbol
            strike: Strike price
            option_type: CE or PE
        
        Returns:
            List of Bar objects
        """
        bars = []
        
        for _, row in df.iterrows():
            bar = Bar(
                token=0,  # Will be set by instrument manager
                timestamp=row['Date'],
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=int(row['No. of contracts']) if pd.notna(row['No. of contracts']) else 0,
                oi=int(row['Open Int']) if pd.notna(row['Open Int']) else None
            )
            
            bars.append(bar)
        
        return bars
    
    def convert_to_ticks(
        self,
        df: pd.DataFrame,
        symbol: str,
        strike: float,
        option_type: str
    ) -> List[Tick]:
        """
        Convert historical DataFrame to Tick objects.
        
        Uses LTP (Last Traded Price) as the tick price.
        
        Args:
            df: Historical data DataFrame
            symbol: Underlying symbol
            strike: Strike price
            option_type: CE or PE
        
        Returns:
            List of Tick objects
        """
        ticks = []
        
        for _, row in df.iterrows():
            # Use LTP as last price, fallback to Close
            last_price = row['LTP'] if pd.notna(row['LTP']) else row['Close']
            
            tick = Tick(
                token=0,  # Will be set by instrument manager
                timestamp=row['Date'],
                last_price=last_price,
                last_quantity=0,
                volume=int(row['No. of contracts']) if pd.notna(row['No. of contracts']) else 0,
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                oi=int(row['Open Int']) if pd.notna(row['Open Int']) else 0
            )
            
            ticks.append(tick)
        
        return ticks
    
    def get_atm_strikes(
        self,
        symbol: str,
        date: datetime,
        num_strikes: int = 5
    ) -> List[float]:
        """
        Get ATM (At-The-Money) strikes for a date.
        
        Args:
            symbol: NIFTY or BANKNIFTY
            date: Trading date
            num_strikes: Number of strikes above and below ATM
        
        Returns:
            List of strike prices around ATM
        """
        chain = self.get_options_chain(symbol, date)
        
        if chain.empty:
            return []
        
        # Get underlying value (spot)
        underlying_value = chain['Underlying Value'].iloc[0] if 'Underlying Value' in chain.columns else None
        
        if not underlying_value:
            # Estimate from strike prices
            strikes = sorted(chain['Strike Price'].unique())
            underlying_value = strikes[len(strikes) // 2]
        
        # Find ATM strike (closest to underlying)
        strikes = sorted(chain['Strike Price'].unique())
        atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - underlying_value))
        
        # Get strikes around ATM
        start_idx = max(0, atm_idx - num_strikes)
        end_idx = min(len(strikes), atm_idx + num_strikes + 1)
        
        return strikes[start_idx:end_idx]
    
    def calculate_iv(
        self,
        symbol: str,
        strike: float,
        option_type: str,
        date: datetime,
        expiry: datetime,
        risk_free_rate: float = 0.06
    ) -> Optional[float]:
        """
        Calculate implied volatility from historical data.
        
        Uses Black-Scholes model (simplified).
        In production, use a proper IV calculator.
        
        Args:
            symbol: NIFTY or BANKNIFTY
            strike: Strike price
            option_type: CE or PE
            date: Trading date
            expiry: Expiry date
            risk_free_rate: Risk-free rate (default 6%)
        
        Returns:
            Implied volatility (as decimal, e.g., 0.20 for 20%)
        """
        df = self.get_strike_data(symbol, option_type, strike)
        row = df[df['Date'] == date]
        
        if row.empty:
            return None
        
        row = row.iloc[0]
        spot = row['Underlying Value']
        premium = row['LTP'] if pd.notna(row['LTP']) else row['Close']
        time_to_expiry = (expiry - date).days / 365.0
        
        if time_to_expiry <= 0 or premium <= 0:
            return None
        
        # Simplified IV calculation (placeholder)
        # In production, use proper Black-Scholes solver
        # For now, return a rough estimate based on premium/spot ratio
        moneyness = spot / strike if option_type == 'CE' else strike / spot
        
        # Rough IV estimate (not accurate, just for demonstration)
        iv_estimate = abs(premium / spot) / (time_to_expiry ** 0.5) * 2
        
        return min(max(iv_estimate, 0.05), 2.0)  # Clamp between 5% and 200%
    
    def get_date_range(self, symbol: str, option_type: str) -> tuple[datetime, datetime]:
        """Get available date range for a symbol/type"""
        df = self.load_file(symbol, option_type)
        
        if df.empty:
            return None, None
        
        return df['Date'].min(), df['Date'].max()
    
    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
        logger.info("Historical data cache cleared")

