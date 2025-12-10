# 🧠 The Cortex - Quick Start Guide

## ✅ Implementation Complete

**The Cortex** is now fully operational as a Level 5 Self-Evolving Trading System.

---

## 🚀 Quick Start

### 1. Manual Testing (Dry Run)

```bash
# See what The Cortex would change (without applying)
python3 scripts/run_evolution_cycle.py --use-cortex --dry-run
```

**Output:**
```
🧠 CORTEX: Initiating Evolution Cycle (Dry Run: True)
📊 Observed: 5 Entries, Regime: LOW_MEAN_REVERT
📚 Retrieved 3 relevant episodes for regime: LOW_MEAN_REVERT
🧪 DRY RUN MODE: Evolution logic will run but config updates are simulated.
💡 Would apply patches: {'strategies.trend_credit_spread.adx_threshold': 20.0}
✅ CORTEX: Cycle Complete.
```

### 2. Live Evolution (Applies Changes)

```bash
# Run evolution cycle and apply changes
python3 scripts/run_evolution_cycle.py --use-cortex
```

### 3. Daily Automation (Cron)

Add to crontab to run daily at 4:05 PM (after market close):

```bash
# Edit crontab
crontab -e

# Add this line (adjust path as needed)
5 16 * * * cd /path/to/AITRAPP && /usr/bin/python3 scripts/run_evolution_cycle.py --use-cortex >> logs/evolution.log 2>&1
```

---

## 📋 How It Works

### The OODA Loop

The Cortex executes a complete OODA loop:

1. **OBSERVE (Perception)**
   - Parses trading logs
   - Extracts metrics (entries, rejections, regime)
   - Detects patterns

2. **ORIENT (Memory)**
   - Retrieves relevant past episodes from RAG Memory
   - Finds similar market regimes
   - Builds context

3. **DECIDE (Cognition)**
   - AI Analyst analyzes metrics + history
   - Generates config patch suggestions
   - Evaluates impact

4. **ACT (Evolution)**
   - Applies config patches safely
   - Backs up config
   - Records in RAG Memory

---

## 🎯 Example Scenario

### Day 1: Strict Filters

```
Log Analysis:
- Entries: 2
- Rejections: 12 (WEAK_TREND: 8, MARGIN_LIMIT: 4)
- Regime: LOW_MEAN_REVERT
- Win Rate: 60%

Cortex Analysis:
- Too many WEAK_TREND rejections
- Historical episodes show: Lower ADX worked well in LOW_MEAN_REVERT
- Suggestion: Relax ADX threshold 22.0 → 20.0

Action:
✅ Config updated: strategies.trend_credit_spread.adx_threshold = 20.0
💾 Episode stored in RAG Memory
```

### Day 2: Improved Performance

```
Log Analysis:
- Entries: 8 (increased!)
- Rejections: 4 (reduced!)
- Regime: LOW_MEAN_REVERT
- Win Rate: 65%

Cortex Analysis:
- ADX relaxation worked
- No changes needed
- Episode stored for future reference
```

---

## 📊 Monitoring

### Check Cortex Status

```python
from packages.core.intelligence import Cortex

cortex = Cortex(
    config_path="configs/kite_day1_live.yaml",
    log_path="logs/trading.log"
)

status = cortex.get_cortex_status()
print(f"Memory Episodes: {status['memory_episodes']}")
print(f"Avg PnL: ₹{status['avg_pnl']:.2f}")
print(f"Avg Win Rate: {status['avg_win_rate']:.1%}")
```

### View Evolution History

```bash
# Check RAG Memory
python3 << 'EOF'
from packages.core.rag_memory import RAGMemory

memory = RAGMemory()
history = memory.get_all_episodes(limit=10)

for ep in history:
    print(f"{ep['date']}: PnL=₹{ep['pnl']:.2f}, Regime={ep['dominant_regime']}")
    if ep.get('config_snapshot'):
        print(f"  Patches: {ep['config_snapshot']}")
EOF
```

---

## 🔧 Configuration

### Required Files

- **Config File**: `configs/kite_day1_live.yaml` (or custom path)
- **Log File**: `logs/trading.log` (or custom path)
- **Memory File**: `data/memory.json` (auto-created)

### Custom Paths

```bash
python3 scripts/run_evolution_cycle.py \
    --use-cortex \
    --config-path configs/custom.yaml \
    --log-path logs/custom.log \
    --memory-path data/custom_memory.json
```

---

## ⚠️ Important Notes

1. **Log File Required**: The Cortex needs trading logs to analyze. Ensure logs are being written.

2. **Activity Threshold**: If no significant activity (entries + rejections = 0), evolution is skipped.

3. **Dry Run First**: Always test with `--dry-run` before running live.

4. **Config Backup**: Last stable config is always backed up before changes.

5. **Reversible**: All changes can be reverted using config backup.

---

## 🎉 Summary

**The Cortex** is now operational:

- ✅ **Perception**: LogParser extracts metrics
- ✅ **Memory**: RAG Memory stores episodes
- ✅ **Cognition**: AI Analyst proposes changes
- ✅ **Evolution**: Config patches applied safely
- ✅ **Automation**: Ready for cron scheduling

**Your trading system now evolves autonomously!** 🚀

---

## 📚 Related Documentation

- `THE_CORTEX_IMPLEMENTATION.md` - Full technical documentation
- `SELF_HEALING_IMPLEMENTATION.md` - Self-healing system
- `ORCHESTRATOR_SELF_HEALING_INTEGRATION.md` - Orchestrator integration





