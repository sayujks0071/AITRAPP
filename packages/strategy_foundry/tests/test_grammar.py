from packages.strategy_foundry.factory.grammar import StrategyCandidate, generate_id
from packages.strategy_foundry.factory.generator import StrategyGenerator

def test_grammar_id_stability():
    c1 = StrategyCandidate(
        id="",
        entry_logic={"type": "A"},
        exit_logic={"type": "B"},
        filters=[],
        timeframe="5m"
    )
    id1 = generate_id(c1)
    id2 = generate_id(c1)
    assert id1 == id2

def test_generator():
    gen = StrategyGenerator()
    cands = gen.generate(5)
    assert len(cands) == 5
    assert cands[0].timeframe in ["5m", "15m"]
