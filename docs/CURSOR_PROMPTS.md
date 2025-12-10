# Cursor + Trading Analyst MCP — Prompt Playbook

This is your **cockpit manual** for using Cursor + the **Trading Analyst** MCP server as a decision-support layer on top of AITRAPP.

---

## Your Bot Structure (Quick Reference)

**Strategies:**
- **R1** – RegimeVolEngine (income short vol, regime-aware)
- **G1** – GammaScalper (delta-hedged long gamma)
- **T1** – CalendarArb (term-structure / calendar vol arb)
- **D1** – DispersionArb (index vs sector)
- **H1** – TailShortVolOverlay (tail risk overlay)
- **E1** – EventVolEngine (event + day-type context)
- **Allocator** – StrategyAllocator (ML-ready capital router)

**Data:**
- **Position store** – canonical PnL/exposure
- **Kite** – broker ground truth

**Trading Analyst MCP Tools:**
1. `get_live_risk_snapshot` - Complete risk view
2. `get_strategy_summary` - Per-strategy performance
3. `get_broker_vs_algo_reconciliation` - State drift detection
4. `get_event_and_regime_context` - R1 + E1 joint view
5. `propose_config_tweaks` - AI config suggestions

---

## Your Risk Limits (Customize These)

**Update these to match your actual configs:**

```yaml
# Your configured limits (example - adjust to actual)
margin_utilisation_max: 70%        # Hard stop
net_delta_max: 15                  # Absolute value
tail_coverage_min: 10%             # When short premium > ₹500k
daily_loss_limit: ₹50,000          # Hard stop (per day)
position_heat_max: 5%              # Per-position risk
portfolio_heat_max: 15%            # Total portfolio risk
```

**When using prompts below, reference YOUR limits explicitly.**

---

## 0. How to Talk to Trading Analyst

In Cursor chat, always hint that you want the **Trading Analyst** tools:

```
Using the Trading Analyst MCP tools, ...
```

Cursor will call the right MCP tools behind the scenes.

**Remember:** Trading Analyst MCP is **READ-ONLY**. It explains and suggests; you decide and apply changes.

---

## 1. Pre-Open GO/NO-GO Checks

### 1.1 Complete Pre-Open Safety Check

**Use before starting LIVE session.**

```
Using the Trading Analyst MCP tools, call get_broker_vs_algo_reconciliation and get_live_risk_snapshot and:

1. Check for any mismatches between broker (Kite) and my algo's position_store.
2. Confirm I am flat in index futures and weekly index options where my configs expect me to be flat pre-open.
3. Summarise my current margin utilisation, net delta, short premium notional, and tail coverage.
4. Based on my intended limits:
   - margin utilisation < 50% (pre-open)
   - |net delta| < 10 (pre-open)
   - tail coverage ≥ 10% when short premium > ₹500k
   - no orphan positions from yesterday

Answer with a clear GO or NO-GO for starting the LIVE session, and explain why in 3–5 bullet points.
```

**This is your hard gate before LIVE.**

---

## 2. Intraday Health & Regime Alignment

### 2.1 Environment + Risk Alignment Check

**Run every 30-60 minutes or when something feels "off".**

```
Using the Trading Analyst MCP tools, call get_live_risk_snapshot and get_event_and_regime_context for NIFTY and BANKNIFTY.

1. First, describe today's environment in plain language:
   - R1 regime per index (LOW_MEAN_REVERT / MEDIUM_TREND / HIGH_EVENT)
   - E1 event day-type (NORMAL / PRE_EVENT / EVENT_DAY / POST_EVENT)
   - IV rank, ATR%, RV/IV ratio
   - Any major event labels (RBI, Budget, US macro)

2. Then compare that environment to my current portfolio from get_live_risk_snapshot:
   - Net delta/gamma/vega
   - Short premium exposure
   - Tail coverage
   - Margin utilisation

3. Tell me explicitly whether my book is ALIGNED with the environment or FIGHTING it.
   Examples of misalignment:
   - Heavy short vol (R1) on HIGH_EVENT + EVENT_DAY with low tail coverage
   - Long gamma (G1) heavy on LOW_MEAN_REVERT + NORMAL day
   - Insufficient tail hedges (H1) when short premium is elevated

4. Suggest high-level actions I should consider (e.g., reduce short premium in BANKNIFTY, increase tails, pause new R1 entries), but do NOT propose specific orders.
```

---

### 2.2 Quick Intraday Risk Pulse

