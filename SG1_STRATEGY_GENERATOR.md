# 🤖 SG-1 (Strategy Generator 1) - Level 6 Self-Replicating System

## ✅ Implementation Complete

**SG-1** is an autonomous agent that generates brand new trading strategies using AI, moving your system from **Level 5 (Self-Optimizing)** to **Level 6 (Self-Replicating)**.

---

## 🎯 What is SG-1?

SG-1 autonomously:

1. **Ideates:** Analyzes RAG Memory to find market regimes where current strategies fail
2. **Codes:** Uses Gemini LLM to write brand new Python strategy files
3. **Validates:** Performs AST-based safety checks to prevent malicious code
4. **Deploys:** Saves strategies to `generated/` folder for review/testing

---

## 🚀 Quick Start

### Prerequisites

1. **Gemini API Key** (required):
   ```bash
   # In .env file
   GEMINI_API_KEY=your_api_key_here
   ```

2. **Dependencies**:
   ```bash
   pip install google-generativeai
   ```

### Generate a Strategy

```bash
# Auto-ideate worst-performing regime
python3 scripts/run_sg1.py

# Target specific regime
python3 scripts/run_sg1.py --regime "SIDEWAYS_CHOP"
```

**Output:**
```
🤖 SG-1 STRATEGY GENERATOR
============================================================
💡 Target Regime: SIDEWAYS_CHOP
💡 Problem: Strategies lose money in SIDEWAYS_CHOP regime
🤖 SG-1: Generating strategy code...
✅ SG-1: Strategy code generated successfully
🔒 SG-1: Validating generated code...
✅ SG-1: Code validation passed
📦 SG-1: Deploying strategy...
✅ SG-1: Strategy deployed to packages/core/strategies/generated/sg1_sideways_chop_20251120_2345.py
```

---

## 📋 How It Works

### Step 1: Ideate

SG-1 analyzes RAG Memory to find:
- **Worst-performing regimes** (if no regime specified)
- **Specific regime** (if `--regime` provided)
- **Historical episodes** for context

**Example:**
```
Regime: SIDEWAYS_CHOP
Problem: Strategies lose money in this regime (avg PnL: ₹-2000.00)
Episodes: 5 historical episodes with similar regime
```

### Step 2: Code

Gemini LLM generates a complete Python strategy class:
- Inherits from `Strategy` base class
- Implements `generate_signals()` method
- Implements `validate()` method
- Uses safe imports only
- Includes proper error handling

**Prompt includes:**
- Target regime
- Problem statement
- Historical context
- Strategy requirements
- Example structure

### Step 3: Validate

AST-based safety checks:
- ✅ No forbidden imports (`os`, `sys`, `subprocess`, etc.)
- ✅ No dangerous functions (`exec`, `eval`, `open`)
- ✅ Valid Python syntax
- ✅ Implements Strategy interface

### Step 4: Deploy

Saves validated code to:
```
packages/core/strategies/generated/sg1_{regime}_{timestamp}.py
```

---

## 🔒 Safety Features

### Code Safety Inspector

**Blocks:**
- System calls (`os`, `sys`, `subprocess`)
- File I/O (`open`, file operations)
- Network calls (`requests`, `urllib`, `socket`)
- Dangerous built-ins (`exec`, `eval`, `compile`)

**Allows:**
- Data processing (`pandas`, `numpy`)
- Technical indicators (`pandas_ta`)
- Standard libraries (`datetime`, `typing`, `math`)
- Strategy framework imports

### Validation Process

1. **AST Parsing:** Validates Python syntax
2. **Import Check:** Blocks forbidden imports
3. **Function Check:** Blocks dangerous function calls
4. **Interface Check:** Verifies Strategy inheritance

### Human Review Required

**SG-1 generates code but does NOT execute it.**

Generated strategies:
- ✅ Saved to `generated/` folder
- ✅ Require human review
- ✅ Must be tested in backtest mode
- ✅ Must be approved before live deployment

---

## 📁 Generated Files

### Location

```
packages/core/strategies/generated/
├── README.md
├── sg1_sideways_chop_20251120_2345.py
├── sg1_low_vol_20251121_1015.py
└── ...
```

### File Naming

Format: `sg1_{regime}_{timestamp}.py`

Example: `sg1_sideways_chop_20251120_2345.py`

