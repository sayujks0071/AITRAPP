# 🧠 The HiveMind - Level 7 Multi-Agent Council

## ✅ Implementation Complete

**The HiveMind** is a real-time "Board of Directors" with 7 specialized AI agents that debate, analyze, and vote on every major trading decision.

---

## 🎯 What is The HiveMind?

While **Level 5 (The Cortex)** was a single analyst fixing configs overnight, **Level 7** is a real-time council running inside your server. Seven specialized AI Agents debate, analyze, and vote on every major decision before it happens.

---

## 👥 The Council of Seven

### 1. MarketAgent - "The Eyes"
**Monitors:** Regime, Volatility, News

**Responsibilities:**
- Detect regime shifts
- Monitor volatility levels
- Track market events
- Assess market conditions

**Output:** Regime assessment, volatility level, market quality

### 2. StrategyAgent - "The General"
**Monitors:** Strategy Performance & Signal Quality

**Responsibilities:**
- Track strategy performance
- Assess signal quality
- Identify underperforming strategies
- Recommend strategy adjustments

**Output:** Signal quality, top/underperforming strategies, allocation recommendations

### 3. RiskAgent - "The Shield"
**Monitors:** Drawdown, Delta Skew, Margin

**Responsibilities:**
- Monitor portfolio risk
- Track delta exposure
- Assess margin utilization
- Detect risk emergencies (DEFCON 1-5)

**Output:** DEFCON level, risk status, delta assessment, margin pressure

### 4. ExecutionAgent - "The Sniper"
**Monitors:** Slippage, Fill Rates, Latency

**Responsibilities:**
- Monitor execution quality
- Track slippage
- Assess fill rates
- Monitor latency

**Output:** Execution quality, slippage assessment, fill rate, latency

### 5. AnalystAgent - "The Historian"
**Monitors:** Historical Patterns from RAG Memory

**Responsibilities:**
- Search RAG Memory for similar situations
- Provide historical context
- Identify patterns from past
- Recommend based on history

**Output:** Historical match, similar episodes, historical outcome, patterns

### 6. AllocatorAgent - "The Treasurer"
**Monitors:** Capital Allocation & Position Sizing

**Responsibilities:**
- Calculate optimal position sizes
- Propose capital allocation
- Adjust sizing based on risk/performance
- Recommend strategy weights

**Output:** Recommended allocation, position size multiplier, target strategy

### 7. RefereeAgent - "The Judge"
**Synthesizes:** All inputs into final Binding Directive

**Responsibilities:**
- Synthesize all agent inputs
- Make final decision
- Issue binding directives
- Resolve conflicts

**Output:** Binding directive, rationale, priority, voting summary

---

## 🚀 Usage

### Basic Usage

```bash
# Convene the council (standalone mode)
python3 scripts/run_hivemind.py

# Connect to running orchestrator (live mode)
python3 scripts/run_hivemind.py --live
```

### Expected Output

```
🧠 HIVEMIND: Convening The Council of Seven
============================================================
📊 Phase 1: Agents analyzing context...
   ✅ MarketAgent: PROCEED
   ✅ StrategyAgent: MAINTAIN
   ✅ RiskAgent: REDUCE_SIZE
   ✅ ExecutionAgent: PROCEED
   ✅ AnalystAgent: CAUTION
   ✅ AllocatorAgent: DECREASE
⚖️  Phase 2: RefereeAgent synthesizing...
   ✅ RefereeAgent: CONDITIONAL_APPROVE

📋 HiveMind Council Summary:
   Directive: CONDITIONAL_APPROVE
   Priority: HIGH
   Confidence: 85.0%
============================================================
```

---

## 📊 How It Works

### The Board Meeting Process

1. **Context Building**
   - Extracts current trading state
   - Gathers portfolio risk metrics
   - Collects execution stats
   - Retrieves historical context

2. **Phase 1: Independent Analysis**
   - Each agent (1-6) analyzes context independently
   - Each provides its perspective and recommendation
   - All insights collected

