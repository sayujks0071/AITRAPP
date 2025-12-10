#!/usr/bin/env python3
"""
FinRL Model Training Script
============================

Trains FinRL DRL agents for use with AITRAPP trading system.

Usage:
    python scripts/train_finrl.py \
        --data data/stock_data.csv \
        --algorithm PPO \
        --train-start 2020-01-01 \
        --train-end 2023-12-31 \
        --output models/finrl_ppo.zip
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.core.strategies.finrl_trainer import FinRLTrainer
import structlog

logger = structlog.get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train FinRL DRL model")
    parser.add_argument("--data", required=True, help="Path to CSV data file")
    parser.add_argument("--algorithm", default="PPO", choices=["PPO", "A2C", "DDPG", "TD3", "SAC"],
                       help="DRL algorithm to use")
    parser.add_argument("--train-start", required=True, help="Training start date (YYYY-MM-DD)")
    parser.add_argument("--train-end", required=True, help="Training end date (YYYY-MM-DD)")
    parser.add_argument("--trade-start", help="Trading start date for backtest (YYYY-MM-DD)")
    parser.add_argument("--trade-end", help="Trading end date for backtest (YYYY-MM-DD)")
    parser.add_argument("--output", required=True, help="Output path for trained model")
    parser.add_argument("--timesteps", type=int, default=100000, help="Training timesteps")
    
    args = parser.parse_args()
    
    logger.info("Starting FinRL training", algorithm=args.algorithm)
    
    # Initialize trainer
    trainer = FinRLTrainer()
    
    # Prepare data
    logger.info("Preparing data...")
    train_data, trade_data = trainer.prepare_data(
        data_path=args.data,
        train_start=args.train_start,
        train_end=args.train_end,
        trade_start=args.trade_start or args.train_end,
        trade_end=args.trade_end or args.train_end
    )
    
    logger.info(f"Training data: {len(train_data)} rows")
    logger.info(f"Trade data: {len(trade_data)} rows")
    
    # Train model
    logger.info(f"Training {args.algorithm} model...")
    model_path = trainer.train(
        train_data=train_data,
        algorithm=args.algorithm,
        model_save_path=args.output,
        total_timesteps=args.timesteps
    )
    
    logger.info(f"✅ Model trained and saved to {model_path}")
    
    # Backtest if trade data provided
    if args.trade_start and args.trade_end and len(trade_data) > 0:
        logger.info("Running backtest...")
        results = trainer.backtest(
            trade_data=trade_data,
            model_path=model_path,
            algorithm=args.algorithm
        )
        
        logger.info("Backtest Results:")
        logger.info(f"  Total Return: {results['total_return']:.2f}%")
        logger.info(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        logger.info(f"  Max Drawdown: {results['max_drawdown']:.2f}%")
        logger.info(f"  Final Value: ₹{results['final_value']:,.2f}")


if __name__ == "__main__":
    main()


