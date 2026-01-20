import unittest
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.grammar import StrategyType

class TestFactory(unittest.TestCase):
    def test_generator(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(5)

        self.assertEqual(len(candidates), 5)
        for c in candidates:
            self.assertIn("type", c)
            self.assertIn("params", c)
            self.assertIn("id", c)

            # Check type validity
            valid_types = [t.value for t in StrategyType]
            self.assertIn(c["type"], valid_types)

if __name__ == "__main__":
    unittest.main()
