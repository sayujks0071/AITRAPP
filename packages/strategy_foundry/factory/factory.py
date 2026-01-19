"""Strategy Factory for Deserialization"""
import re

from .generator import StrategyCandidate
from .grammar import RSIReversionRule, StopLossRule, SupertrendRule, TrendFollowingRule


class StrategyFactory:
    @staticmethod
    def from_dict(data: dict) -> StrategyCandidate:
        entry_desc = data.get('entry', '')
        exit_desc = data.get('exit', '')
        stop_desc = data.get('stop', '')

        entry = StrategyFactory._parse_rule(entry_desc)
        exit_rule = StrategyFactory._parse_rule(exit_desc)
        stop = StrategyFactory._parse_stop(stop_desc)

        return StrategyCandidate(entry, exit_rule, stop)

    @staticmethod
    def _parse_rule(desc: str):
        # Regex parsing of descriptions
        # "EMA Crossover (10, 20)"
        m = re.match(r"EMA Crossover \((\d+), (\d+)\)", desc)
        if m:
            return TrendFollowingRule(int(m.group(1)), int(m.group(2)))

        # "Supertrend (10, 3.0)"
        m = re.match(r"Supertrend \((\d+), ([\d.]+)\)", desc)
        if m:
            return SupertrendRule(int(m.group(1)), float(m.group(2)))

        # "RSI Reversion (14: <30 buy, >70 sell)"
        m = re.match(r"RSI Reversion \((\d+): <(\d+) buy, >(\d+) sell\)", desc)
        if m:
            return RSIReversionRule(int(m.group(1)), int(m.group(2)), int(m.group(3)))

        raise ValueError(f"Unknown rule format: {desc}")

    @staticmethod
    def _parse_stop(desc: str):
        # "ATR Stop (14, 2.0x)"
        m = re.match(r"ATR Stop \((\d+), ([\d.]+)x\)", desc)
        if m:
            return StopLossRule(int(m.group(1)), float(m.group(2)))
        raise ValueError(f"Unknown stop format: {desc}")