3. **Phase 2: Synthesis**
   - RefereeAgent receives all insights
   - Synthesizes into final decision
   - Issues binding directive

4. **Phase 3: Directive**
   - Final binding directive issued
   - Priority and confidence assigned
   - Rationale provided

### Example Scenario

**Context:**
- Regime: HIGH_VOL
- Net Delta: 120 (High)
- Daily PnL: -0.5%
- Portfolio Heat: 1.8%

**Agent Analysis:**
- **MarketAgent:** "HIGH_VOL regime, proceed with caution"
- **RiskAgent:** "DEFCON 4 - High delta, elevated risk"
- **AnalystAgent:** "Historical episodes show high delta killed account"
- **StrategyAgent:** "Signal quality good, maintain"
- **ExecutionAgent:** "Execution quality excellent"
- **AllocatorAgent:** "Reduce position sizes by 30%"

**RefereeAgent Directive:**
```
Directive: CONDITIONAL_APPROVE
Details: "Approve allocation but cap Trend Strategy due to Risk Warning"
Priority: HIGH
Rationale: "RiskAgent flags DEFCON 4 due to high delta exposure. 
            Historical patterns confirm risk. Reduce sizes but allow trading."
```

---

## 🔧 Integration

### With Orchestrator

The HiveMind can be integrated into the trading loop:

```python
from packages.core.hivemind import HiveMindSwarm

# In orchestrator
swarm = HiveMindSwarm(memory=rag_memory)

# Before major decisions
decision = swarm.convene_council(orchestrator=self)

if decision["binding_directive"]["directive"] == "HALT":
    # Pause trading
    await self.pause_trading()
elif decision["binding_directive"]["directive"] == "REDUCE_SIZE":
    # Reduce position sizes
    position_multiplier = decision["agent_insights"]["AllocatorAgent"]["position_size_multiplier"]
```

### Standalone Mode

Can run independently for analysis:

```bash
python3 scripts/run_hivemind.py
```

---

## 📋 Directive Types

### APPROVE
- All systems go
- Normal operations
- No restrictions

### CONDITIONAL_APPROVE
- Proceed with conditions
- Specific restrictions apply
- Monitor closely

### REDUCE_SIZE
- Reduce position sizes
- Lower allocation
- Maintain trading

### PAUSE
- Temporarily pause
- Review situation
- Resume after review

### HALT
- Stop all trading
- Critical situation
- Manual intervention required

---

## 🎯 DEFCON Levels (RiskAgent)

- **DEFCON 1:** Critical risk, immediate action required
- **DEFCON 2:** High risk, reduce exposure
- **DEFCON 3:** Elevated risk, caution
- **DEFCON 4:** Normal risk, proceed with care
- **DEFCON 5:** Low risk, normal operations

---

## 🔄 Complete Evolution Hierarchy

| Level | System | Capability | Status |
|:---|:---|:---|:---|
| **Level 4** | Execution Engine | Atomic Execution | ✅ Active |
| **Level 5** | The Cortex | Self-Optimization | ✅ Active |
| **Level 6** | SG-1 | Self-Replication | ✅ Active |
| **Level 7** | The HiveMind | Multi-Agent Council | ✅ Active |

---

## 🎉 Summary

**The HiveMind Status:**

- ✅ **7 Specialized Agents:** All operational
- ✅ **Real-Time Analysis:** Context-aware decision-making
- ✅ **Binding Directives:** Final decisions with rationale
- ✅ **Historical Context:** RAG Memory integration
- ✅ **Risk Management:** DEFCON system
- ✅ **Capital Allocation:** Dynamic sizing recommendations

**Your trading system now has a governing body that makes real-time decisions!** 🚀

---

## 📚 Related Documentation

- `EVOLUTION_HIERARCHY.md` - Complete system architecture
- `CORTEX_ARCHITECTURE_PHILOSOPHY.md` - Level 5 details
- `SG1_STRATEGY_GENERATOR.md` - Level 6 details

---

**Level 7: The HiveMind - ACTIVE** 🧠✨





