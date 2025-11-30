# FinRL Integration with AITRAPP

## Overview

FinRL (Financial Reinforcement Learning) has been integrated into the AITRAPP trading system as a new strategy type. This allows you to use Deep Reinforcement Learning (DRL) agents to generate trading signals.

## Components

### 1. FinRLStrategy (`packages/core/strategies/finrl_strategy.py`)
- Main strategy class that implements the AITRAPP Strategy interface
- Uses trained FinRL DRL models to generate trading signals
- Supports multiple algorithms: PPO, A2C, DDPG, TD3, SAC
- Converts AITRAPP market data to FinRL format

### 2. FinRLTrainer (`packages/core/strategies/finrl_trainer.py`)
- Training utility for FinRL models
- Supports data preparation, model training, and backtesting
- Can be used to train custom models for your trading strategies

### 3. Training Script (`scripts/train_finrl.py`)
- Command-line tool for training FinRL models
- Handles data preparation, training, and backtesting

### 4. Configuration (`configs/finrl_strategy.yaml`)
- YAML configuration file for FinRL strategy
- Configures model path, algorithm, and trading parameters

## Setup

### 1. Install Dependencies

FinRL dependencies should already be installed. If not:

```bash
cd FinRL
pip3 install -r requirements.txt
```

### 2. Prepare Training Data

You need historical OHLCV data in CSV format with columns:
- `date`: Date/timestamp
- `open`, `high`, `low`, `close`: OHLC prices
- `volume`: Trading volume
- `tic`: Ticker symbol

Example:
```csv
date,open,high,low,close,volume,tic
2020-01-01,100.0,102.0,99.0,101.0,1000000,NIFTY
2020-01-02,101.0,103.0,100.0,102.0,1100000,NIFTY
...
```

### 3. Train a Model

```bash
python scripts/train_finrl.py \
    --data data/stock_data.csv \
    --algorithm PPO \
    --train-start 2020-01-01 \
    --train-end 2023-12-31 \
    --trade-start 2024-01-01 \
    --trade-end 2024-12-31 \
    --output models/finrl_ppo.zip \
    --timesteps 100000
```

### 4. Configure Strategy

Edit `configs/finrl_strategy.yaml`:

```yaml
finrl_strategy:
  enabled: true
  priority: 50
  model_path: "models/finrl_ppo.zip"
  algorithm: "PPO"
  lookback_window: 30
  min_confidence: 0.6
  max_positions: 2
```

### 5. Enable in Main Config

Add to your main config file (e.g., `configs/kite_day1_live.yaml`):

```yaml
strategies:
  - name: FinRLStrategy
    enabled: true
    priority: 50
```

## Usage

### Training Models

1. **Collect Historical Data**: Gather OHLCV data for your instruments
2. **Train Model**: Use `train_finrl.py` script
3. **Backtest**: Script automatically runs backtest after training
4. **Deploy**: Update config and enable strategy

### Running Strategy

Once configured and enabled, the FinRL strategy will:
1. Load the trained model on startup
2. Convert incoming market data to FinRL format
3. Generate trading signals based on model predictions
4. Submit signals to the AITRAPP execution engine

### Monitoring

- Check logs for model loading status
- Monitor signal generation in strategy logs
- Review performance metrics in Prometheus

## Supported Algorithms

- **PPO** (Proximal Policy Optimization): Recommended for most cases
- **A2C** (Advantage Actor-Critic): Faster training
- **DDPG** (Deep Deterministic Policy Gradient): For continuous actions
- **TD3** (Twin Delayed DDPG): Improved DDPG
- **SAC** (Soft Actor-Critic): State-of-the-art performance

## Data Format

FinRL expects data in this format:
- DataFrame with columns: `date`, `open`, `high`, `low`, `close`, `volume`, `tic`
- Technical indicators added automatically
- Data sorted by date

## Integration Points

1. **Strategy Interface**: Implements `Strategy` base class
2. **Market Data**: Uses `StrategyContext` from AITRAPP
3. **Signal Generation**: Returns `Signal` objects compatible with AITRAPP
4. **Execution**: Signals flow through normal AITRAPP execution pipeline

## Limitations

- Requires pre-trained models (no online learning yet)
- Model must match data format (same features/indicators)
- Training requires historical data
- `box2d-py` dependency failed (optional, not critical)

## Next Steps

1. Train models on your specific instruments
2. Backtest thoroughly before live trading
3. Monitor performance and retrain as needed
4. Consider ensemble of multiple algorithms
5. Fine-tune hyperparameters for your use case

## Troubleshooting

### Model Not Loading
- Check `model_path` in config
- Verify model file exists
- Check algorithm matches model type

### No Signals Generated
- Verify `enabled: true` in config
- Check `lookback_window` - need enough historical bars
- Review logs for errors

### Import Errors
- Ensure FinRL is in Python path
- Install missing dependencies
- Check FinRL installation

## References

- [FinRL Documentation](https://finrl.readthedocs.io/)
- [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL)
- [Stable Baselines3](https://stable-baselines3.readthedocs.io/)


