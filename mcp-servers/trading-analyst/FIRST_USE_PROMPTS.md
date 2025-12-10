# Trading Analyst MCP - First-Use Prompts

**Pin these prompts for your first week** of using the MCP server. They're designed to help you learn the tools and integrate them into your daily workflow.

---

## 🧪 Smoke Test (Run this first)

After installing and restarting Cursor, verify MCP is working:

### Prompt: Risk Snapshot Smoke Test

```
Using the Trading Analyst MCP tools, call get_live_risk_snapshot and:

1. Summarise my net delta, net vega, margin utilisation and tail coverage in one paragraph.
2. Then tell me if anything is outside my configured safe band:
   - margin utilisation > 70%
   - |net delta| > 15
   - tail coverage < 10% while short premium > ₹500k

Use plain language, not just raw numbers.
```

**Expected:**
- Tool call to `get_live_risk_snapshot`
- Natural language summary
- Clear flags if any threshold is breached

**If this works:** ✅ MCP is ready to use

---

## 📅 Daily Workflow Prompts

### A. Pre-open GO/NO-GO (9:00 AM)

**Purpose:** Verify state integrity before starting LIVE session.

```
Use get_broker_vs_algo_reconciliation and get_live_risk_snapshot:

1. Confirm there are no mismatches between broker and algo positions that look serious.
2. Confirm I am flat where my configs expect me to be flat pre-open (index futures and weekly options).
3. Check margin and tail coverage against my pre-market limits:
   - margin utilisation should be < 50% pre-open
   - no orphan positions from yesterday's close
   - position count matches what I expect

Answer with a clear GO or NO-GO for starting the LIVE session, and explain why in 3–5 bullet points.
```

**What it checks:**
- State drift (orphans/ghosts)
- Correct flatness
- Margin headroom
- Clean slate for new session

**Expected output:**
```
✅ GO FOR LIVE SESSION

• Reconciliation: No mismatches. Broker and algo state match perfectly.
• Positions: Flat (0 open positions)
• Margin: 0% utilisation (₹1,000,000 available)
• No orphan positions from yesterday
• All systems aligned for clean start

You can safely start LIVE trading.
```

---

### B. Intraday "Is the bot behaving?" Check (Every 30-60 min)

**Purpose:** Continuous risk monitoring and environment alignment check.

```
Call get_live_risk_snapshot and get_event_and_regime_context for NIFTY and BANKNIFTY.

1. Explain today's environment: regime, event context, and whether it favours income, long gamma, calendars, or dispersion.
2. Then tell me if my current risk (delta, vega, tail coverage, margin) is aligned with that environment or fighting it.
3. If there's a mismatch (e.g., heavy short vol on HIGH_EVENT + EVENT_DAY), highlight it explicitly so I can decide whether to manually cut risk.

Keep it concise - I just need to know if things look normal or if I should intervene.
```

**What it checks:**
- Current regime (R1) + event context (E1)
- Portfolio risk profile
- Alignment between environment and strategy deployment
- Warning flags for mismatches

**Expected output example 1 (aligned):**
```
✅ ENVIRONMENT & RISK ALIGNED

Today's Environment:
• NIFTY: MEDIUM_TREND regime, no events (NORMAL day)
• BANKNIFTY: LOW_MEAN_REVERT regime, no events

This environment favours:
• Income strategies (R1 short vol, short condors) ✓
• Calendar arb (stable vol term structure) ✓

Current Risk:
• Net delta: 3.2 (neutral, good)
• Margin: 42% (comfortable)
• Short premium: ₹450k with 14% tail coverage (adequate)

Assessment: Your positioning matches the regime. R1 and T1 should perform well today. No intervention needed.
```

**Expected output example 2 (misaligned):**
```
⚠️ POTENTIAL MISMATCH DETECTED

Today's Environment:
• NIFTY: HIGH_EVENT regime, EVENT_DAY (RBI Policy Announcement)
• BANKNIFTY: HIGH_EVENT regime, PRE_EVENT

This environment favours:
• Long gamma (G1) ✓
• Tail hedges (H1) ✓
• NOT income short vol ✗

Current Risk:
• Net delta: -8.5 (slightly bearish)
• Margin: 68% (elevated)
• Short premium: ₹850k with only 8% tail coverage ⚠️

⚠️ WARNING: You're running heavy short vol (R1) on an EVENT_DAY with thin tail coverage. This is fighting the regime.

Suggested Actions:
1. Reduce short premium in BANKNIFTY (most exposed)
2. OR increase H1 tail hedges to 12%+ coverage
3. OR pause new R1 entries until post-event

No automatic action taken. Manual review required.
```

---

