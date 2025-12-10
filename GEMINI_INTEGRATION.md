# 🤖 Gemini LLM Integration - The Cortex

## ✅ Integration Complete

**Gemini API** has been integrated into The Cortex's AI Analyst for advanced reasoning capabilities.

---

## 🔑 Setup

### 1. API Key Added

The Gemini API key has been added to `.env`:
```bash
GEMINI_API_KEY=AIzaSyAvtzNWzYWa7gAnMrPnF_mW5CoOsShxZR4
```

### 2. Install Dependencies

```bash
pip install google-generativeai
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

---

## 🚀 How It Works

### Automatic Fallback

The AI Analyst now supports **two modes**:

1. **LLM Mode (Gemini)** - When `GEMINI_API_KEY` is set and `google-generativeai` is installed
2. **Heuristic Mode** - Fallback when LLM is unavailable

### Mode Selection

```python
# Automatically detects and uses best available:
analyst = AIAnalyst(config_path="configs/kite_day1_live.yaml", memory=memory)

# If GEMINI_API_KEY is set:
# ✅ Uses Gemini for advanced reasoning

# If GEMINI_API_KEY is not set:
# ✅ Falls back to heuristic rules
```

---

## 📊 LLM Reasoning Process

### 1. Prompt Building

The LLM receives:
- **Today's Metrics**: PnL, win rate, rejections, regime
- **Historical Context**: Similar past episodes from RAG Memory
- **Task**: Suggest config parameter adjustments

### 2. LLM Analysis

Gemini analyzes:
- Rejection patterns
- Performance trends
- Historical comparisons
- Market regime context

### 3. Response Parsing

LLM returns JSON:
```json
{
  "config_patches": {
    "strategies.trend_credit_spread.adx_threshold": 20.0,
    "risk.per_trade_risk_pct": 0.20
  },
  "reasoning": "Too many WEAK_TREND rejections. Historical data shows lower ADX worked well in LOW_MEAN_REVERT regime."
}
```

### 4. Config Updates

Patches are applied to `configs/kite_day1_live.yaml` automatically.

---

## 🔍 Verification

### Check LLM Status

```python
from packages.core.intelligence import AIAnalyst
from packages.core.rag_memory import RAGMemory

memory = RAGMemory()
analyst = AIAnalyst("configs/kite_day1_live.yaml", memory)

if analyst.llm_enabled:
    print("✅ LLM Mode: Active (Gemini)")
else:
    print("ℹ️  Heuristic Mode: Active (LLM not available)")
```

### Test LLM Integration

```bash
# Run evolution cycle (will use LLM if available)
python3 scripts/run_evolution_cycle.py --use-cortex --dry-run
```

**Expected Output (LLM Mode):**
```
✅ Gemini API configured - LLM reasoning enabled
🧠 CORTEX: Initiating Evolution Cycle
📊 Observed: 15 Entries, Regime: LOW_MEAN_REVERT
🤖 LLM-generated suggestions
🤖 LLM Reasoning: Too many WEAK_TREND rejections...
🧬 Evolving: strategies.trend_credit_spread.adx_threshold 22.0 -> 20.0
```

**Expected Output (Heuristic Mode):**
```
Using heuristic-based analysis (GEMINI_API_KEY not set)
🧠 CORTEX: Initiating Evolution Cycle
📊 Observed: 15 Entries, Regime: LOW_MEAN_REVERT
💡 Insight: Trend filter too strict. Relaxing ADX.
🧬 Evolving: strategies.trend_credit_spread.adx_threshold 22.0 -> 20.0
```

---

## ⚙️ Configuration

### Enable/Disable LLM

**Enable:**
```bash
# Set in .env
GEMINI_API_KEY=your_api_key_here
```

**Disable:**
```bash
# Remove or comment out in .env
# GEMINI_API_KEY=
```

### API Key Security

⚠️ **Important:** 
- Never commit `.env` to version control
- Keep API key secure
- Rotate keys periodically
- Use environment-specific keys for dev/prod

---

## 🐛 Troubleshooting

### Issue: "google-generativeai not installed"

**Solution:**
```bash
pip install google-generativeai
```

### Issue: "Failed to configure Gemini API"

**Solution:**
- Verify API key is correct
- Check API key has proper permissions
- Ensure internet connection for API calls

### Issue: "LLM generation failed, falling back to heuristics"

**Solution:**
- Check API quota/limits
- Verify API key is valid
- Check network connectivity
- System will automatically use heuristics as fallback

---

## 📈 Benefits

### LLM Mode Advantages

- ✅ **Advanced Reasoning**: Understands complex patterns
- ✅ **Context Awareness**: Considers historical episodes
- ✅ **Nuanced Decisions**: Beyond simple rule matching
- ✅ **Adaptive Learning**: Learns from patterns over time

### Heuristic Mode Advantages

- ✅ **No API Costs**: Free to run
- ✅ **Fast**: No network latency
- ✅ **Reliable**: No API dependency
- ✅ **Predictable**: Rule-based logic

---

## 🎯 Summary

**Gemini LLM Integration Status:**

- ✅ API Key: Added to `.env`
- ✅ Dependencies: Added to `requirements.txt`
- ✅ Code Integration: Complete
- ✅ Fallback Logic: Implemented
- ✅ Error Handling: Robust

**The Cortex now has true AI reasoning capabilities!** 🚀

---

**Next Steps:**
1. Install dependencies: `pip install google-generativeai`
2. Test with dry-run: `python3 scripts/run_evolution_cycle.py --use-cortex --dry-run`
3. Monitor LLM usage and costs
4. Review LLM-generated suggestions before applying