### File Structure

Generated strategies follow this structure:

```python
from packages.core.strategies.base import Strategy, StrategyContext
from packages.core.models import Signal, SignalSide
from typing import List
import pandas as pd
import numpy as np

class GeneratedStrategy(Strategy):
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        # Initialize indicators, parameters, etc.
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        # Generate trading signals based on context
        signals = []
        # ... trading logic ...
        return signals
    
    def validate(self, context: StrategyContext) -> bool:
        # Validate if strategy can run
        if not super().validate(context):
            return False
        # ... additional validation ...
        return True
```

---

## 🔧 Usage Examples

### Example 1: Auto-Ideation

```bash
python3 scripts/run_sg1.py
```

**What happens:**
1. Analyzes all episodes in RAG Memory
2. Finds worst-performing regime
3. Generates strategy for that regime

### Example 2: Target Specific Regime

```bash
python3 scripts/run_sg1.py --regime "LOW_VOL"
```

**What happens:**
1. Targets LOW_VOL regime specifically
2. Retrieves relevant historical episodes
3. Generates strategy optimized for LOW_VOL

### Example 3: Custom Memory Path

```bash
python3 scripts/run_sg1.py --regime "HIGH_VOL" --memory-path "data/custom_memory.json"
```

---

## 📊 Integration with The Cortex

### Workflow

```
The Cortex (Level 5)
    ↓
RAG Memory stores episodes
    ↓
SG-1 (Level 6) analyzes failures
    ↓
Generates new strategies
    ↓
Human review & testing
    ↓
Deploy to production
```

### Example Scenario

**Day 1-10:**
- Trading system runs
- The Cortex evolves configs
- RAG Memory stores episodes

**Day 11:**
- SG-1 analyzes: "SIDEWAYS_CHOP regime losing money"
- Generates: `sg1_sideways_chop_strategy.py`
- Human reviews and backtests

**Day 12:**
- Strategy approved
- Added to config YAML
- Deployed to live trading

---

## ⚠️ Important Notes

### Safety First

1. **Never auto-execute** generated code
2. **Always review** before testing
3. **Backtest thoroughly** before live deployment
4. **Monitor closely** after deployment

### LLM Limitations

- Generated code may need refinement
- Logic may not be optimal initially
- Requires human expertise to validate
- May need parameter tuning

### Best Practices

1. **Review generated code** line by line
2. **Test in paper trading** first
3. **Start with small position sizes**
4. **Monitor performance closely**
5. **Iterate and improve**

---

## 🐛 Troubleshooting

### Issue: "GEMINI_API_KEY not set"

**Solution:**
```bash
# Add to .env file
GEMINI_API_KEY=your_api_key_here
```

### Issue: "google-generativeai not installed"

**Solution:**
```bash
pip install google-generativeai
```

### Issue: "No episodes in RAG Memory"

**Solution:**
- Ensure trading system has been running
- Check that RAG Memory is being populated
- Run The Cortex evolution cycle first

### Issue: "Code validation failed"

**Solution:**
- LLM may have generated unsafe code
- Review the generated code manually
- Re-run generation (may produce different code)

---

## 📈 Future Enhancements

### Planned Features

- [ ] **Auto-Backtest:** Automatically test generated strategies
- [ ] **Performance Scoring:** Rank generated strategies
- [ ] **Multi-Strategy Generation:** Generate multiple variants
- [ ] **Strategy Evolution:** Improve existing strategies
- [ ] **Integration with Orchestrator:** Auto-deploy approved strategies

---

## 🎉 Summary

**SG-1 Status:**

- ✅ **Ideation:** Analyzes RAG Memory for opportunities
- ✅ **Code Generation:** Uses Gemini LLM to write strategies
- ✅ **Safety Validation:** AST-based security checks
- ✅ **Deployment:** Saves to generated/ folder
- ✅ **Human Review:** Required before execution

**Your trading system can now generate new strategies autonomously!** 🚀

---

## 📚 Related Documentation

- `CORTEX_ARCHITECTURE_PHILOSOPHY.md` - Level 5 system architecture
- `GEMINI_INTEGRATION.md` - LLM integration guide
- `CORTEX_ACTIVATION_GUIDE.md` - Cortex operations manual

---

**Level 6: Self-Replicating System - ACTIVE** 🤖✨