### C. Mid-day Context Check (12:30 PM - Optional)

**Purpose:** Quick environment check if you haven't looked at the market all morning.

```
Using get_event_and_regime_context, tell me:
- What regime we're in (LOW/MEDIUM/HIGH vol)
- Whether it's an event day (PRE_EVENT/EVENT_DAY/POST_EVENT)
- Which of my strategies should naturally be doing well vs struggling

Keep it to 2-3 sentences.
```

**Expected output:**
```
We're in MEDIUM_TREND regime for NIFTY and LOW_MEAN_REVERT for BANKNIFTY. No events today (NORMAL day). This environment favours income strategies (R1), calendar arb (T1), and is neutral for gamma scalping (G1). Short vol should be working well.
```

---

### D. Post-close PM Note (3:45 PM)

**Purpose:** End-of-day performance review and config adjustment ideas.

```
Use get_strategy_summary and get_event_and_regime_context for today.

Give me a mini PM note:
1. Which strategies made/lost money today
2. Whether that matches the kind of regime we were in
3. Any obvious red flags (e.g., strategy consistently losing in the regimes it's supposed to be good at)
4. A short bullet list of suggested config changes which I can later review and apply manually

Format this like a real PM note - clear sections, numbers, and actionable takeaways.
```

**Expected output:**
```
=== EOD PM Note: 2025-11-17 ===

ENVIRONMENT
• NIFTY: MEDIUM_TREND regime, NORMAL day
• BANKNIFTY: LOW_MEAN_REVERT regime, NORMAL day
• This was a textbook income/calendar environment

STRATEGY PERFORMANCE
1. R1 (RegimeVolEngine): +₹12,500 realised, +₹800 unrealised ✓
   - 62% hit rate (20d), consistent with regime
   - Max DD: ₹-18k (60d) - within limits

2. G1 (GammaScalper): -₹2,500 realised, flat unrealised ✗
   - 48% hit rate (20d), struggling in LOW vol
   - This is expected - G1 needs HIGH_EVENT or volatility expansion

3. T1 (CalendarArb): +₹4,200 realised, +₹1,100 unrealised ✓
   - 58% hit rate (20d), performing as expected
   - Calendar spreads working well in stable term structure

RED FLAGS
• G1 has underperformed in 7 of last 10 LOW/MEDIUM regime days
• Allocation might be too high for current environment (5% allocated but only 42% win rate in non-event periods)

SUGGESTED CONFIG CHANGES
1. Reduce G1 allocation from 5% → 3% until we see more HIGH_EVENT days
2. Increase R1 allocation from 15% → 17% (strong performance in current regime)
3. Consider tightening G1 entry filters for MEDIUM_TREND (only enter if RV/IV > 1.2)

NEXT SESSION
• Continue current R1/T1 positioning if regime stays MEDIUM/LOW
• Watch for regime transition to HIGH (would favor increasing G1)
• H1 tail coverage at 14% - adequate, no changes needed
```

---

## 🔬 Weekly Review Prompts

### E. Allocator Weight Adjustment (Friday EOD)

**Purpose:** Data-driven allocation changes based on recent performance.

```
Using propose_config_tweaks with analysis_window_days=30 and focus='allocator', analyze the last 30 days.

Propose weight changes for strategies that are consistently underperforming or outperforming. I'll manually review and apply the changes to my YAML configs.

For each suggestion, explain:
- Current allocation %
- Suggested new allocation %
- Reason (hit rate, drawdown, PnL trend, regime alignment)
- Which regime(s) the strategy struggled/excelled in

Be specific about numbers, not vague.
```

**Expected output:**
```
=== ALLOCATOR WEIGHT PROPOSALS (30-day analysis) ===

1. R1 (RegimeVolEngine)
   Current: 15%
   Suggested: 18% (+3%)

   Reason:
   • 68% hit rate over 30 days (target: 60%)
   • Realised PnL: +₹45,000
   • Max DD: ₹-12,000 (well within ₹-20k limit)
   • Strong performance in MEDIUM_TREND (70% of days)
   • Consistent positive edge in intended regimes

   Verdict: Increase allocation. R1 is delivering.

2. G1 (GammaScalper)
   Current: 8%
   Suggested: 5% (-3%)

   Reason:
   • 42% hit rate over 30 days (target: 55%)
   • Realised PnL: -₹8,000
   • Only 3 HIGH_EVENT days in last 30 (G1 needs these)
   • Struggling in LOW/MEDIUM regimes (90% of recent days)
   • Not getting the environment it needs

   Verdict: Reduce allocation until we see more event-driven vol.

3. T1 (CalendarArb)
   Current: 10%
   Suggested: 10% (no change)

   Reason:
   • 55% hit rate (stable, not exceptional)
   • Realised PnL: +₹18,000 (consistent)
   • Max DD: ₹-8,000 (very controlled)
   • No strong reason to change

   Verdict: Keep current allocation.

4. D1 (DispersionArb)
   Current: 7%
   Suggested: 9% (+2%)

   Reason:
   • 64% hit rate over 30 days
   • Realised PnL: +₹22,000
   • Working well when index vol < single-stock vol
   • Recent macro environment (sector rotation) favours dispersion

   Verdict: Modest increase justified.

TO APPLY:
Edit configs/strategy_allocator.yaml:

```yaml
strategy_allocator:
  allocations:
    R1: 18  # was 15
    G1: 5   # was 8
    T1: 10  # no change
    D1: 9   # was 7
