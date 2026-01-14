import random

class ParameterSpace:
    INDICATORS = ['rsi', 'adx', 'ema', 'supertrend', 'bollinger', 'donchian']
    OPERATORS = ['>', '<']

    @staticmethod
    def get_random_indicator():
        return random.choice(ParameterSpace.INDICATORS)

    @staticmethod
    def get_random_params(indicator):
        if indicator == 'rsi':
            return {'period': random.choice([7, 14, 21])}
        elif indicator == 'adx':
            return {'period': random.choice([14, 21])}
        elif indicator == 'ema':
            return {'period': random.choice([10, 20, 50, 100, 200])}
        elif indicator == 'supertrend':
            return {'period': random.choice([7, 10, 14]), 'multiplier': random.choice([2.0, 3.0])}
        elif indicator == 'bollinger':
            return {'period': 20, 'std': 2.0}
        elif indicator == 'donchian':
            return {'period': 20}
        return {}

    @staticmethod
    def get_random_threshold(indicator):
        if indicator == 'rsi':
            return random.choice([30, 40, 50, 60, 70])
        elif indicator == 'adx':
            return random.choice([20, 25, 30])
        return 0

