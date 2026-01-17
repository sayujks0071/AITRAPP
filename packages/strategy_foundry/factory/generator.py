import time
import random
from typing import List
from .grammar import StrategyCandidate, hash_strategy
from .parameter_space import ParameterSpace

class StrategyGenerator:

    def generate_candidates(self, n: int = 50) -> List[StrategyCandidate]:
        candidates = []
        seen_hashes = set()

        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            attempts += 1
            strategy_def = self._create_random_strategy()
            sid = hash_strategy(strategy_def)

            if sid in seen_hashes:
                continue

            seen_hashes.add(sid)
            candidates.append(StrategyCandidate(
                id=sid,
                source_code=strategy_def,
                created_at=time.time()
            ))

        return candidates

    def _create_random_strategy(self):
        # Decide type: Trend or Mean Reversion
        # Bias towards trend for daily timeframe
        is_trend = random.random() < 0.7

        logic_blocks = []

        if is_trend:
            logic_blocks.append(self._make_trend_block())
            filter_block = self._make_filter_block()
            if filter_block:
                logic_blocks.append(filter_block)
        else:
            logic_blocks.append(self._make_mean_reversion_block())
            # Usually mean reversion needs a regime filter (e.g. only if ADX < 25)
            # But we'll keep it simple for now

        risk_config = self._make_risk_config()

        return {
            "type": "Trend" if is_trend else "MeanReversion",
            "logic": logic_blocks,
            "risk": risk_config
        }

    def _make_trend_block(self):
        choice = ParameterSpace.get_trend_logic()
        if choice == "ema_crossover":
            fast = ParameterSpace.random_ma_period()
            slow = ParameterSpace.random_ma_period()
            if fast >= slow: fast, slow = 10, 50 # Fallback correction
            return {
                "type": "ema_crossover",
                "params": {"fast": fast, "slow": slow}
            }
        elif choice == "supertrend":
            return {
                "type": "supertrend",
                "params": {"period": 10, "multiplier": 3.0} # Keep standard for now or randomize
            }
        elif choice == "donchian":
            return {
                "type": "donchian",
                "params": {"period": 20}
            }
        return {"type": "noop"}

    def _make_mean_reversion_block(self):
        choice = ParameterSpace.get_mean_reversion_logic()
        if choice == "rsi_reversion":
            return {
                "type": "rsi_reversion",
                "params": {
                    "period": ParameterSpace.random_rsi_period(),
                    "lower": random.choice(ParameterSpace.RSI_OVERSOLD),
                    "upper": random.choice(ParameterSpace.RSI_OVERBOUGHT)
                }
            }
        return {"type": "noop"}

    def _make_filter_block(self):
        choice = ParameterSpace.get_filter_logic()
        if choice == "adx_filter":
            return {
                "type": "adx_filter",
                "params": {"period": 14, "threshold": random.choice(ParameterSpace.ADX_TRENDING)}
            }
        elif choice == "regime_filter":
             return {
                "type": "regime_filter",
                "params": {"ma_period": 200}
            }
        return None

    def _make_risk_config(self):
        return {
            "stop_loss_atr": random.choice(ParameterSpace.SL_ATR_MULT),
            "take_profit_atr": random.choice(ParameterSpace.TP_ATR_MULT),
            "trailing_stop": random.choice(ParameterSpace.TRAILING_SL)
        }
