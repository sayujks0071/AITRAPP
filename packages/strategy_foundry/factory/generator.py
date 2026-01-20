"""Generates strategy candidates"""
import random
from typing import List
from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyBlock
from packages.strategy_foundry.factory.parameter_space import ENTRY_BLOCKS, EXIT_BLOCKS, FILTER_BLOCKS

class StrategyGenerator:
    def __init__(self):
        pass

    def generate(self, count: int = 10, timeframes: List[str] = ["15m"]) -> List[StrategyCandidate]:
        candidates = []
        for _ in range(count):
            tf = random.choice(timeframes)
            candidates.append(self._generate_one(tf))
        return candidates

    def _generate_one(self, timeframe: str) -> StrategyCandidate:
        # 1. Entry
        entry_name = random.choice(list(ENTRY_BLOCKS.keys()))
        entry_params = {p.name: p.sample() for p in ENTRY_BLOCKS[entry_name]}
        entry_block = StrategyBlock(name=entry_name, params=entry_params)

        # 2. Exits (Always include EODExit for Intraday)
        exit_blocks = []

        # EOD Exit
        exit_blocks.append(StrategyBlock(name="EODExit", params={}))

        # Stop Loss (ATR or Fixed) - High probability of having one
        if random.random() < 0.9:
            sl_name = "ATRStop"
            sl_params = {p.name: p.sample() for p in EXIT_BLOCKS[sl_name]}
            exit_blocks.append(StrategyBlock(name=sl_name, params=sl_params))

        # Target (Optional)
        if random.random() < 0.5:
            tp_name = "ProfitTarget"
            tp_params = {p.name: p.sample() for p in EXIT_BLOCKS[tp_name]}
            exit_blocks.append(StrategyBlock(name=tp_name, params=tp_params))

        # Time Stop (Optional)
        if random.random() < 0.3:
            ts_name = "TimeStop"
            ts_params = {p.name: p.sample() for p in EXIT_BLOCKS[ts_name]}
            exit_blocks.append(StrategyBlock(name=ts_name, params=ts_params))

        # 3. Filters (Optional)
        filter_blocks = []
        if random.random() < 0.5:
             # Pick one filter
             f_name = random.choice(list(FILTER_BLOCKS.keys()))
             f_params = {p.name: p.sample() for p in FILTER_BLOCKS[f_name]}
             filter_blocks.append(StrategyBlock(name=f_name, params=f_params))

        return StrategyCandidate(
            entry_block=entry_block,
            exit_blocks=exit_blocks,
            filter_blocks=filter_blocks,
            timeframe=timeframe
        )
