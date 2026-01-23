from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings

client = TestClient(app)

def test_backtest_input_validation():
    """Test validation of backtest requests"""
    headers = {"X-API-Key": settings.api_secret_key}

    # 1. Test start_date > end_date
    payload = {
        "symbol": "NIFTY",
        "start_date": "2024-01-10",
        "end_date": "2024-01-01",
        "initial_capital": 1000000,
        "strategy": "all"
    }
    response = client.post("/backtest", json=payload, headers=headers)
    assert response.status_code == 422
    assert "start_date must be before end_date" in str(response.json())

    # 2. Test duration > 365 days
    payload = {
        "symbol": "NIFTY",
        "start_date": "2023-01-01",
        "end_date": "2024-02-01", # > 1 year
        "initial_capital": 1000000,
        "strategy": "all"
    }
    response = client.post("/backtest", json=payload, headers=headers)
    assert response.status_code == 422
    assert "Backtest duration cannot exceed 365 days" in str(response.json())

    # 3. Test symbol validation (invalid char)
    payload = {
        "symbol": "NIFTY$%",
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",
        "initial_capital": 1000000,
        "strategy": "all"
    }
    response = client.post("/backtest", json=payload, headers=headers)
    assert response.status_code == 422
    assert "Symbol must be alphanumeric" in str(response.json())