**Fast check every 30 min.**

```
Using get_live_risk_snapshot from the Trading Analyst MCP server, check:
- margin utilisation
- net delta
- tail coverage vs short premium

Flag if any of these are breached:
- margin ≥ 70%
- |net delta| > 15
- tail coverage < 10% while short premium notional > ₹500k

If all are within limits, summarise in one short paragraph.
If any are breached, highlight them as RED FLAGS and explain the implications in plain language so I can decide whether to manually cut risk or pause the bot.
```

---

## 3. Post-Close PM Note & Reconciliation

### 3.1 EOD PM Note (Strategies vs Regime)

**Run at 3:45 PM after market close.**

```
Using the Trading Analyst MCP tools, call get_strategy_summary and get_event_and_regime_context for today's session.

Write me an end-of-day PM note with:

1. PnL per strategy:
   - R1 (RegimeVolEngine): realised, unrealised, hit rate, allocation %
   - G1 (GammaScalper): realised, unrealised, hit rate, allocation %
   - T1 (CalendarArb): realised, unrealised, hit rate, allocation %
   - D1 (DispersionArb): realised, unrealised, hit rate, allocation %
   - H1 (TailShortVolOverlay): tail coverage %, premium paid
   - Any other active strategies

2. How their PnL lined up with the R1 regimes and E1 day-type we actually saw:
   - Did R1 make money on MEDIUM_TREND (expected)?
   - Did G1 struggle on LOW_MEAN_REVERT (expected)?
   - Did D1 work on sector rotation days?

3. Any strategies that consistently underperformed their 'intended' regimes over the last 10 sessions.

4. Red flags:
   - Strategies losing in regimes where they should win
   - Persistent drawdown beyond max_dd limits
   - Hit rates below target for 5+ consecutive days

5. End with a short bullet list of candidate config tweaks (allocator weights, regime bands, term-structure thresholds) that I could consider. Do NOT edit any config; just suggest.

Format this like a real PM note - clear sections, numbers, and actionable takeaways.
```

---

### 3.2 Broker vs Algo Reconciliation

**Run after close or when you suspect drift.**

```
Using get_broker_vs_algo_reconciliation from the Trading Analyst MCP server:

1. List all mismatches (orphans, ghosts, qty differences) between broker (Kite) and algo position_store.
2. For each mismatch, classify it as:
   - Reporting delay (likely harmless)
   - Partial fill not yet ingested (needs manual sync)
   - Serious state drift (requires immediate action)
3. For serious drifts, suggest specific manual actions I should take (e.g., manually close orphan position, resync position_store).

Compare realised PnL by underlying between broker and algo.
Highlight any mismatches in PnL > ₹1,000 or in positions.
Categorise each as likely fees/taxes, timing/reconciliation lag, or a genuine state drift requiring manual intervention.

Be paranoid - I'd rather get a false alarm than miss a real drift.
```

---

## 4. Weekly Review & Config Tuning

### 4.1 Weekly Strategy & Allocator Review

**Run Friday EOD.**

```
Using the Trading Analyst MCP tools, call get_strategy_summary with lookback_days=30 and combine with get_event_and_regime_context for the last 30 days.

For each strategy (R1, G1, T1, D1, H1), compute:
- 30-day realised PnL
- Hit rate (wins / total trades)
- Worst drawdown over the period
- Which regimes it actually traded in (LOW/MEDIUM/HIGH distribution)
- Current allocation % from Allocator

Tell me:
1. Which strategies earned their keep and could justify slightly higher allocator weight or capital cap.
2. Which should be cut back or temporarily paused due to poor performance or behaviour misaligned with their design.

Finish with a proposed allocator adjustment plan (increase/decrease/no change per strategy) that I can then map into configs/strategy_allocator.yaml.

For each suggestion, provide:
- Current allocation %
- Suggested new allocation %
- Reason (hit rate, drawdown, PnL trend, regime alignment)
- Which regime(s) the strategy struggled/excelled in

Make this a plan only; do not assume any file edits.
```

---

### 4.2 Config Tweaks (R1, Allocator, H1)

**Monthly or after major market regime shift.**

