import pytest
from packages.core.historical_data import HistoricalDataLoader
from apps.api.main import BacktestRequest
from pydantic import ValidationError

def test_historical_data_loader_path_traversal_check():
    """
    Test that HistoricalDataLoader rejects symbols with path traversal characters.
    """
    loader = HistoricalDataLoader(data_dir="test_data")

    # Validation should prevent calling glob or open
    # We pass invalid symbol
    symbol_with_traversal = "../../../etc/passwd"

    with pytest.raises(ValueError) as excinfo:
        loader.load_file(symbol=symbol_with_traversal, option_type="CE")

    assert "Invalid symbol format" in str(excinfo.value)

def test_backtest_request_validation_invalid():
    """
    Test that BacktestRequest Pydantic model rejects invalid symbols.
    """
    invalid_payload = {
        "symbol": "../bad_symbol",
        "start_date": "2023-01-01",
        "end_date": "2023-01-02",
        "initial_capital": 100000,
        "strategy": "all"
    }

    with pytest.raises(ValidationError) as excinfo:
        BacktestRequest(**invalid_payload)

    assert "Symbol must be alphanumeric" in str(excinfo.value)

def test_backtest_request_validation_valid():
    """
    Test that BacktestRequest Pydantic model accepts valid symbols.
    """
    valid_payload = {
        "symbol": "NIFTY",
        "start_date": "2023-01-01",
        "end_date": "2023-01-02",
        "initial_capital": 100000,
        "strategy": "all"
    }
    req = BacktestRequest(**valid_payload)
    assert req.symbol == "NIFTY"
