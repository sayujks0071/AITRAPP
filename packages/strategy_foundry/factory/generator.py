import random
from typing import List
from packages.strategy_foundry.factory.grammar import StrategySpec, StrategyBlock, GRAMMAR

class StrategyGenerator:
    """Generates random strategies based on the grammar"""

    def generate(self, count: int, instrument: str, timeframe: str) -> List[StrategySpec]:
        strategies = []
        seen_ids = set()

        attempts = 0
        while len(strategies) < count and attempts < count * 5:
            attempts += 1
            blocks = []

            # Mandatory: 1 Entry
            entry_def = random.choice(GRAMMAR["entry"])
            entry_params = {k: random.choice(v) for k, v in entry_def["params"].items()}
            blocks.append(StrategyBlock(entry_def["type"], entry_params))

            # Mandatory: ATR Stop (almost always good for intraday)
            # Or sample from exits
            # Let's sample 1-2 exits
            # Ensure at least one risk management exit

            # Simple approach: Pick 1-2 exits from grammar
            num_exits = random.randint(1, 2)
            # Don't pick same exit type twice
            exit_defs = random.sample(GRAMMAR["exit"], num_exits)

            for ex in exit_defs:
                ex_params = {k: random.choice(v) for k, v in ex["params"].items()}
                blocks.append(StrategyBlock(ex["type"], ex_params))

            # Optional: 0-1 Filters
            if random.random() < 0.5:
                filt_def = random.choice(GRAMMAR["filter"])
                filt_params = {k: random.choice(v) for k, v in filt_def["params"].items()}
                blocks.append(StrategyBlock(filt_def["type"], filt_params))

            spec = StrategySpec(blocks=blocks, timeframe=timeframe, instrument=instrument)

            if spec.id not in seen_ids:
                seen_ids.add(spec.id)
                strategies.append(spec)

        return strategies
