import pandas as pd
import pytest
from packages.core.historical_data import HistoricalDataLoader
import warnings
import os
import sys

class TestHistoricalDataLoaderNaValues:
    """Test that HistoricalDataLoader correctly handles missing values in CSV files."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        """Create a temporary directory for data."""
        return tmp_path

    @pytest.fixture
    def sample_csv(self, data_dir):
        """Create a sample CSV with missing values represented as '-'."""
        csv_content = """Symbol,Date,Expiry,Option type,Strike Price,Open,High,Low,Close,LTP,Settle Price,No. of contracts,Turnover,Premium Turnover,Open Int,Change in OI,Underlying Value
NIFTY,03-Oct-2025,16-Oct-2025,CE,25000,100,110,90,-,105,105,-,10000,5000,-,100,25100
NIFTY,04-Oct-2025,16-Oct-2025,CE,25000,105,115,95,110,110,110,50,11000,5500,1000,150,25150
"""
        file_path = data_dir / "OPTIDX_NIFTY_CE_12-Aug-2025_TO_12-Nov-2025.csv"
        with open(file_path, "w") as f:
            f.write(csv_content)
        return file_path

    def test_load_file_handles_na_values_without_warning(self, data_dir, sample_csv):
        """Test that load_file handles '-' as NaN without issuing a DtypeWarning."""
        loader = HistoricalDataLoader(data_dir=str(data_dir))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always") # Cause all warnings to always be triggered.
            df = loader.load_file("NIFTY", "CE")

            # Filter specifically for DtypeWarning
            dtype_warnings = [warning for warning in w if issubclass(warning.category, pd.errors.DtypeWarning)]
            assert len(dtype_warnings) == 0, f"Expected no DtypeWarnings, but got: {dtype_warnings}"

        # Verify correctness of data
        first_row = df.iloc[0]
        assert pd.isna(first_row['Close']), "Close value should be NaN"
        assert pd.isna(first_row['No. of contracts']), "Volume should be NaN"
        assert pd.isna(first_row['Open Int']), "Open Int should be NaN"

        # Verify second row is correct
        second_row = df.iloc[1]
        assert second_row['Close'] == 110.0
        assert second_row['No. of contracts'] == 50.0

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
