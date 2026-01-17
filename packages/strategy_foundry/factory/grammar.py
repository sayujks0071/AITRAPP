from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass, field, asdict

class Operator(str, Enum):
    GT = ">"
    LT = "<"
    CROSS_UP = "cross_up"
    CROSS_DOWN = "cross_down"
    BETWEEN = "between"

@dataclass
class IndicatorDef:
    name: str
    params: Dict[str, Any]

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

@dataclass
class Condition:
    indicator_a: IndicatorDef
    operator: Operator
    indicator_b: Any  # IndicatorDef or scalar
    param_override: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        d = {
            "indicator_a": self.indicator_a.to_dict(),
            "operator": self.operator.value,
            "param_override": self.param_override
        }
        if isinstance(self.indicator_b, IndicatorDef):
            d["indicator_b"] = self.indicator_b.to_dict()
            d["indicator_b_type"] = "indicator"
        else:
            d["indicator_b"] = self.indicator_b
            d["indicator_b_type"] = "scalar"
        return d

    @classmethod
    def from_dict(cls, data):
        ind_a = IndicatorDef.from_dict(data["indicator_a"])
        op = Operator(data["operator"])

        if data.get("indicator_b_type") == "indicator":
            ind_b = IndicatorDef.from_dict(data["indicator_b"])
        else:
            ind_b = data["indicator_b"]

        return cls(
            indicator_a=ind_a,
            operator=op,
            indicator_b=ind_b,
            param_override=data.get("param_override", {})
        )

@dataclass
class StrategyRule:
    entry_conditions: List[Condition]
    exit_conditions: List[Condition]
    risk_params: Dict[str, Any]
    description: str = ""

    def to_dict(self):
        return {
            "entry_conditions": [c.to_dict() for c in self.entry_conditions],
            "exit_conditions": [c.to_dict() for c in self.exit_conditions],
            "risk_params": self.risk_params,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            entry_conditions=[Condition.from_dict(c) for c in data.get("entry_conditions", [])],
            exit_conditions=[Condition.from_dict(c) for c in data.get("exit_conditions", [])],
            risk_params=data.get("risk_params", {}),
            description=data.get("description", "")
        )

@dataclass
class StrategyCandidate:
    id: str
    rule: StrategyRule
    timeframe: str
    source_code: str = ""
