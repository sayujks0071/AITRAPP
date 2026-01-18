import unittest
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.grammar import StrategyCandidate

class TestFactory(unittest.TestCase):
    def test_generator(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(n=5)
        self.assertEqual(len(candidates), 5)
        self.assertTrue(isinstance(candidates[0], StrategyCandidate))
        self.assertTrue("entry_type" in candidates[0].params)

    def test_json_serialization(self):
        gen = StrategyGenerator()
        c = gen.generate_candidates(n=1)[0]
        j = c.to_json()
        c2 = StrategyCandidate.from_json(j)
        self.assertEqual(c.strategy_id, c2.strategy_id)
        self.assertEqual(c.params, c2.params)

if __name__ == '__main__':
    unittest.main()
