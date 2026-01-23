import unittest
from packages.strategy_foundry.factory.generator import StrategyGenerator

class TestGenerator(unittest.TestCase):
    def test_generation(self):
        gen = StrategyGenerator(seed=42)
        candidates = gen.generate_candidates(5)
        self.assertEqual(len(candidates), 5)

        # Check stability
        c1 = candidates[0]
        gen2 = StrategyGenerator(seed=42)
        c1_replica = gen2.generate_candidates(5)[0]

        self.assertEqual(c1.id, c1_replica.id)

        d1 = c1.model_dump()
        d2 = c1_replica.model_dump()
        del d1['generation_ts']
        del d2['generation_ts']
        self.assertEqual(d1, d2)

        print(f"Generated ID: {c1.id}")
        print(f"Summary: {c1.get_summary()}")

if __name__ == "__main__":
    unittest.main()
