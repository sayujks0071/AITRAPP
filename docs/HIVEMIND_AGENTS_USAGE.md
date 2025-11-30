# HiveMind Agents - Usage Guide

## Overview

The AITRAPP system now includes two new HiveMind agents built on the `BaseAgent` framework:

1. **CortexAnalyst** - Post-trade daily reviewer
2. **SG1StrategyGenerator** - Config tuning suggestions

Both agents use OpenAI (GPT-5 with GPT-4o fallback) and provide structured JSON outputs.

---

## 1. CortexAnalyst

### Purpose
Analyzes daily trading performance and provides structured insights for portfolio management decisions.

### Input Context Schema
```python
{
    "date": "2025-11-21",
    "pnl": {
        "day": 1200.5,
        "max_dd": -3500.0,
        "by_strategy": {
            "intraday_short_strangle": {...},
            "trend_credit_spread": {...}
        }
    },
    "trades": [...],
    "regime": {
        "NIFTY": {"regime": "LOW_MEAN_REVERT", "iv_rank": 32.1}
    },
    "execution": {
        "limit_chase": {
            "total_saves_rs": 780.0,
            "timeouts": 2,
            "slippage_stops": 1
        }
    },
    "filters": {
        "options_ranker": {
            "setups_evaluated": 14,
            "rejections": {
                "WEAK_TREND": 5,
                "LIQUIDITY": 3,
                "RISK_CAP": 2
            }
        }
    }
}
```

### Output Schema
```json
{
    "summary": "1–3 sentence narrative of the day.",
    "issues": ["short bullet issues detected today"],
    "risk_flags": ["items that threaten capital if ignored"],
    "config_tweaks": [
        "very concrete small tweaks, e.g. 'raise ADX threshold for trend_credit_spread from 22 to 25'"
    ],
    "focus_areas_tomorrow": [
        "what to watch or collect more data on tomorrow"
    ],
    "confidence": 0.86
}
```

### Usage Example
```python
from packages.core.intelligence.analyst import CortexAnalyst
import json

# Build your daily context
context = {
    "date": "2025-11-21",
    "pnl": {"day": 1200.5},
    "trades": [],
    "regime": {"NIFTY": {"regime": "LOW_MEAN_REVERT"}},
    "execution": {"limit_chase": {"total_saves_rs": 780.0}},
    "filters": {"options_ranker": {"rejections": {"WEAK_TREND": 5}}}
}

# Run analysis
analyst = CortexAnalyst()
analysis = analyst.think(context)

print(json.dumps(analysis, indent=2))
```

---

## 2. SG1StrategyGenerator

### Purpose
Proposes small, reversible config changes based on performance analysis. Focuses on safe, incremental improvements.

### Input Context Schema
```python
{
    "date": "2025-11-21",
    "strategies": {
        "intraday_short_strangle": {
            "trades": {...},
            "win_rate": 0.55,
            "avg_rr": 1.4,
            "streak": -2,
            "config": {...}
        },
        "trend_credit_spread": {
            "trades": {...},
            "win_rate": 0.40,
            "avg_rr": 0.8,
            "streak": -4,
            "config": {...}
        }
    },
    "regimes": {...},
    "execution": {...}
}
```

### Output Schema
```json
{
    "summary": "short description of what you want to change and why",
    "proposed_changes": [
        {
            "path": "strategies.intraday_short_strangle.adx_threshold",
            "old_value": 22.0,
            "new_value": 25.0,
            "reason": "short explanation tied to observed stats",
            "priority": "HIGH"
        }
    ],
    "changes_safe_to_apply_automatically": false,
    "notes": [
        "optional caveats or 'need more data' comments"
    ]
}
```

### Usage Example
```python
from packages.core.intelligence.sg1 import SG1StrategyGenerator
import json

# Build your strategy performance context
context = {
    "date": "2025-11-21",
    "strategies": {
        "intraday_short_strangle": {
            "win_rate": 0.55,
            "avg_rr": 1.4,
            "streak": -2
        },
        "trend_credit_spread": {
            "win_rate": 0.40,
            "avg_rr": 0.8,
            "streak": -4
        }
    }
}

# Get tuning suggestions
sg1 = SG1StrategyGenerator()
plan = sg1.think(context)

print(json.dumps(plan, indent=2))

# Optionally save to file for review
with open("reports/tuning/2025-11-21_SG1_PLAN.json", "w") as f:
    json.dump(plan, f, indent=2)
```

---

## Integration with Daily Flow

### End-of-Day Routine

```python
from packages.core.intelligence.analyst import CortexAnalyst
from packages.core.intelligence.sg1 import SG1StrategyGenerator
import json
from datetime import datetime

# 1. Build daily context (from your existing metrics collection)
daily_context = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "pnl": {...},  # From your PnL tracker
    "trades": [...],  # From your trade log
    "regime": {...},  # From RegimeVolEngine
    "execution": {...},  # From ExecutionEngine
    "filters": {...}  # From OptionsRanker
}

# 2. Run Cortex Analysis
cortex = CortexAnalyst()
cortex_out = cortex.think(daily_context)

# 3. Run SG-1 Tuning
sg1 = SG1StrategyGenerator()
sg1_out = sg1.think(daily_context)

# 4. Append to daily report
report = f"""
# Daily Report - {daily_context['date']}

## HiveMind – Cortex Analyst
{json.dumps(cortex_out, indent=2)}

## HiveMind – SG-1 Tuning Suggestions
{json.dumps(sg1_out, indent=2)}
"""

with open(f"reports/{daily_context['date']}_FINAL_REPORT.md", "w") as f:
    f.write(report)
```

---

## Configuration

Both agents respect these environment variables:

- `HIVEMIND_MODEL` - Model name (default: `gpt-5`)
- `HIVEMIND_TEMPERATURE` - Temperature (default: `0.1`)
- `HIVEMIND_MAX_TOKENS` - Max tokens (default: `800`)
- `OPENAI_API_KEY` - Required for LLM features

### Example `.env`:
```bash
OPENAI_API_KEY=sk-proj-...
HIVEMIND_MODEL=gpt-5
HIVEMIND_TEMPERATURE=0.1
HIVEMIND_MAX_TOKENS=800
```

---

## Fallback Behavior

If OpenAI API is unavailable or misconfigured, both agents fall back to heuristic logic:

- **CortexAnalyst**: Returns basic summary with PnL and generic recommendations
- **SG1StrategyGenerator**: Returns conservative sizing adjustments based on win rate and streak

---

## Notes

- Both agents enforce **strict JSON output** via `response_format={"type": "json_object"}`
- All changes suggested by SG-1 are **small, reversible, and safe**
- SG-1 will **never suggest leverage increases** or removal of risk limits
- Changes are marked with `changes_safe_to_apply_automatically` flag for manual review

---

## Next Steps

To apply SG-1's suggested changes to your config:

1. Review the `proposed_changes` array
2. If `changes_safe_to_apply_automatically` is `true`, you can auto-apply
3. Otherwise, manually review each change
4. Use a YAML patching script to apply approved changes

A future enhancement will include an automated YAML patcher that converts `proposed_changes` into actual config updates.




