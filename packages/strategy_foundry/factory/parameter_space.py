import random

class ParameterSpace:
    # Indicator Periods
    MA_PERIODS = [10, 20, 50, 100, 200]
    RSI_PERIODS = [7, 14, 21]
    ATR_PERIODS = [14]
    ADX_PERIODS = [14]
    BB_PERIODS = [20]

    # Thresholds
    RSI_OVERSOLD = [20, 25, 30, 35]
    RSI_OVERBOUGHT = [65, 70, 75, 80]
    ADX_TRENDING = [20, 25, 30]

    # Risk
    SL_ATR_MULT = [1.0, 1.5, 2.0, 3.0]
    TP_ATR_MULT = [2.0, 3.0, 4.0, 5.0, 0] # 0 means no fixed TP (trailing only)
    TRAILING_SL = [True, False]

    @classmethod
    def random_ma_period(cls): return random.choice(cls.MA_PERIODS)
    @classmethod
    def random_rsi_period(cls): return random.choice(cls.RSI_PERIODS)

    @classmethod
    def get_trend_logic(cls):
        choices = ["ema_crossover", "supertrend", "donchian"]
        return random.choice(choices)

    @classmethod
    def get_mean_reversion_logic(cls):
        return "rsi_reversion"

    @classmethod
    def get_filter_logic(cls):
        choices = ["adx_filter", "regime_filter", None]
        return random.choice(choices)
