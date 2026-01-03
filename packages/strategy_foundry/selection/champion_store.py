import json
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from packages.strategy_foundry.factory.grammar import StrategyCandidate, Rule

CHAMPION_DIR = os.path.join(os.path.dirname(__file__), "../results/champions")

def ensure_champion_dir():
    os.makedirs(CHAMPION_DIR, exist_ok=True)

def get_champion_path(instrument: str) -> str:
    return os.path.join(CHAMPION_DIR, f"champion_{instrument}.json")

def load_champion(instrument: str) -> Optional[Dict[str, Any]]:
    path = get_champion_path(instrument)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_champion(candidate: StrategyCandidate, metrics: Dict[str, Any], score: float, instrument: str):
    ensure_champion_dir()

    data = candidate.to_json()
    data["metrics"] = metrics
    data["score"] = score
    data["instrument"] = instrument
    data["timestamp"] = datetime.now().isoformat()

    # Save as current for instrument
    with open(get_champion_path(instrument), "w") as f:
        json.dump(data, f, indent=2)

    # Archive
    archive_name = f"{datetime.now().strftime('%Y%m%d%H%M')}_{instrument}_{candidate.strategy_id}.json"
    archive_path = os.path.join(CHAMPION_DIR, archive_name)
    with open(archive_path, "w") as f:
        json.dump(data, f, indent=2)

def reconstruct_strategy(data: Dict[str, Any]) -> StrategyCandidate:
    """Reconstruct StrategyCandidate from JSON data"""
    from packages.strategy_foundry.factory.generator import (
        rule_ema_cross, rule_supertrend_long, rule_rsi_entry, rule_rsi_exit,
        rule_adx_filter, rule_regime_filter, rule_donchian_breakout
    )

    func_map = {
        "EMA_Cross": rule_ema_cross,
        "Supertrend_Bull": rule_supertrend_long,
        "RSI_Oversold": rule_rsi_entry,
        "RSI_Overbought": rule_rsi_exit,
        "ADX_Filter": rule_adx_filter,
        "Regime_Filter": rule_regime_filter,
        "Donchian_Breakout": rule_donchian_breakout
    }

    entry_rules = []
    for r in data["entry"]:
        if r["name"] in func_map:
            entry_rules.append(Rule(r["name"], func_map[r["name"]], r["params"]))

    exit_rules = []
    for r in data["exit"]:
        if r["name"] in func_map:
            exit_rules.append(Rule(r["name"], func_map[r["name"]], r["params"]))

    return StrategyCandidate(
        strategy_id=data["id"],
        entry_rules=entry_rules,
        exit_rules=exit_rules,
        risk_params=data["risk"]
    )
