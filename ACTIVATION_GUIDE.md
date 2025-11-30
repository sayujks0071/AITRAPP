# 🚀 The Cortex - Activation Guide

## ✅ Level 5 System: ACTIVE

**The Cortex** is fully implemented and ready for production use. Your trading bot now has **autonomous self-evolution capabilities**.

---

## 🎯 Quick Activation

### Step 1: Verify Prerequisites

```bash
# Check that config file exists
ls -la configs/kite_day1_live.yaml

# Check that logs directory exists (will be created automatically)
mkdir -p logs

# Verify Cortex can be imported
python3 -c "from packages.core.intelligence import Cortex; print('✅ Cortex ready')"
```

### Step 2: Test with Dry Run

```bash
# Run dry run to see what would happen
python3 scripts/run_evolution_cycle.py --use-cortex --dry-run
```

**Expected Output:**
- If logs exist: Shows metrics and what patches would be applied
- If logs don't exist: Gracefully handles missing log file

### Step 3: Schedule Daily Automation

Add to crontab to run daily at 4:05 PM IST (after market close):

```bash
# Edit crontab
crontab -e

# Add this line (adjust path as needed)
5 16 * * * cd /path/to/AITRAPP && /usr/bin/python3 scripts/run_evolution_cycle.py --use-cortex >> logs/evolution.log 2>&1
```

---

## 📋 How It Works

### Daily Evolution Cycle

Every day after market close, The Cortex:

1. **OBSERVE** - Parses `logs/trading.log` to extract:
   - Number of entries
   - Rejection patterns
   - Market regime
   - Win rate
   - Other metrics

2. **ORIENT** - Retrieves relevant past episodes from RAG Memory:
   - Finds similar market regimes
   - Reviews historical performance
   - Builds context

3. **DECIDE** - AI Analyst analyzes:
   - Compares current metrics with history
   - Identifies patterns (e.g., too many rejections)
   - Generates config patch suggestions

4. **ACT** - Applies evolution:
   - Updates config YAML safely
   - Records episode in RAG Memory
   - Logs all changes

---

## 🔍 Monitoring

### Check Evolution Logs

```bash
# View evolution log
tail -f logs/evolution.log

# Check for recent evolution cycles
grep "CORTEX" logs/evolution.log | tail -10
```

### View RAG Memory

```bash
# Check stored episodes
python3 << 'EOF'
from packages.core.rag_memory import RAGMemory

memory = RAGMemory()
episodes = memory.get_all_episodes(limit=10)

print(f"📚 Stored Episodes: {len(episodes)}")
for ep in episodes:
    print(f"   {ep['date']}: PnL=₹{ep['pnl']:.2f}, Regime={ep['dominant_regime']}")
    if ep.get('config_snapshot'):
        print(f"      Patches: {ep['config_snapshot']}")
EOF
```

### Check Config Changes

```bash
# View config file
cat configs/kite_day1_live.yaml

# Check git diff (if using version control)
git diff configs/kite_day1_live.yaml
```

---

## ⚠️ Important Notes

### Log File Requirements

The Cortex needs `logs/trading.log` with trading activity. Ensure your trading system is writing logs in this format:

```
2025-11-20 09:15:00 [INFO] Position Secured: NIFTY 25000 CE
2025-11-20 09:30:00 [INFO] Skipping: WEAK_TREND
2025-11-20 10:00:00 [INFO] Regime: LOW_MEAN_REVERT
```

### Activity Threshold

Evolution is **skipped** if:
- No log file exists
- `entries + rejections = 0` (no activity)

This prevents noise from empty days.

### Dry Run Safety

Currently, `--dry-run` mode still calls `perform_eod_analysis()`, which may write files. For true dry-run safety, consider:
- Extending `AIAnalyst` to accept a `dry_run` flag
- Or manually backing up config before running

---

## 🎉 Success Indicators

### After First Evolution Cycle

You should see:

1. **Config Changes**: YAML file updated with new parameter values
2. **RAG Memory**: New episode stored with today's metrics
3. **Evolution Log**: Entry in `logs/evolution.log` showing what changed

### Example First Evolution

```
Day 1:
- Logs: 2 entries, 12 rejections (WEAK_TREND: 8)
- Cortex: Relaxes ADX threshold 22.0 → 20.0
- Result: Config evolved, episode stored

Day 2:
- Logs: 8 entries, 4 rejections (improved!)
- Cortex: No changes needed (system working well)
- Result: Episode stored for future reference
```

---

## 🔧 Troubleshooting

### Issue: "Log file not found"

**Solution:**
- Ensure trading system is writing to `logs/trading.log`
- Check file permissions
- Verify log path in Cortex initialization

### Issue: "No significant activity"

**Solution:**
- This is normal if no trading occurred
- Evolution is skipped to prevent noise
- System will evolve on active trading days

### Issue: Config not updating

**Solution:**
- Check file permissions on config YAML
- Verify config path is correct
- Check for errors in `logs/evolution.log`

---

## 📊 System Status

**Current Capabilities:**

- ✅ **Perception**: Log parsing operational
- ✅ **Memory**: RAG Memory storing episodes
- ✅ **Cognition**: AI Analyst generating patches
- ✅ **Evolution**: Config patching working
- ✅ **Automation**: Cron-ready

**Next Evolution:**

The system will automatically:
- Learn from each trading day
- Identify patterns in rejections
- Adjust parameters based on performance
- Build historical context
- Improve over time

---

## 🎯 Summary

**The Cortex is ACTIVE and ready to evolve your trading system!**

1. ✅ Implementation complete
2. ✅ Architecture verified
3. ✅ OODA loop operational
4. ✅ CLI interface working
5. ✅ Ready for automation

**Your trading bot now evolves autonomously every day!** 🚀

---

**To activate:** Run the dry run, then schedule the cron job. The system will start evolving automatically after each trading day.





