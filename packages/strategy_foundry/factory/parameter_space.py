import random

class ParameterSpace:
    @staticmethod
    def get_random_params(indicator: str):
        if indicator == 'ema':
            return {'period': random.choice([9, 20, 50, 200])}
        elif indicator == 'rsi':
            return {'period': random.choice([7, 14, 21])}
        elif indicator == 'bollinger':
            return {
                'period': random.choice([20, 30]),
                'std_dev': random.choice([2.0, 2.5])
            }
        elif indicator == 'atr':
            return {'period': 14}
        elif indicator == 'adx':
            return {'period': 14}
        elif indicator == 'supertrend':
            return {
                'period': random.choice([7, 10, 14]),
                'multiplier': random.choice([3.0, 4.0])
            }
        return {}