```
Using get_strategy_summary, get_event_and_regime_context, and propose_config_tweaks from the Trading Analyst MCP server with analysis_window_days=30 and focus='all':

Generate a JSON patch-like proposal of config changes for:
1. R1 regime bands (if we're consistently misclassifying or missing profitable regimes)
2. Strategy allocator weights/caps (especially for persistent over/underperformers)
3. H1 tail coverage targets for specific regimes or event types
4. G1 hedge thresholds (if churning or leaving too much delta)
5. T1 term structure bands (if missing setups or entering too often)
6. D1 correlation/liquidity thresholds per pair

For each suggested tweak, include:
- The old value
- The suggested new value
- A one-line justification tied to observed data (P&L, drawdown, regime behaviour)
- Which config file to edit (e.g., configs/regime_vol_engine.yaml)

This is a planning exercise only; I will review and apply changes manually to YAML.
```

---

## 5. Strategy-Specific Diagnostics

### 5.1 R1 - RegimeVolEngine Regime Classification

```
Using the Trading Analyst MCP tools and get_strategy_summary + get_event_and_regime_context, analyse R1_RegimeVolEngine over the last 20 sessions:

1. How often did R1 classify each regime (LOW/MEDIUM/HIGH)?
2. On days R1 classified as MEDIUM_TREND, what was the actual realised vol vs IV?
3. Were there days where R1 should have been active (high IV rank, stable trend) but stayed flat?
4. Were there days where R1 was active but the regime turned out to be choppy/unfavorable?

Suggest whether I should consider adjusting:
- IV rank thresholds for LOW/MEDIUM/HIGH bands
- ATR% thresholds
- RV/IV ratio thresholds

For each suggestion, provide the current threshold and suggested new threshold with reasoning.

Planning only, no live edits to configs/regime_vol_engine.yaml.
```

---

### 5.2 G1 - GammaScalper Hedge Behaviour

```
Using the Trading Analyst MCP tools and any strategy-specific stats exposed via get_strategy_summary, analyse G1_GammaScalper over the last 10 sessions:

1. Average number of hedge rebalances per day
2. Typical |net delta| before and after hedge
3. PnL distribution on HIGH_EVENT vs NORMAL days from get_event_and_regime_context
4. Is G1 hedging too aggressively (churning)?
5. Is G1 leaving too much directional exposure?
6. Is G1 broadly behaving as a stable long-gamma book?

Suggest whether I should consider adjusting:
- Hedge cooldown period
- Delta threshold for rebalancing
- Gamma threshold for entry

Planning only, no live edits to configs/gamma_scalper.yaml.
```

---

### 5.3 T1 - CalendarArb Term Structure

```
Using get_strategy_summary and any term-structure metrics available via Trading Analyst, evaluate T1_CalendarArb for NIFTY vs BANKNIFTY over the last 10 trading days:

1. How often did it open vs skip trades due to term_ratio/term_spread thresholds?
2. Were the profitable trades associated with clearly elevated weekly IV vs monthly IV, as you would expect for long calendars?
3. Are there underlyings where it rarely finds valid setups and might need different term bands?
4. What was the average term_ratio at entry for winning vs losing trades?

Suggest if any per-underlying term bands in configs/calendar_arb.yaml should be widened or tightened, and why.

Planning only, no live edits.
```

---

### 5.4 D1 - DispersionArb Pairs Analysis

```
Using get_strategy_summary and get_event_and_regime_context, analyse D1_DispersionArb over the last 20 sessions:

1. PnL per pair:
   - NIFTY–BANKNIFTY
   - NIFTY–FINNIFTY
   - NIFTY–MIDCAPNIFTY
   - Any other configured pairs

2. Typical realised vol ratio and correlation at entry for each pair
3. Which pair(s), if any, show noisy or unstable behaviour with poor risk-adjusted returns
4. Were there days with high sector rotation (favorable for D1) where D1 was inactive?

Recommend whether I should:
- Keep all pairs
- Downweight or temporarily disable specific pairs in configs/dispersion_arb.yaml
- Tighten correlation/liquidity thresholds for certain underlyings

Planning only, no live edits.
```

---

### 5.5 H1 - Tail Coverage Adequacy

```
Using get_live_risk_snapshot and get_event_and_regime_context, analyse H1_TailShortVolOverlay:

1. Current tail coverage % by underlying (NIFTY, BANKNIFTY)
2. Short premium notional by underlying
3. Is coverage adequate given:
   - Current regime (HIGH_EVENT needs more coverage)
   - Event context (EVENT_DAY needs more coverage)
   - Margin utilisation (high margin → need more tail protection)

4. Historical tail hedge performance:
   - Did H1 tails offset losses on event days?
   - What was the cost of carry (premium paid for tails) vs benefit?

Suggest whether I should adjust:
- Target tail coverage % per regime
- Target tail coverage % per event day-type
- Strike selection for tails (how far OTM)

Planning only, no live edits to configs/tail_short_vol.yaml.
```

