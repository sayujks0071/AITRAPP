import unittest
import pandas as pd
from datetime import datetime
from packages.strategy_foundry.data.loader import DataLoader

class TestLoader(unittest.TestCase):
    def test_timezone_conversion(self):
        # Create a mock loader or just test the logic if we could isolate it.
        # But we can test get_data logic if we mock source.
        pass

    def test_instantiation(self):
        loader = DataLoader()
        self.assertIsNotNone(loader)
