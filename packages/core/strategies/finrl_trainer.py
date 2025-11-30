"""
FinRL Model Training Script
===========================

Trains FinRL DRL agents for use with FinRLStrategy.
Supports multiple algorithms: PPO, A2C, DDPG, TD3, SAC
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import structlog

# Add FinRL to path
finrl_path = Path(__file__).parent.parent.parent.parent / "FinRL"
if str(finrl_path) not in sys.path:
    sys.path.insert(0, str(finrl_path))

logger = structlog.get_logger(__name__)

try:
    from finrl.meta.env_stock_trading.env_stock_trading import StockTradingEnv
    from finrl.agents.stablebaselines3.models import DRLAgent
    from finrl.meta.preprocessor.preprocessors import FeatureEngineer
    from stable_baselines3 import PPO, A2C, DDPG, TD3, SAC
    FINRL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FinRL not fully available: {e}")
    FINRL_AVAILABLE = False


class FinRLTrainer:
    """
    Trainer for FinRL DRL models.
    
    Usage:
        trainer = FinRLTrainer()
        trainer.train(
            data_path="data/stock_data.csv",
            algorithm="PPO",
            model_save_path="models/finrl_ppo.zip"
        )
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.feature_engineer = None
        
        if FINRL_AVAILABLE:
            self.feature_engineer = FeatureEngineer(
                use_technical_indicator=True,
                use_turbulence=False,
                use_vix=False,
                user_defined_feature=False
            )
    
    def prepare_data(
        self,
        data_path: str,
        train_start: str,
        train_end: str,
        trade_start: str,
        trade_end: str
    ) -> tuple:
        """
        Prepare and split data for training.
        
        Args:
            data_path: Path to CSV file with OHLCV data
            train_start: Training start date (YYYY-MM-DD)
            train_end: Training end date (YYYY-MM-DD)
            trade_start: Trading start date (YYYY-MM-DD)
            trade_end: Trading end date (YYYY-MM-DD)
            
        Returns:
            Tuple of (train_data, trade_data) DataFrames
        """
        if not FINRL_AVAILABLE:
            raise ImportError("FinRL not available")
        
        # Load data
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Add technical indicators
        if self.feature_engineer:
            df = self.feature_engineer.preprocess_data(df)
        
        # Split data
        train_data = df[(df['date'] >= train_start) & (df['date'] <= train_end)]
        trade_data = df[(df['date'] >= trade_start) & (df['date'] <= trade_end)]
        
        return train_data, trade_data
    
    def create_environment(
        self,
        df: pd.DataFrame,
        stock_dim: int,
        hmax: int = 100,
        initial_amount: float = 1000000,
        transaction_cost_pct: float = 0.001
    ) -> StockTradingEnv:
        """
        Create FinRL trading environment.
        
        Args:
            df: DataFrame with processed data
            stock_dim: Number of stocks
            hmax: Maximum number of shares to trade
            initial_amount: Initial capital
            transaction_cost_pct: Transaction cost percentage
            
        Returns:
            StockTradingEnv instance
        """
        if not FINRL_AVAILABLE:
            raise ImportError("FinRL not available")
        
        env = StockTradingEnv(
            df=df,
            stock_dim=stock_dim,
            hmax=hmax,
            initial_amount=initial_amount,
            transaction_cost_pct=transaction_cost_pct,
            reward_scaling=1e-4,
            state_space=stock_dim,
            action_space=stock_dim,
            tech_indicator_list=self._get_tech_indicators(df)
        )
        
        return env
    
    def _get_tech_indicators(self, df: pd.DataFrame) -> List[str]:
        """Extract technical indicator column names"""
        exclude_cols = ['date', 'tic', 'open', 'high', 'low', 'close', 'volume']
        tech_cols = [col for col in df.columns if col not in exclude_cols]
        return tech_cols
    
    def train(
        self,
        train_data: pd.DataFrame,
        algorithm: str = "PPO",
        model_save_path: str = "models/finrl_model.zip",
        total_timesteps: int = 100000,
        **kwargs
    ) -> str:
        """
        Train FinRL model.
        
        Args:
            train_data: Training data DataFrame
            algorithm: DRL algorithm (PPO, A2C, DDPG, TD3, SAC)
            model_save_path: Path to save trained model
            total_timesteps: Number of training timesteps
            **kwargs: Additional algorithm-specific parameters
            
        Returns:
            Path to saved model
        """
        if not FINRL_AVAILABLE:
            raise ImportError("FinRL not available")
        
        # Get unique stocks
        stock_list = train_data['tic'].unique().tolist()
        stock_dim = len(stock_list)
        
        # Create environment
        env = self.create_environment(train_data, stock_dim)
        env_train, _ = env.get_sb_env()
        
        # Initialize agent
        agent = DRLAgent(env=env_train)
        
        # Algorithm-specific parameters
        model_params = {
            "PPO": {
                "n_steps": 2048,
                "ent_coef": 0.01,
                "learning_rate": 0.00025,
                "batch_size": 128
            },
            "A2C": {
                "n_steps": 5,
                "ent_coef": 0.01,
                "learning_rate": 0.0007
            },
            "DDPG": {
                "batch_size": 128,
                "buffer_size": 50000,
                "learning_rate": 0.0005
            },
            "TD3": {
                "batch_size": 100,
                "buffer_size": 100000,
                "learning_rate": 0.001
            },
            "SAC": {
                "batch_size": 128,
                "buffer_size": 100000,
                "learning_rate": 0.0003
            }
        }
        
        params = model_params.get(algorithm.upper(), {})
        params.update(kwargs)
        
        # Train model
        logger.info(f"Training {algorithm} model...")
        model = agent.get_model(algorithm.upper(), model_kwargs=params)
        model = agent.train_model(
            model=model,
            tb_log_name=f"{algorithm}",
            total_timesteps=total_timesteps
        )
        
        # Save model
        os.makedirs(os.path.dirname(model_save_path) if os.path.dirname(model_save_path) else ".", exist_ok=True)
        model.save(model_save_path)
        
        logger.info(f"Model saved to {model_save_path}")
        return model_save_path
    
    def backtest(
        self,
        trade_data: pd.DataFrame,
        model_path: str,
        algorithm: str = "PPO"
    ) -> Dict:
        """
        Backtest trained model.
        
        Args:
            trade_data: Trading data DataFrame
            model_path: Path to trained model
            algorithm: DRL algorithm used
            
        Returns:
            Dictionary with backtest results
        """
        if not FINRL_AVAILABLE:
            raise ImportError("FinRL not available")
        
        # Load model
        model_class_map = {
            "PPO": PPO,
            "A2C": A2C,
            "DDPG": DDPG,
            "TD3": TD3,
            "SAC": SAC
        }
        
        model_class = model_class_map.get(algorithm.upper())
        if not model_class:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        model = model_class.load(model_path)
        
        # Create environment
        stock_list = trade_data['tic'].unique().tolist()
        stock_dim = len(stock_list)
        env = self.create_environment(trade_data, stock_dim)
        env_trade, _ = env.get_sb_env()
        
        # Run backtest
        df_account_value, df_actions = DRLAgent.DRL_prediction(
            model=model,
            environment=env_trade
        )
        
        # Calculate metrics
        returns = df_account_value['account_value'].pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0
        
        results = {
            "total_return": (df_account_value['account_value'].iloc[-1] / df_account_value['account_value'].iloc[0] - 1) * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": self._calculate_max_drawdown(df_account_value['account_value']),
            "final_value": float(df_account_value['account_value'].iloc[-1]),
            "account_value": df_account_value.to_dict('records'),
            "actions": df_actions.to_dict('records')
        }
        
        return results
    
    def _calculate_max_drawdown(self, account_value: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = account_value / account_value.iloc[0]
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min() * 100)