```

Then restart bot or reload configs.
```

---

## 🎯 Troubleshooting Prompts

### F. Reconciliation Deep-Dive

If you suspect state drift:

```
Using get_broker_vs_algo_reconciliation, do a detailed analysis:

1. List all mismatches (orphans, ghosts, qty differences)
2. For each mismatch, classify it as:
   - Reporting delay (likely harmless)
   - Partial fill not yet ingested (needs manual sync)
   - Serious state drift (requires immediate action)
3. For serious drifts, suggest specific manual actions I should take

Be paranoid - I'd rather get a false alarm than miss a real drift.
```

---

### G. Why Is This Strategy Losing?

If a strategy underperforms:

```
Using get_strategy_summary and get_event_and_regime_context, analyze why [STRATEGY_NAME] has been losing.

Look at:
1. Is it losing in regimes where it should win? (red flag)
2. Is it losing in regimes where it's expected to struggle? (normal)
3. Recent hit rate trend (improving or worsening?)
4. Has the market environment changed but the strategy hasn't adapted?

Give me 3-5 bullet points of root cause analysis, not just "it's underperforming."
```

Replace `[STRATEGY_NAME]` with R1, G1, T1, etc.

---

## 💡 Advanced Prompts (After 1 week of use)

### H. Regime Transition Alert

```
Using get_event_and_regime_context, compare today's regime to yesterday's (if you have historical data).

If we've transitioned regimes (e.g., LOW → MEDIUM or MEDIUM → HIGH):
1. Flag the transition explicitly
2. Explain which strategies should increase/decrease deployment
3. Suggest whether I should manually adjust H1 tail coverage

This helps me catch regime shifts before the bot fully adapts.
```

---

### I. Config Diff Proposal

After getting suggestions from `propose_config_tweaks`:

```
Based on the config changes you just proposed, generate a YAML diff that I can directly apply.

Show:
1. Old values
2. New values
3. Files to edit (e.g., configs/strategy_allocator.yaml, configs/regime_vol_engine.yaml)

Format as a code block I can copy-paste.
```

---

## 📌 Prompt Library Tips

### 1. Save Your Favorites

Create a `prompts.txt` file with your most-used prompts for quick copy-paste:

```bash
# Save common prompts
cat > ~/trading_prompts.txt << 'EOF'
# Pre-open GO/NO-GO
Use get_broker_vs_algo_reconciliation and get_live_risk_snapshot...

# Intraday check
Call get_live_risk_snapshot and get_event_and_regime_context...
EOF
```

### 2. Chain Multiple Tools

Cursor can call multiple MCP tools in one response. Leverage this:

```
Using get_live_risk_snapshot AND get_broker_vs_algo_reconciliation AND get_event_and_regime_context, give me a complete pre-open briefing.
```

### 3. Be Specific About Thresholds

The more specific you are, the better the analysis:

```
Flag if margin > 75%, |net delta| > 20, or tail coverage < 12%
```

Better than:

```
Tell me if anything looks bad
```

### 4. Ask "Why" Questions

Use MCP for learning, not just monitoring:

```
Using get_event_and_regime_context, explain why R1 is favored in today's regime but G1 is not. Teach me the intuition.
```

---

## 🎓 Learning Path

**Week 1:** Use prompts A, B, D (pre-open, intraday, post-close)
**Week 2:** Add prompt E (weekly allocator review)
**Week 3:** Add prompts F, G (troubleshooting)
**Week 4+:** Create custom prompts based on your workflow

---

## 📞 Support

If prompts aren't working as expected:

1. **Check MCP logs**: Cursor → View → Output → MCP
2. **Test tools directly**: See if Python adapter returns good data
3. **Refine prompt**: Be more specific about what you want

Most issues are:
- Prompt too vague (80%)
- Tool returns placeholder data because bot API is down (15%)
- MCP config issue (5%)
