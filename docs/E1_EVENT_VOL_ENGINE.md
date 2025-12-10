# Event-Driven Vol Engine (E1) - Future Design

## Overview

The Event-Driven Vol Engine (E1) is an **optional premium module** that maintains an event calendar and provides event-aware adjustments to R1, Allocator, and H1.

**Status:** Design document only - implement after full stack is stable in LIVE.

---

## Concept

E1 monitors upcoming events (Budget, RBI, US CPI/Fed, elections, etc.) and:

1. **Tags days** as pre-event / event / post-event
2. **Feeds into R1** - Regime hints (favor long vol before events)
3. **Feeds into Allocator** - Penalize/boost specific roles on event days
4. **Feeds into H1** - Bump tail coverage targets around events

---

## Event Calendar Structure

```yaml
events:
  - name: "RBI Policy Meeting"
    date: "2025-02-07"
    type: "CENTRAL_BANK"
    impact_level: "HIGH"
    pre_event_days: 3
    post_event_days: 2
    affected_underlyings: ["NIFTY", "BANKNIFTY"]
    
  - name: "US CPI Release"
    date: "2025-02-13"
    type: "ECONOMIC_DATA"
    impact_level: "MEDIUM"
    pre_event_days: 2
    post_event_days: 1
    affected_underlyings: ["NIFTY"]
    
  - name: "Union Budget"
    date: "2025-02-01"
    type: "FISCAL_POLICY"
    impact_level: "VERY_HIGH"
    pre_event_days: 5
    post_event_days: 3
    affected_underlyings: ["NIFTY", "BANKNIFTY"]
```

---

## Integration Points

### R1 Integration

E1 can provide regime hints:
- Pre-event: Favor HIGH_EVENT regime
- Event day: Force HIGH_EVENT or CHAOTIC
- Post-event: Allow return to normal

### Allocator Integration

E1 can adjust role weights:
- Pre-event: Cut income_short_vol, boost long_vol
- Event day: Maximum cuts on short vol
- Post-event: Gradual return to normal

### H1 Integration

E1 can adjust coverage multipliers:
- Pre-event: Increase coverage multiplier
- Event day: Maximum coverage
- Post-event: Gradual return to normal

---

## Implementation Notes

**When to implement:**
- After full stack is stable in LIVE
- After position store is fully wired
- After PAPER behavior is well understood

**Priority:** Low (nice-to-have, not critical)

**Complexity:** Medium (requires event calendar maintenance)

---

## Future Enhancement

This is a placeholder for future implementation. Focus on:
1. Position store integration
2. PAPER playbook execution
3. Small LIVE rollout
4. Then consider E1


