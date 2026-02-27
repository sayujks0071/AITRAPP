# Recommended Trading & Backtesting Setup
# For Malaysia Markets + Dhan/OpenAlgo Integration

## Quick Start Installation

```bash
# Create virtual environment
python -m venv trading_env
source trading_env/bin/activate  # On Windows: trading_env\Scripts\activate

# Install backtesting framework (choose one)
pip install backtesting              # Backtesting.py (recommended)
# OR
pip install backtrader              # Backtrader (more features)

# Install data sources
pip install yfinance                # For Malaysia markets (Bursa)
pip install pandas ta-lib pandas-ta # Technical analysis

# For Indian markets (optional)
# Follow OpenAlgo installation: https://github.com/marketcalls/openalgo
```

## Example: Backtesting Malaysia Stocks

```python
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA

class SmaCross(Strategy):
    # Simple Moving Average Crossover Strategy
    n1 = 10  # Fast SMA
    n2 = 20  # Slow SMA

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.position.close()

# Download Bursa Malaysia stock data
# Example: Maybank (1155.KL), Public Bank (1295.KL), Tenaga (5347.KL)
ticker = "1155.KL"  # Maybank
data = yf.download(ticker, start="2023-01-01", end="2024-01-01")

# Run backtest
bt = Backtest(data, SmaCross, cash=100000, commission=0.002)
stats = bt.run()
print(stats)

# Optimize parameters
stats = bt.optimize(n1=range(5, 30, 5),
                    n2=range(10, 70, 5),
                    maximize='Sharpe Ratio')
print(stats)

# Plot results
bt.plot()
```

## Example: OpenAlgo + Dhan Integration

```python
# Install OpenAlgo first: https://github.com/marketcalls/openalgo

from openalgo import OpenAlgo

# Initialize OpenAlgo with Dhan broker
api = OpenAlgo(
    broker='dhan',
    api_key='your_dhan_api_key',
    api_secret='your_dhan_api_secret'
)

# Place order
order = api.place_order(
    symbol='RELIANCE',
    exchange='NSE',
    transaction_type='BUY',
    quantity=1,
    order_type='MARKET'
)

print(order)

# Get positions
positions = api.get_positions()
print(positions)
```

## Bursa Malaysia Stock Tickers

Common Bursa Malaysia stocks (use with yfinance):

```python
bursa_stocks = {
    "Maybank": "1155.KL",
    "Public Bank": "1295.KL",
    "Tenaga Nasional": "5347.KL",
    "CIMB": "1023.KL",
    "Petronas Gas": "6033.KL",
    "IHH Healthcare": "5225.KL",
    "Maxis": "6012.KL",
    "Axiata": "6888.KL",
    "Sime Darby": "4197.KL",
    "Hong Leong Bank": "5819.KL"
}

# Download multiple stocks
import pandas as pd

data = yf.download(
    list(bursa_stocks.values()),
    start="2023-01-01",
    end="2024-01-01",
    group_by='ticker'
)
```

## Resources

### Backtesting.py
- Documentation: https://kernc.github.io/backtesting.py/
- GitHub: https://github.com/kernc/backtesting.py
- Tutorial: https://www.interactivebrokers.com/campus/ibkr-quant-news/backtesting-py-an-introductory-guide-to-backtesting-with-python/

### OpenAlgo
- GitHub: https://github.com/marketcalls/openalgo
- Documentation: https://docs.openalgo.in/
- Dhan Integration: https://docs.openalgo.in/connect-brokers/brokers/dhan

### OpenEngine
- GitHub: https://github.com/marketcalls/openengine
- For backtesting Indian markets

### Malaysia Market Data
- yfinance: https://pypi.org/project/yfinance/
- Bursa Price API: https://nikizwan.com/bursa-price-api/
- Twelve Data: https://twelvedata.com/exchanges/XKLS

### Alternative Frameworks
- Backtrader: https://www.backtrader.com/
- Vectorbt: https://vectorbt.dev/
- List of frameworks: https://tradewithpython.com/list-of-most-extensive-backtesting-frameworks-available-in-python