---

## 6. Emergency / Anomaly Checks

### 6.1 Sudden PnL Drop Investigation

```
We just had an unexpected PnL drop / odd behaviour. Using Trading Analyst MCP tools:

Call get_live_risk_snapshot, get_strategy_summary, and get_broker_vs_algo_reconciliation now.

Tell me:
1. Which strategy or underlying is responsible for most of the move
2. Whether broker positions and algo positions match for that underlying
3. Whether risk metrics (delta, margin, tail coverage) are still within my hard limits:
   - margin < 70%
   - |net delta| < 15
   - tail coverage ≥ 10%
   - daily PnL > daily loss limit (₹-50k)

4. Timestamp of the move (if logs available)
5. Was there a major market event at that time?

Summarise in clear language whether this looks like:
- Normal volatility for my current book
- A parameter/config issue (e.g., G1 failed to hedge, R1 entered wrong regime)
- A genuine state drift / bug that warrants pausing the bot and flattening manually

Don't give me orders; give me a diagnosis so I can decide what to do.
```

---

### 6.2 Why Is This Strategy Losing?

**Use when a strategy underperforms for 3+ days.**

```
Using get_strategy_summary and get_event_and_regime_context, analyze why [STRATEGY_NAME] has been losing.

Look at:
1. Is it losing in regimes where it should win? (RED FLAG)
2. Is it losing in regimes where it's expected to struggle? (NORMAL)
3. Recent hit rate trend (improving or worsening over last 10 sessions?)
4. Has the market environment changed but the strategy hasn't adapted?
5. Are there parameter drifts (e.g., IV rank consistently lower than historical, term structure flatter)?

Give me 3-5 bullet points of root cause analysis, not just "it's underperforming."

Examples of good root cause:
- "R1 is classifying days as MEDIUM_TREND but realised vol is spiking intraday (choppy regime)"
- "G1 is entering long gamma but hedging too frequently, churning away PnL"
- "T1 is entering calendars but term structure is too flat (weekly vs monthly IV spread < threshold)"
```

Replace `[STRATEGY_NAME]` with R1, G1, T1, D1, etc.

---

## 7. Advanced Use Cases

### 7.1 Regime Transition Alert

```
Using get_event_and_regime_context, compare today's regime to recent history (if you have access to historical data or logs).

If we've transitioned regimes (e.g., LOW → MEDIUM or MEDIUM → HIGH):
1. Flag the transition explicitly
2. Explain which strategies should increase/decrease deployment:
   - R1: typically likes MEDIUM/HIGH with stable trends
   - G1: likes HIGH_EVENT with volatility expansion
   - T1: likes stable term structure (MEDIUM)
   - D1: likes sector rotation (any regime with dispersion)
3. Suggest whether I should manually adjust H1 tail coverage given new regime

This helps me catch regime shifts before the bot fully adapts.
```

---

### 7.2 Config Diff Proposal

**After getting suggestions from `propose_config_tweaks`:**

```
Based on the config changes you just proposed, generate a YAML diff that I can directly apply.

Show:
1. Old values
2. New values
3. Files to edit (e.g., configs/strategy_allocator.yaml, configs/regime_vol_engine.yaml)
4. Command to backup current config before editing

Format as code blocks I can copy-paste.

Example:
```yaml
# configs/strategy_allocator.yaml
# OLD:
strategy_allocator:
  allocations:
    R1: 15
    G1: 8
    T1: 10

# NEW:
strategy_allocator:
  allocations:
    R1: 18  # +3% due to strong 30d performance
    G1: 5   # -3% due to struggling in LOW vol
    T1: 10  # no change
\`\`\`

# Backup command:
cp configs/strategy_allocator.yaml configs/strategy_allocator.yaml.bak
```
```

---

## 8. Prompt Library Tips

### 1. Save Your Favorites

Create a `~/trading_prompts.txt` file:

```bash
cat > ~/trading_prompts.txt << 'EOF'
# Pre-open GO/NO-GO
Using the Trading Analyst MCP tools, call get_broker_vs_algo_reconciliation and get_live_risk_snapshot...

# Intraday check
Call get_live_risk_snapshot and get_event_and_regime_context...

