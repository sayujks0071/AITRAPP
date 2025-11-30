"""
FinRL Deep Reinforcement Learning Strategy
==========================================

Integrates FinRL DRL agents with AITRAPP trading system.
Uses trained FinRL models to generate trading signals.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import structlog

# Add FinRL to path
finrl_path = Path(__file__).parent.parent.parent.parent / "FinRL"
if str(finrl_path) not in sys.path:
    sys.path.insert(0, str(finrl_path))

from packages.core.models import Instrument, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)

try:
    from finrl.meta.env_stock_trading.env_stock_trading import StockTradingEnv
    from finrl.agents.stablebaselines3.models import DRLAgent
    from stable_baselines3 import PPO, A2C, DDPG, TD3, SAC
    FINRL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FinRL not fully available: {e}")
    FINRL_AVAILABLE = False
    # Create dummy classes for type hints
    class StockTradingEnv:
        pass
    class DRLAgent:
        pass


class FinRLDataAdapter:
    """
    Adapter to convert AITRAPP market data to FinRL format.
    
    FinRL expects:
    - DataFrame with columns: date, open, high, low, close, volume, tic
    - Technical indicators as additional columns
    """
    
    @staticmethod
    def bars_to_dataframe(
        bars: List[Any],
        instrument: Instrument,
        tick: Optional[Any] = None
    ) -> pd.DataFrame:
        """
        Convert AITRAPP bars to FinRL DataFrame format.
        
        Args:
            bars: List of Bar objects
            instrument: Instrument object
            tick: Optional latest tick
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, tic
        """
        if not bars:
            return pd.DataFrame()
        
        data = []
        for bar in bars:
            data.append({
                'date': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume) if hasattr(bar, 'volume') else 0,
                'tic': instrument.symbol
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        return df
    
    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to DataFrame (FinRL style).
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with technical indicators added
        """
        if df.empty:
            return df
        
        try:
            from finrl.meta.preprocessor.preprocessors import data_split, FeatureEngineer
            
            # Use FinRL's feature engineering
            fe = FeatureEngineer(
                use_technical_indicator=True,
                use_turbulence=False,
                use_vix=False,
                user_defined_feature=False
            )
            
            processed_df = fe.preprocess_data(df)
            return processed_df
        except Exception as e:
            logger.warning(f"Could not add technical indicators: {e}")
            # Fallback: add basic indicators manually
            if len(df) > 0:
                df['rsi'] = 50.0  # Placeholder
                df['macd'] = 0.0
                df['boll_ub'] = df['close'] * 1.02
                df['boll_lb'] = df['close'] * 0.98
            return df


