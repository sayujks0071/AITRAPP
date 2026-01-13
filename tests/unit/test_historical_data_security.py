import pytest
from packages.core.historical_data import HistoricalDataLoader

def test_symbol_validation_valid():
    """Test that valid symbols are accepted (even if file not found)"""
    loader = HistoricalDataLoader()
    # Should not raise ValueError
    try:
        loader.load_file("NIFTY", "CE")
    except FileNotFoundError:
        pass
    except ValueError as e:
        pytest.fail(f"Valid symbol raised ValueError: {e}")

def test_symbol_validation_invalid_symbol():
    """Test that invalid symbols raise ValueError"""
    loader = HistoricalDataLoader()
    with pytest.raises(ValueError, match="Invalid input"):
        loader.load_file("../EVIL", "CE")

def test_symbol_validation_invalid_type():
    """Test that invalid option types raise ValueError"""
    loader = HistoricalDataLoader()
    with pytest.raises(ValueError, match="Invalid input"):
        loader.load_file("NIFTY", "CE/PE")
