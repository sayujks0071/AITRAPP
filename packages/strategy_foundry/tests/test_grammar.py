import unittest
import pandas as pd
from packages.strategy_foundry.factory.grammar import StrategyBlock, StrategyCandidate

class TestGrammar(unittest.TestCase):
    def test_block_serialization(self):
        block = StrategyBlock(name="TestBlock", params={"p1": 1, "p2": 0.5})
        d = block.to_dict()
        self.assertEqual(d["name"], "TestBlock")
        self.assertEqual(d["params"]["p1"], 1)

    def test_candidate_id_stability(self):
        b1 = StrategyBlock(name="Entry", params={"a": 1})
        b2 = StrategyBlock(name="Exit", params={"b": 2})
        c1 = StrategyCandidate(entry_block=b1, exit_blocks=[b2], filter_blocks=[], timeframe="15m")
        c2 = StrategyCandidate(entry_block=b1, exit_blocks=[b2], filter_blocks=[], timeframe="15m")

        self.assertEqual(c1.get_id(), c2.get_id())

        c3 = StrategyCandidate(entry_block=b1, exit_blocks=[b2], filter_blocks=[], timeframe="5m")
        self.assertNotEqual(c1.get_id(), c3.get_id())

if __name__ == '__main__':
    unittest.main()
