import random
from typing import List
from packages.strategy_foundry.factory.grammar import (
    Strategy, StrategyBlock, EmaCrossBlock, RsiFilterBlock, SupertrendBlock, DonchianBlock
)

class StrategyGenerator:
    def __init__(self):
        pass

    def generate_random_strategy(self) -> Strategy:
        # Pick 2-3 blocks
        num_blocks = random.randint(2, 3)
        blocks = []

        # Block Types
        block_types = [
            "EmaCross", "RsiFilter", "Supertrend", "Donchian"
        ]

        for _ in range(num_blocks):
            b_type = random.choice(block_types)
            if b_type == "EmaCross":
                fast = random.choice([5, 9, 10, 20])
                slow = random.choice([20, 50, 100, 200])
                if fast >= slow: fast, slow = slow, fast
                if fast == slow: slow += 1
                blocks.append(EmaCrossBlock(fast, slow))

            elif b_type == "RsiFilter":
                period = 14
                threshold = random.choice([30, 40, 50, 60, 70])
                mode = random.choice(["long_if_above", "long_if_below"])
                blocks.append(RsiFilterBlock(period, threshold, mode))

            elif b_type == "Supertrend":
                period = random.choice([7, 10, 14])
                mult = random.choice([1.5, 2.0, 3.0])
                blocks.append(SupertrendBlock(period, mult))

            elif b_type == "Donchian":
                period = random.choice([20, 50])
                blocks.append(DonchianBlock(period))

        # Risk Params
        stop_loss = random.choice([1.0, 2.0, 3.0, 4.0])
        take_profit = stop_loss * random.choice([1.5, 2.0, 3.0])

        return Strategy(blocks, stop_loss, take_profit)

    def generate_batch(self, n: int) -> List[Strategy]:
        strategies = []
        seen_ids = set()
        attempts = 0
        while len(strategies) < n and attempts < n * 5:
            s = self.generate_random_strategy()
            if s.id not in seen_ids:
                strategies.append(s)
                seen_ids.add(s.id)
            attempts += 1
        return strategies
