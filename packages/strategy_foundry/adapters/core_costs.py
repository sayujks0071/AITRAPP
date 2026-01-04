from typing import Optional

# Adapter for core costs/risk if available
# Currently acts as a placeholder for cost constants used in backtest engine

DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_COST_BPS = 10.0

def get_slippage_bps(instrument: str = "NIFTY") -> float:
    return DEFAULT_SLIPPAGE_BPS

def get_transaction_cost_bps(instrument: str = "NIFTY") -> float:
    return DEFAULT_COST_BPS
