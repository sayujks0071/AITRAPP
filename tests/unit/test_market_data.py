import unittest
from datetime import datetime, timedelta
from packages.core.market_data import TickAggregator
from packages.core.models import Tick

class TestVolumeAggregation(unittest.TestCase):
    def test_dropped_ticks_volume_loss(self):
        """
        Verify that TickAggregator correctly calculates volume from cumulative volume,
        capturing volume from dropped ticks.
        """
        token = 12345
        aggregator = TickAggregator(token, window_seconds=60)

        start_time = datetime(2025, 1, 1, 9, 15, 0)

        # Tick 1: Volume 1000, Last Qty 10
        tick1 = Tick(
            token=token,
            timestamp=start_time,
            last_price=100.0,
            last_quantity=10,
            volume=1000,
            oi=0,
            bid=0, ask=0, bid_quantity=0, ask_quantity=0,
            open=0, high=0, low=0, close=0,
            oi_day_high=0, oi_day_low=0
        )

        aggregator.add_tick(tick1)

        # Initial volume should be tick1.last_quantity (10) as we don't know history
        self.assertEqual(aggregator.current_bar.volume, 10)

        # Tick 2: Dropped ticks happened!
        # Volume jumped to 1500 (500 traded), but this specific tick only traded 5.
        # So we missed 495 volume from dropped ticks.
        tick2 = Tick(
            token=token,
            timestamp=start_time + timedelta(seconds=10),
            last_price=101.0,
            last_quantity=5,
            volume=1500, # Cumulative volume increased by 500 from 1000
            oi=0,
            bid=0, ask=0, bid_quantity=0, ask_quantity=0,
            open=0, high=0, low=0, close=0,
            oi_day_high=0, oi_day_low=0
        )

        aggregator.add_tick(tick2)

        # Volume should be 10 (initial) + (1500 - 1000) = 510
        self.assertEqual(aggregator.current_bar.volume, 510, "Aggregator should capture dropped volume using cumulative delta")

    def test_volume_reset(self):
        """
        Verify behavior when volume resets (e.g. next day or bad feed).
        """
        token = 67890
        aggregator = TickAggregator(token, window_seconds=60)
        start_time = datetime(2025, 1, 1, 9, 15, 0)

        # Tick 1: Volume 1000
        tick1 = Tick(
            token=token,
            timestamp=start_time,
            last_price=100.0,
            last_quantity=10,
            volume=1000,
            oi=0,
            bid=0, ask=0, bid_quantity=0, ask_quantity=0,
            open=0, high=0, low=0, close=0,
            oi_day_high=0, oi_day_low=0
        )
        aggregator.add_tick(tick1)

        # Tick 2: Volume resets to 10 (e.g. new day, or bad data)
        tick2 = Tick(
            token=token,
            timestamp=start_time + timedelta(seconds=1),
            last_price=101.0,
            last_quantity=5,
            volume=10, # RESET! 10 < 1000
            oi=0,
            bid=0, ask=0, bid_quantity=0, ask_quantity=0,
            open=0, high=0, low=0, close=0,
            oi_day_high=0, oi_day_low=0
        )

        aggregator.add_tick(tick2)

        # Delta would be 10 - 1000 = -990.
        # Implementation should fallback to last_quantity (5).
        # Total volume = 10 (initial) + 5 (fallback) = 15.

        self.assertEqual(aggregator.current_bar.volume, 15, "Should fallback to last_quantity on volume reset")

if __name__ == '__main__':
    unittest.main()
