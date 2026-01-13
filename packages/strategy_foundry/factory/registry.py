class StrategyRegistry:
    def __init__(self):
        self.strategies = {}

    def register(self, strategy_class):
        self.strategies[strategy_class.__name__] = strategy_class

registry = StrategyRegistry()
