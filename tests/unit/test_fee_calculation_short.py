"""Regression tests for Short trade fee calculations"""
import pytest
from packages.core.models import Instrument, InstrumentType, SignalSide
from packages.core.config import RiskConfig, TaxConfig
from packages.core.risk import RiskManager

@pytest.fixture
def risk_manager():
    config = RiskConfig({
        "per_trade_risk_pct": 1.0,
        "max_portfolio_heat_pct": 5.0,
        "daily_loss_stop_pct": 3.0,
        "slippage_bps": 5,
        "fees_per_order": 20,
        "fees_per_option_leg": 0,
        "max_position_size_multiplier": 1
    })
    return RiskManager(config)

@pytest.fixture
def equity_instrument():
    return Instrument(
        token=12345,
        symbol="RELIANCE",
        tradingsymbol="RELIANCE",
        exchange="NSE",
        instrument_type=InstrumentType.EQ,
        lot_size=1,
        tick_size=0.05
    )

def test_short_trade_fees_stt_stamp_duty(risk_manager, equity_instrument):
    """
    Test fee calculation for a Short Trade (Sell -> Buy).

    Correct Behavior for Intraday Short:
    - Entry (Sell): STT Applicable (0.025%), Stamp Duty Not Applicable
    - Exit (Buy): STT Not Applicable, Stamp Duty Applicable (0.003%)
    """

    quantity = 100
    entry_price = 2000.0  # Sell Price
    exit_price = 1990.0   # Buy Price

    # Expected Calculation for Short Trade:

    # Brokerage: 0.03% or 20 per order
    # Entry: 2000 * 100 * 0.0003 = 60 -> limited to 20
    # Exit: 1990 * 100 * 0.0003 = 59.7 -> limited to 20
    expected_brokerage = 40.0

    turnover = (entry_price + exit_price) * quantity

    # Transaction Charges: NSE Equity 0.0000325
    expected_txn = turnover * TaxConfig.TXN_NSE_EQUITY

    # GST: 18% of (Brokerage + Txn)
    expected_gst = (expected_brokerage + expected_txn) * TaxConfig.GST_RATE

    # SEBI: 0.000001 of turnover
    expected_sebi = turnover * TaxConfig.SEBI_CHARGES

    # STT (Sell side only): 0.025% of Sell Value (Entry Price)
    expected_stt = (entry_price * quantity) * TaxConfig.STT_EQUITY_INTRADAY_SELL

    # Stamp Duty (Buy side only): 0.003% of Buy Value (Exit Price)
    expected_stamp_duty = (exit_price * quantity) * TaxConfig.STAMP_DUTY_BUY

    expected_total_fees = expected_brokerage + expected_txn + expected_gst + expected_sebi + expected_stt + expected_stamp_duty

    fees = risk_manager.estimate_fees(
        instrument=equity_instrument,
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        side=SignalSide.SHORT
    )

    assert abs(fees - expected_total_fees) < 0.01, f"Fees mismatch: Got {fees}, Expected {expected_total_fees}"
