import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from packages.strategy_foundry.data.loader import DataLoader

class TestLoader(unittest.TestCase):
    def test_sanitize(self):
        loader = DataLoader()
        # Mock dataframe
        df = pd.DataFrame({
            "Open": [100], "High": [105], "Low": [95], "Close": [101], "Volume": [1000],
            "Adj Close": [101]
        }, index=pd.to_datetime(["2023-01-01"]))

        cleaned = loader._sanitize(df)
        self.assertTrue("open" in cleaned.columns)
        self.assertTrue("adj close" not in cleaned.columns) # We drop extra cols? No we keep required.
        # Wait, sanitize filters to 'required'.
        # required = ["open", "high", "low", "close", "volume"]
        self.assertTrue("adj close" not in cleaned.columns)

if __name__ == '__main__':
    unittest.main()
