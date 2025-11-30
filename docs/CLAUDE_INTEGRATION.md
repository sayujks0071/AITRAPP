# Claude Integration - Pluggable LLM Backend

## Overview

The AITRAPP HiveMind system now supports **both Claude (Anthropic) and OpenAI** as pluggable LLM backends. All agents share the same backend, enabling seamless agent-to-agent interactions.

---

## Configuration

### Environment Variables

```bash
# Choose provider: "anthropic" or "openai" (default: "anthropic")
export HIVEMIND_PROVIDER="anthropic"

# Anthropic (Claude) settings
export ANTHROPIC_API_KEY="sk-ant-..."
export HIVEMIND_ANTHROPIC_MODEL="claude-3-5-sonnet-latest"

# OpenAI settings (if using OpenAI)
export OPENAI_API_KEY="sk-proj-..."
export HIVEMIND_OPENAI_MODEL="gpt-5"

# Shared settings
export HIVEMIND_TEMPERATURE="0.1"
export HIVEMIND_MAX_TOKENS="800"
```

### Quick Switch

To switch from OpenAI to Claude (or vice versa), just change the provider:

```bash
# Use Claude
export HIVEMIND_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."

# Use OpenAI
export HIVEMIND_PROVIDER="openai"
export OPENAI_API_KEY="sk-proj-..."
```

**No code changes required!** All agents automatically use the configured backend.

---

## Architecture

### LLM Client Layer

The `LLMClient` class (`packages/core/intelligence/llm_client.py`) provides a unified interface:

```python
from packages.core.intelligence.llm_client import LLMClient, LLMConfig

# Create client with default config (reads from env)
client = LLMClient()

# Or customize
config = LLMConfig(
    provider="anthropic",
    anthropic_model="claude-3-5-sonnet-latest",
    temperature=0.1
)
client = LLMClient(config)

# Use it
result = client.chat_json(
    system_prompt="You are a trading analyst.",
    user_prompt="Analyze this data: {...}"
)
```

### BaseAgent Integration

All HiveMind agents (`BaseAgent` subclasses) automatically use the configured LLM backend:

```python
from packages.core.hivemind.base import BaseAgent
from packages.core.intelligence.llm_client import LLMClient, LLMConfig

# Shared LLM client for all agents
llm = LLMClient(LLMConfig())

# Agents share the same backend
analyst = CortexAnalyst(llm_client=llm)
sg1 = SG1StrategyGenerator(llm_client=llm)
```

---

## Agent-to-Agent Interactions

### HiveMind Orchestrator

The `HiveMindOrchestrator` enables multi-agent conversations:

```python
from packages.core.hivemind.orchestrator import HiveMindOrchestrator

# Initialize with shared LLM backend
hm = HiveMindOrchestrator(vector_store=None)

# Run a conversation round
core_ctx = {
    "day": "2025-11-21",
    "metrics": {
        "intraday_short_strangle_v1": {
            "trades": 4, "wins": 3, "losses": 1, "max_dd": -2800
        }
    },
    "guardrails": {
        "max_dd_per_strategy": 0.03
    }
}

result = hm.run_config_round(core_ctx)
# Returns: {"analyst": {...}, "sg1": {...}}
```

### Nightly Round Script

Run a full agent conversation:

```bash
# Dry run (generate suggestions, don't apply)
python3 scripts/nightly_hivemind_round.py --dry-run

# With output file
python3 scripts/nightly_hivemind_round.py --output reports/tuning/my_round.json
```

---

## Usage Examples

### Example 1: Single Agent (CortexAnalyst)

```python
from packages.core.intelligence.analyst import CortexAnalyst

analyst = CortexAnalyst()
context = {
    "date": "2025-11-21",
    "pnl": {"day": 1200.5},
    "trades": [],
    "regime": {"NIFTY": {"regime": "LOW_MEAN_REVERT"}}
}

result = analyst.think(context)
# Uses Claude or OpenAI based on HIVEMIND_PROVIDER
```

### Example 2: Shared Backend (Agent-to-Agent)

```python
from packages.core.intelligence.llm_client import LLMClient, LLMConfig
from packages.core.intelligence.analyst import CortexAnalyst
from packages.core.intelligence.sg1 import SG1StrategyGenerator

# Shared LLM client
llm = LLMClient(LLMConfig(provider="anthropic"))

# Both agents use Claude
analyst = CortexAnalyst(llm_client=llm)
sg1 = SG1StrategyGenerator(llm_client=llm)

# Analyst proposes changes
analyst_out = analyst.think({"core": {...}})

# SG-1 converts to patches (using same Claude backend)
sg1_out = sg1.think({"core": {"analyst": analyst_out, ...}})
```

### Example 3: Orchestrator (Full Round)

```python
from packages.core.hivemind.orchestrator import HiveMindOrchestrator

hm = HiveMindOrchestrator()
result = hm.run_config_round({
    "day": "2025-11-21",
    "metrics": {...}
})

# All agents used the same LLM backend (Claude or OpenAI)
print(result["analyst"])  # Analyst's output
print(result["sg1"])      # SG-1's output
```

---

## Fallback Behavior

If the configured provider is unavailable:

1. **Anthropic unavailable** → Falls back to OpenAI
2. **OpenAI unavailable** → Falls back to heuristics
3. **Both unavailable** → All agents use heuristic fallbacks

The system gracefully degrades without crashing.

---

## Model Support

### Anthropic (Claude)
- `claude-3-5-sonnet-latest` (default)
- `claude-3-opus-latest`
- `claude-3-sonnet-latest`
- `claude-3-haiku-latest`

### OpenAI
- `gpt-5` (default, falls back to `gpt-4o` if unavailable)
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-4`

---

## Installation

### Anthropic

```bash
pip install anthropic
```

### OpenAI

```bash
pip install openai
```

---

## Testing

Test the integration:

```bash
# Test with Claude
export HIVEMIND_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."
python3 scripts/nightly_hivemind_round.py --dry-run

# Test with OpenAI
export HIVEMIND_PROVIDER="openai"
export OPENAI_API_KEY="sk-proj-..."
python3 scripts/nightly_hivemind_round.py --dry-run
```

---

## Next Steps

1. **JSON Patch Schema**: Design schema for config changes
2. **Config Patcher**: Auto-apply approved changes to YAML
3. **Risk Officer Agent**: Add risk critique layer
4. **Vector Store Integration**: Add RAG for historical context

---

## Notes

- All agents share the same LLM backend for consistency
- Agent-to-agent conversations use the same provider
- No code changes needed to switch providers
- Graceful fallback if provider is unavailable
- Supports both Claude and OpenAI JSON mode




