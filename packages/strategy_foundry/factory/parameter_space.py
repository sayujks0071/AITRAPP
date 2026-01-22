import random

class ParameterSpace:
    """
    Defines the parameter space for strategy generation.
    """

    # Ranges
    PERIOD_FAST = range(3, 20)
    PERIOD_SLOW = range(20, 100)
    RSI_PERIOD = [7, 14, 21]
    RSI_OVERBOUGHT = range(70, 90, 5)
    RSI_OVERSOLD = range(10, 30, 5)
    BB_STD = [1.5, 2.0, 2.5]
    ATR_PERIOD = [10, 14, 20]
    ATR_MULTIPLIER = [1.0, 1.5, 2.0, 3.0]
    DONCHIAN_PERIOD = [10, 20, 40, 60]
    TIME_STOP_BARS = [6, 12, 24, 48] # e.g. 1 hour, 2 hours, etc on 5m

    @staticmethod
    def sample_entry_type():
        return random.choice([
            "rsi_reversion",
            "bollinger_reversion",
            "ema_crossover",
            "donchian_breakout",
            "orb_breakout"
        ])

    @staticmethod
    def sample_exit_type():
        # Mandatory stops are usually added by default, this is for logic based exits
        return random.choice([
            "time_stop",
            "rsi_exit",
            "trailing_stop_atr"
        ])

    @staticmethod
    def sample_filter_type():
        return random.choice([
            "trend_filter_ema",
            "volatility_filter_atr",
            "no_filter"
        ])

    @staticmethod
    def get_params(block_type: str):
        if block_type == "rsi_reversion":
            return {
                "period": random.choice(ParameterSpace.RSI_PERIOD),
                "lower": random.choice(ParameterSpace.RSI_OVERSOLD),
                "upper": random.choice(ParameterSpace.RSI_OVERBOUGHT)
            }
        elif block_type == "bollinger_reversion":
            return {
                "period": 20,
                "std": random.choice(ParameterSpace.BB_STD)
            }
        elif block_type == "ema_crossover":
            fast = random.choice(ParameterSpace.PERIOD_FAST)
            slow = random.choice(ParameterSpace.PERIOD_SLOW)
            return {"fast": fast, "slow": slow}
        elif block_type == "donchian_breakout":
            return {
                "period": random.choice(ParameterSpace.DONCHIAN_PERIOD)
            }
        elif block_type == "orb_breakout":
            return {
                "time_window_mins": 30 # usually fixed to first 30 mins
            }
        elif block_type == "time_stop":
            return {
                "bars": random.choice(ParameterSpace.TIME_STOP_BARS)
            }
        elif block_type == "rsi_exit":
             return {
                "period": random.choice(ParameterSpace.RSI_PERIOD),
                "threshold": 50 # Cross 50 to exit
            }
        elif block_type == "trailing_stop_atr":
            return {
                "period": random.choice(ParameterSpace.ATR_PERIOD),
                "multiplier": random.choice(ParameterSpace.ATR_MULTIPLIER)
            }
        elif block_type == "trend_filter_ema":
            return {
                "period": 200 # Classic
            }
        elif block_type == "volatility_filter_atr":
             return {
                 "period": 14,
                 "min_val": 0.0 # Context dependent, maybe hard to randomize meaningfully without normalization
             }
        return {}