# EOD PM note
Use get_strategy_summary and get_event_and_regime_context for today...
EOF
```

### 2. Chain Multiple Tools

Cursor can call multiple MCP tools in one response:

```
Using get_live_risk_snapshot AND get_broker_vs_algo_reconciliation AND get_event_and_regime_context, give me a complete pre-open briefing.
```

### 3. Be Specific About Thresholds

Always reference YOUR configured limits:

```
Flag if margin > 70%, |net delta| > 15, or tail coverage < 10% while short premium > ₹500k
```

Better than vague:

```
Tell me if anything looks bad
```

### 4. Ask "Why" Questions

Use MCP for learning:

```
Using get_event_and_regime_context, explain why R1 is favored in MEDIUM_TREND regime but G1 struggles. Teach me the intuition behind regime classification.
```

---

## 9. Integration with Your Workflow

### Morning Routine (9:00 AM)
1. Run pre-open GO/NO-GO check (prompt 1.1)
2. If GO, start LIVE session
3. If NO-GO, investigate mismatches and fix before starting

### Intraday Routine (Every 30-60 min)
1. Quick risk pulse (prompt 2.2)
2. If RED FLAGS, run full environment check (prompt 2.1)
3. Decide whether to manually intervene (cut risk, pause bot, flatten)

### Post-Close Routine (3:45 PM)
1. Run EOD PM note (prompt 3.1)
2. Run reconciliation check (prompt 3.2)
3. Review strategy performance vs regime alignment
4. Make notes for weekly review

### Weekly Review (Friday EOD)
1. Run weekly strategy review (prompt 4.1)
2. Run config tweaks proposal (prompt 4.2)
3. Apply approved changes to YAML configs
4. Commit configs with detailed commit message

### Monthly Review
1. Deep-dive into each strategy (prompts 5.1-5.5)
2. Review regime classification accuracy
3. Tune parameters based on 30-day performance
4. Update allocator weights if justified

---

## 10. What NOT to Do

### ❌ Don't ask MCP to place orders

```
BAD: "Using MCP, close all R1 positions"
GOOD: "Using MCP, analyze whether I should consider closing R1 positions"
```

### ❌ Don't ask MCP to edit configs

```
BAD: "Update configs/strategy_allocator.yaml with new weights"
GOOD: "Propose new allocator weights, I'll apply them manually"
```

### ❌ Don't blindly trust suggestions

Always review proposals against:
- Your market intuition
- Recent news/events
- Risk limits
- Position sizing

### ❌ Don't use MCP as a replacement for monitoring

MCP is decision support, not automated trading. You still need:
- Eyes on positions
- Manual GO/NO-GO decisions
- Human judgment for edge cases

---

## 11. Success Metrics

After 1 week of using Trading Analyst MCP, you should see:

1. **Faster decisions** - Pre-open check: 5 min → 30 sec
2. **Fewer misses** - Reconciliation catches orphans before they're a problem
3. **Better allocation** - Data-driven weight changes, not gut feel
4. **Clearer context** - You know WHY strategies are working/not working

After 1 month:
1. **Improved hit rates** - Better regime alignment
2. **Lower drawdowns** - Earlier detection of misalignment
3. **More confidence** - AI validates your decisions with data

---

## 12. Support & Troubleshooting

If prompts aren't working:

1. **Check MCP logs**: Cursor → View → Output → MCP
2. **Test tools directly**: Run Python adapter manually
3. **Refine prompt**: Be more specific about what you want
4. **Check bot API**: Ensure endpoints return real data

Most issues:
- Prompt too vague (80%)
- Bot API down (15%)
- MCP config issue (5%)

---

## Appendix: Your Exact Limits (Customize This)

```yaml
# Copy from your actual configs and keep updated
risk_limits:
  margin:
    max_utilisation_pct: 70
    comfortable_pct: 50
    pre_open_max_pct: 30

  greeks:
    max_net_delta: 15
    max_net_vega: 50000
    max_net_gamma: 0.05

  tail_coverage:
    min_pct_when_short_premium_high: 10
    short_premium_high_threshold: 500000  # ₹5 lakh
    target_pct_event_day: 15

  daily_loss:
    hard_stop: 50000  # ₹50k
    soft_alert: 30000  # ₹30k

  position_sizing:
    max_position_heat_pct: 5
    max_portfolio_heat_pct: 15
    max_positions: 20
```

Update this section with YOUR actual limits so prompts reference correct thresholds.

---

**Remember:** Trading Analyst MCP is your analyst brain, not your trading hand. It reads, analyzes, suggests. You decide and execute.
