
import unittest
from unittest.mock import MagicMock
from packages.core.risk import RiskManager, TaxConfig
from packages.core.models import Instrument, SignalSide

class TestFeeCalculation(unittest.TestCase):
    def setUp(self):
        # Mock configuration
        self.mock_config = MagicMock()
        self.mock_config.fees_per_order = 20.0

        # Initialize RiskManager with mock config
        self.risk_manager = RiskManager(self.mock_config)

        # Create a dummy instrument (Equity)
        self.instrument = MagicMock(spec=Instrument)
        self.instrument.is_equity = True
        self.instrument.is_future = False
        self.instrument.is_option = False
        self.instrument.exchange = "NSE"
        self.instrument.lot_size = 1

    def test_stamp_duty_and_stt_short_selling(self):
        """
        Verify that fees are calculated correctly for Short trades.
        - STT should be on the SELL side (Entry for Short).
        - Stamp Duty should be on the BUY side (Exit for Short).
        """
        quantity = 10000
        entry_price = 100.0  # Sell
        exit_price = 200.0   # Buy

        # Short Trade
        fees_short = self.risk_manager.estimate_fees(
            self.instrument,
            quantity,
            entry_price,
            exit_price,
            side=SignalSide.SHORT
        )

        turnover = quantity * (entry_price + exit_price) # 3,000,000

        # Brokerage: 40.0
        brokerage = 40.0

        # Txn: 3,000,000 * 0.0000325 = 97.5
        txn = turnover * TaxConfig.TXN_NSE_EQUITY

        # GST: 18% of (40 + 97.5) = 24.75
        gst = (brokerage + txn) * 0.18

        # SEBI: 3,000,000 * 0.000001 = 3.0
        sebi = turnover * TaxConfig.SEBI_CHARGES

        # STT (Equity Intraday): 0.025% on SELL side.
        # For Short, Sell is Entry (100).
        # STT = 100 * 10000 * 0.00025 = 250.0
        stt = (entry_price * quantity) * TaxConfig.STT_EQUITY_INTRADAY_SELL

        # Stamp Duty: 0.003% on BUY side.
        # For Short, Buy is Exit (200).
        # Stamp = 200 * 10000 * 0.00003 = 60.0
        stamp = (exit_price * quantity) * TaxConfig.STAMP_DUTY_BUY

        expected_total = brokerage + txn + gst + sebi + stt + stamp

        self.assertAlmostEqual(fees_short, expected_total, places=2)

    def test_stamp_duty_and_stt_long(self):
        """
        Verify that fees are calculated correctly for Long trades.
        - STT should be on the SELL side (Exit for Long).
        - Stamp Duty should be on the BUY side (Entry for Long).
        """
        quantity = 10000
        entry_price = 100.0  # Buy
        exit_price = 200.0   # Sell

        # Long Trade
        fees_long = self.risk_manager.estimate_fees(
            self.instrument,
            quantity,
            entry_price,
            exit_price,
            side=SignalSide.LONG
        )

        turnover = quantity * (entry_price + exit_price) # 3,000,000

        # Brokerage: 40.0
        brokerage = 40.0

        # Txn: 97.5
        txn = turnover * TaxConfig.TXN_NSE_EQUITY

        # GST: 24.75
        gst = (brokerage + txn) * 0.18

        # SEBI: 3.0
        sebi = turnover * TaxConfig.SEBI_CHARGES

        # STT (Equity Intraday): 0.025% on SELL side.
        # For Long, Sell is Exit (200).
        # STT = 200 * 10000 * 0.00025 = 500.0
        stt = (exit_price * quantity) * TaxConfig.STT_EQUITY_INTRADAY_SELL

        # Stamp Duty: 0.003% on BUY side.
        # For Long, Buy is Entry (100).
        # Stamp = 100 * 10000 * 0.00003 = 30.0
        stamp = (entry_price * quantity) * TaxConfig.STAMP_DUTY_BUY

        expected_total = brokerage + txn + gst + sebi + stt + stamp

        self.assertAlmostEqual(fees_long, expected_total, places=2)
