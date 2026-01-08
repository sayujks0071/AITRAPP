
import pytest
import pandas as pd
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import BacktestMetrics

def test_strategy_config_id():
    cfg = StrategyConfig(entry_block="test", entry_params={"a": 1})
    cfg.generate_id()
    assert cfg.id != ""

    cfg2 = StrategyConfig(entry_block="test", entry_params={"a": 1})
    cfg2.generate_id()
    assert cfg.id == cfg2.id

def test_backtest_engine_basic():
    # Create dummy data
    dates = pd.date_range("2024-01-01 09:15", "2024-01-01 15:30", freq="5min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "Open": [100 + i for i in range(len(dates))],
        "High": [105 + i for i in range(len(dates))],
        "Low": [95 + i for i in range(len(dates))],
        "Close": [102 + i for i in range(len(dates))],
        "Volume": [1000] * len(dates)
    }, index=dates)

    cfg = StrategyConfig(
        entry_block="breakout_donchian",
        entry_params={"period": 5},
        exit_block="simple_target_stop",
        exit_params={"rr_ratio": 2.0},
        risk_block="percent_stop",
        risk_params={"pct": 1.0},
        filter_block="none"
    )

    engine = BacktestEngine(df)
    trades, equity = engine.run(cfg)

    # We expect some trades given the trend
    assert isinstance(trades, pd.DataFrame)
    assert isinstance(equity, pd.Series)

def test_metrics_calculation():
    trades = pd.DataFrame([
        {"pnl": 100},
        {"pnl": -50},
        {"pnl": 200}
    ])
    equity = pd.Series([100000, 100100, 100050, 100250], index=pd.date_range("2024-01-01", periods=4))

    metrics = BacktestMetrics.calculate(trades, equity)

    assert metrics['net_profit'] == 250
    assert metrics['total_trades'] == 3
    assert metrics['win_rate'] == 2/3
