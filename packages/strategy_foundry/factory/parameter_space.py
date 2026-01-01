"""Strategy Parameter Space"""

# Ranges for strategy generation
PARAM_SPACE = {
    # Moving Averages
    "ma_fast": [5, 10, 20, 30],
    "ma_slow": [50, 100, 200],

    # RSI
    "rsi_period": [7, 14, 21],
    "rsi_overbought": [70, 75, 80],
    "rsi_oversold": [20, 25, 30],

    # ATR
    "atr_period": [10, 14, 20],
    "atr_multiplier": [1.5, 2.0, 2.5, 3.0],

    # Bollinger
    "bb_period": [20],
    "bb_std": [2.0, 2.5],

    # Supertrend
    "st_period": [7, 10, 14],
    "st_multiplier": [2.0, 3.0],

    # Donchian
    "donchian_period": [20, 50, 100],

    # Logic Choice
    "logic_type": ["trend_crossover", "rsi_mean_reversion", "supertrend_follow", "donchian_breakout", "bollinger_mean_reversion"]
}
