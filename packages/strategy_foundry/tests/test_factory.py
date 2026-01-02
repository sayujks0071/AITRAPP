
import pytest
from packages.strategy_foundry.factory.grammar import ParameterSpace
from packages.strategy_foundry.factory.generator import StrategyGenerator

def test_generator():
    gen = StrategyGenerator()
    candidates = gen.generate(5)

    assert len(candidates) == 5
    for c in candidates:
        assert c.id
        assert isinstance(c.entry_rules, list)
        assert isinstance(c.exit_rules, list)
        assert isinstance(c.params, dict)
