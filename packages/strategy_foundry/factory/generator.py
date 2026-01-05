"""
Strategy Generator
Generates random strategies based on the grammar.
"""
import random
from typing import List
from packages.strategy_foundry.factory.grammar import BLOCKS, StrategyConfig, Parameter

class StrategyGenerator:
    @staticmethod
    def generate_random_param(param: Parameter):
        if param.type == "int":
            return random.randrange(param.min, param.max + param.step, param.step)
        elif param.type == "float":
            # Avoid floating point weirdness
            steps = int((param.max - param.min) / param.step)
            return round(param.min + (random.randint(0, steps) * param.step), 2)
        elif param.type == "bool":
            return random.choice([True, False])
        elif param.type == "choice":
            return random.choice(param.options)
        return param.default

    @staticmethod
    def generate_candidate() -> StrategyConfig:
        # Pick one entry
        entry_names = [k for k, v in BLOCKS.items() if v.type == "entry"]
        entry_name = random.choice(entry_names)
        entry_block = BLOCKS[entry_name]
        entry_params = {
            name: StrategyGenerator.generate_random_param(p)
            for name, p in entry_block.params.items()
        }

        # Pick one risk
        risk_names = [k for k, v in BLOCKS.items() if v.type == "risk"]
        risk_name = random.choice(risk_names)
        risk_block = BLOCKS[risk_name]
        risk_params = {
            name: StrategyGenerator.generate_random_param(p)
            for name, p in risk_block.params.items()
        }

        # Pick one exit
        exit_names = [k for k, v in BLOCKS.items() if v.type == "exit"]
        exit_name = random.choice(exit_names)
        exit_block = BLOCKS[exit_name]
        exit_params = {
            name: StrategyGenerator.generate_random_param(p)
            for name, p in exit_block.params.items()
        }

        config = StrategyConfig(
            entry_block=entry_name,
            entry_params=entry_params,
            risk_block=risk_name,
            risk_params=risk_params,
            exit_block=exit_name,
            exit_params=exit_params
        )
        config.id = config.get_hash()
        return config

    @staticmethod
    def generate_population(n: int) -> List[StrategyConfig]:
        return [StrategyGenerator.generate_candidate() for _ in range(n)]
