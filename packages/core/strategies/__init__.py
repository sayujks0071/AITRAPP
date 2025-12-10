"""Trading strategies"""
from packages.core.strategies.base import Strategy, StrategyContext
from packages.core.strategies.orb import ORBStrategy
from packages.core.strategies.trend_pullback import TrendPullbackStrategy
from packages.core.strategies.options_ranker import OptionsRankerStrategy
from packages.core.strategies.iron_condor import IronCondorStrategy
from packages.core.strategies.regime_vol_engine import (
    RegimeVolEngine,
    RegimeClassifier,
    RegimeFeatures,
    VolRegime,
)
from packages.core.strategies.gamma_scalper import (
    GammaScalper,
    GammaBookState,
    OptionGreeks,
)
from packages.core.strategies.calendar_arb import (
    CalendarArb,
    CalendarBookState,
)
from packages.core.strategies.dispersion_arb import (
    DispersionArb,
    DispersionBookState,
)
from packages.core.strategies.tail_short_vol import (
    TailShortVolOverlay,
    TailState,
)
from packages.core.strategies.expiry_short_strangle_v2 import (
    ExpiryShortStrangleV2,
)
from packages.core.strategies.intraday_short_strangle_v1 import (
    IntradayShortStrangleV1,
)
from packages.core.strategies.trend_credit_spread_v1 import (
    TrendCreditSpreadV1,
)
from packages.core.event_vol_engine import (
    EventVolEngine,
    EventDef,
    DayContext,
)
from packages.core.strategies.finrl_strategy import (
    FinRLStrategy,
    FinRLDataAdapter,
)
from packages.core.strategies.sma_momentum import SMAMomentumStrategy
from packages.core.strategies.mean_reversion import MeanReversionStrategy
from packages.core.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from packages.core.strategies.macd_strategy import MACDStrategy
from packages.core.strategies.bollinger_bands_strategy import BollingerBandsStrategy
from packages.core.strategies.vwap_strategy import VWAPStrategy
from packages.core.strategies.breakout_strategy import BreakoutStrategy
from packages.core.strategies.premium_adaptive_trend import PremiumAdaptiveTrendStrategy
from packages.core.strategies.ml_premium_alpha import MLPremiumAlphaStrategy

# Top 10 World's Best Strategies for NSE & MCX
from packages.core.strategies.supertrend_strategy import SuperTrendStrategy
from packages.core.strategies.donchian_breakout_strategy import DonchianBreakoutStrategy
from packages.core.strategies.stochastic_strategy import StochasticStrategy
from packages.core.strategies.adx_trend_strategy import ADXTrendStrategy
from packages.core.strategies.ichimoku_strategy import IchimokuStrategy
from packages.core.strategies.price_action_sr_strategy import PriceActionSRStrategy
from packages.core.strategies.volume_profile_strategy import VolumeProfileStrategy
from packages.core.strategies.pivot_point_strategy import PivotPointStrategy
from packages.core.strategies.cci_strategy import CCIStrategy
from packages.core.strategies.parabolic_sar_strategy import ParabolicSARStrategy

__all__ = [
    "Strategy",
    "StrategyContext",
    "ORBStrategy",
    "TrendPullbackStrategy",
    "OptionsRankerStrategy",
    "IronCondorStrategy",
    "RegimeVolEngine",
    "RegimeClassifier",
    "RegimeFeatures",
    "VolRegime",
    "GammaScalper",
    "GammaBookState",
    "OptionGreeks",
    "CalendarArb",
    "CalendarBookState",
    "DispersionArb",
    "DispersionBookState",
    "TailShortVolOverlay",
    "TailState",
    "ExpiryShortStrangleV2",
    "IntradayShortStrangleV1",
    "TrendCreditSpreadV1",
    "EventVolEngine",
    "EventDef",
    "DayContext",
    "FinRLStrategy",
    "FinRLDataAdapter",
    "SMAMomentumStrategy",
    "MeanReversionStrategy",
    "RSIMeanReversionStrategy",
    "MACDStrategy",
    "BollingerBandsStrategy",
    "VWAPStrategy",
    "BreakoutStrategy",
    "PremiumAdaptiveTrendStrategy",
    "MLPremiumAlphaStrategy",
    # Top 10 World's Best Strategies
    "SuperTrendStrategy",
    "DonchianBreakoutStrategy",
    "StochasticStrategy",
    "ADXTrendStrategy",
    "IchimokuStrategy",
    "PriceActionSRStrategy",
    "VolumeProfileStrategy",
    "PivotPointStrategy",
    "CCIStrategy",
    "ParabolicSARStrategy",
]