class FinRLStrategy(Strategy):
    """
    FinRL Deep Reinforcement Learning Strategy
    
    Uses trained FinRL DRL agents to generate trading signals.
    Supports multiple algorithms: PPO, A2C, DDPG, TD3, SAC
    
    Parameters:
    - model_path: Path to trained FinRL model
    - algorithm: DRL algorithm (PPO, A2C, DDPG, TD3, SAC)
    - lookback_window: Number of bars to use for prediction
    - min_confidence: Minimum confidence threshold for signals
    - enabled: Enable/disable strategy
    """
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        
        if not FINRL_AVAILABLE:
            logger.error("FinRL not available. Install dependencies: pip install -r FinRL/requirements.txt")
            self.enabled = False
            return
        
        # Model configuration
        self.model_path = params.get("model_path", "")
        self.algorithm = params.get("algorithm", "PPO").upper()
        self.lookback_window = params.get("lookback_window", 30)
        self.min_confidence = params.get("min_confidence", 0.6)
        
        # Model and environment
        self.model: Optional[Any] = None
        self.env: Optional[StockTradingEnv] = None
        self.data_adapter = FinRLDataAdapter()
        
        # State tracking
        self.price_history: Dict[int, List[float]] = {}  # token -> price history
        self.last_prediction: Dict[int, float] = {}  # token -> last prediction
        
        # Initialize model if path provided
        if self.model_path and os.path.exists(self.model_path):
            self._load_model()
        else:
            logger.warning(f"FinRL model not found at {self.model_path}. Strategy will be disabled.")
            self.enabled = False
    
    def _load_model(self) -> None:
        """Load trained FinRL model"""
        try:
            model_class_map = {
                "PPO": PPO,
                "A2C": A2C,
                "DDPG": DDPG,
                "TD3": TD3,
                "SAC": SAC
            }
            
            if self.algorithm not in model_class_map:
                logger.error(f"Unsupported algorithm: {self.algorithm}")
                self.enabled = False
                return
            
            model_class = model_class_map[self.algorithm]
            self.model = model_class.load(self.model_path)
            
            logger.info(
                f"FinRL model loaded",
                algorithm=self.algorithm,
                path=self.model_path
            )
        except Exception as e:
            logger.error(f"Failed to load FinRL model: {e}", exc_info=True)
            self.enabled = False
    
    def _prepare_observation(self, context: StrategyContext) -> Optional[np.ndarray]:
        """
        Prepare observation vector for FinRL model.
        
        Args:
            context: Strategy context with market data
            
        Returns:
            Observation array or None if insufficient data
        """
        try:
            # Convert bars to DataFrame
            bars = context.bars_5s or context.bars_1s or []
            if len(bars) < self.lookback_window:
                return None
            
            df = self.data_adapter.bars_to_dataframe(bars, context.instrument, context.latest_tick)
            if df.empty:
                return None
            
            # Add technical indicators
            df = self.data_adapter.add_technical_indicators(df)
            
            # Get last N rows for lookback window
            recent_data = df.tail(self.lookback_window)
            
            # Extract features (FinRL format)
            # Typical features: OHLCV + technical indicators
            feature_cols = ['open', 'high', 'low', 'close', 'volume']
            tech_cols = [col for col in recent_data.columns if col not in ['date', 'tic'] + feature_cols]
            feature_cols.extend(tech_cols)
            
            # Select available columns
            available_cols = [col for col in feature_cols if col in recent_data.columns]
            if not available_cols:
                return None
            
            # Create observation vector
            observation = recent_data[available_cols].values.flatten()
            
            # Pad or truncate to expected size (FinRL models expect fixed size)
            expected_size = self.lookback_window * len(available_cols)
            if len(observation) < expected_size:
                # Pad with last value
                observation = np.pad(observation, (0, expected_size - len(observation)), mode='edge')
            elif len(observation) > expected_size:
                observation = observation[:expected_size]
            
            return observation.astype(np.float32)
        
        except Exception as e:
            logger.warning(f"Failed to prepare observation: {e}")
            return None
    
    def _predict_action(self, observation: np.ndarray) -> Optional[int]:
        """
        Predict action using FinRL model.
        
        Args:
            observation: Observation vector
            
        Returns:
            Action (0=hold, 1=buy, 2=sell) or None
        """
        if self.model is None:
            return None
        
        try:
            # FinRL models typically output action directly
            action, _ = self.model.predict(observation, deterministic=True)
            
            # Convert to integer if needed
            if isinstance(action, np.ndarray):
                action = int(action.item() if action.size == 1 else action[0])
            
            return action
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return None
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """
        Generate trading signals using FinRL model.
        
        Args:
            context: Strategy context with market data
            
        Returns:
            List of trading signals
        """
        if not self.validate(context) or not self.enabled or self.model is None:
            return []
        
        signals: List[Signal] = []
        
        try:
            # Prepare observation
            observation = self._prepare_observation(context)
            if observation is None:
                return []
            
            # Get prediction
            action = self._predict_action(observation)
            if action is None:
                return []
            
            # FinRL action mapping:
            # 0 = hold, 1 = buy, 2 = sell
            # For options trading, we map to LONG/SHORT signals
            
            if action == 1:  # Buy signal
                signal = Signal(
                    strategy=self.name,
                    instrument=context.instrument,
                    side=SignalSide.LONG,
                    confidence=0.7,  # Default confidence
                    reason=f"FinRL {self.algorithm} buy signal",
                    metadata={
                        "algorithm": self.algorithm,
                        "action": int(action),
                        "lookback": self.lookback_window
                    }
                )
                signals.append(signal)
                self.signals_generated += 1
                
            elif action == 2:  # Sell signal
                signal = Signal(
                    strategy=self.name,
                    instrument=context.instrument,
                    side=SignalSide.SHORT,
                    confidence=0.7,  # Default confidence
                    reason=f"FinRL {self.algorithm} sell signal",
                    metadata={
                        "algorithm": self.algorithm,
                        "action": int(action),
                        "lookback": self.lookback_window
                    }
                )
                signals.append(signal)
                self.signals_generated += 1
            
            # Store prediction for tracking
            self.last_prediction[context.instrument.token] = float(action)
            
        except Exception as e:
            logger.error(f"FinRL signal generation failed: {e}", exc_info=True)
        
        return signals
    
    def validate(self, context: StrategyContext) -> bool:
        """Validate if strategy can generate signals"""
        if not super().validate(context):
            return False
        
        if not FINRL_AVAILABLE or self.model is None:
            return False
        
        # Need sufficient historical data
        bars = context.bars_5s or context.bars_1s or []
        if len(bars) < self.lookback_window:
            return False
        
        return True


