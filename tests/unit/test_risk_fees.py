import pytest
from packages.core.risk import RiskManager, RiskConfig
from packages.core.models import Instrument, InstrumentType

class TestRiskFees:
    @pytest.fixture
    def risk_manager(self):
        config = RiskConfig({
            "fees_per_order": 20,
            "fees_per_option_leg": 0
        })
        return RiskManager(config)

    @pytest.fixture
    def equity_instrument(self):
        return Instrument(
            token=1,
            symbol="INFY",
            tradingsymbol="INFY",
            exchange="NSE",
            instrument_type=InstrumentType.EQ,
            lot_size=1,
            segment="NSE"
        )

    @pytest.fixture
    def option_instrument(self):
        return Instrument(
            token=3,
            symbol="NIFTY",
            tradingsymbol="NIFTY24JAN21500CE",
            exchange="NSE",
            instrument_type=InstrumentType.CE,
            lot_size=50,
            segment="NFO"
        )

    def test_equity_delivery_fees(self, risk_manager, equity_instrument):
        # Buy 100 qty at 1500, Sell at 1600
        qty = 100
        buy_price = 1500
        sell_price = 1600

        # Breakdown Target (Zerodha Equity Delivery - Conservative Estimate):
        # Turnover = (1500*100) + (1600*100) = 310,000
        # 1. Brokerage: 20 per order (Config limit) * 2 = 40
        # 2. STT: 0.1% on Turnover = 310,000 * 0.001 = 310.0
        # 3. Transaction Charges (NSE): 0.00325% = 310,000 * 0.0000325 = 10.075
        # 4. SEBI Charges: 10 per crore = 310,000 * 0.000001 = 0.31
        # 5. GST: 18% on (Brokerage + Txn + SEBI) = 0.18 * (40 + 10.075 + 0.31) = 0.18 * 50.385 = 9.0693
        # 6. Stamp Duty: 0.015% on Buy = 150,000 * 0.00015 = 22.5
        # Total = 40 + 310 + 10.075 + 0.31 + 9.0693 + 22.5 = 391.9543

        expected_fees = 391.9543
        fees = risk_manager.estimate_fees(equity_instrument, qty, buy_price, sell_price)

        print(f"\nEquity Delivery Fees: {fees}")
        assert fees == pytest.approx(expected_fees, abs=0.1)

    def test_option_buy_fees(self, risk_manager, option_instrument):
        # Buy 50 qty at 100, Sell at 120
        qty = 50
        buy_price = 100
        sell_price = 120

        # Breakdown Target (Zerodha Options):
        # Turnover = (100*50) + (120*50) = 5000 + 6000 = 11,000
        # 1. Brokerage: Flat 20 * 2 = 40
        # 2. STT: 0.1% on Sell = 6000 * 0.001 = 6.0
        # 3. Transaction Charges (NSE Options): 0.03503% = 11,000 * 0.0003503 = 3.8533
        # 4. SEBI Charges: 10 per crore = 11,000 * 0.000001 = 0.011
        # 5. GST: 18% on (40 + 3.8533 + 0.011) = 0.18 * 43.8643 = 7.895574
        # 6. Stamp Duty: 0.003% on Buy = 5000 * 0.00003 = 0.15
        # Total = 40 + 6 + 3.8533 + 0.011 + 7.895574 + 0.15 = 57.909874

        expected_fees = 57.9099
        fees = risk_manager.estimate_fees(option_instrument, qty, buy_price, sell_price)

        print(f"\nOption Buy Fees: {fees}")
        assert fees == pytest.approx(expected_fees, abs=0.1)
