from packages.strategy_foundry.factory.generator import StrategyGenerator

if __name__ == "__main__":
    gen = StrategyGenerator()
    candidates = gen.generate_candidates(5)
    print(f"Generated {len(candidates)} candidates:")
    for c in candidates:
        print(c)
