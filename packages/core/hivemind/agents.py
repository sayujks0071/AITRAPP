"""
The Council of Seven - HiveMind Agents
======================================

Seven specialized AI agents that form the "Board of Directors" for real-time decision-making.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from packages.core.hivemind.base import BaseAgent
from packages.core.rag_memory import RAGMemory

logger = logging.getLogger("hivemind")


# 1. MarketAgent
class MarketAgent(BaseAgent):
    """
    "The Eyes" - Expert Market Analyst specializing in Regime Detection and Volatility Analysis.
    """
    
    def __init__(self):
        super().__init__(
            "MarketAgent",
            "Expert Market Analyst specializing in Regime Detection and Volatility Analysis."
        )
    
    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        return f"""
You are the MarketAgent. Analyze the current market data.

INPUT DATA:
- VIX: {context.get('vix', 'N/A')}
- Recent Trend: {context.get('trend', 'N/A')}
- Major Events Today: {context.get('events', 'None')}

Determine the Market Regime (BULL_TREND, BEAR_TREND, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, CHAOTIC).
Confidence score (0-100).

Output JSON: {{ "regime": "...", "confidence": 85, "volatility_state": "..." }}
"""
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        regime = context.get("regime", "UNKNOWN")
        iv = context.get("iv_percentile", 0.5)
        
        if iv > 0.75:
            vol_state = "HIGH"
            regime = "SIDEWAYS_HIGH_VOL" if regime == "UNKNOWN" else regime
        elif iv < 0.25:
            vol_state = "LOW"
            regime = "SIDEWAYS_LOW_VOL" if regime == "UNKNOWN" else regime
        else:
            vol_state = "NORMAL"
        
        return {
            "agent": self.name,
            "regime": regime,
            "confidence": 60,
            "volatility_state": vol_state
        }


# 2. StrategyAgent
class StrategyAgent(BaseAgent):
    """
    "The General" - Head of Trading Strategy. Evaluates signal quality and strategy health.
    """
    
    def __init__(self):
        super().__init__(
            "StrategyAgent",
            "Head of Trading Strategy. Evaluates signal quality and strategy health."
        )
    
    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        strategy_metrics = context.get('strategy_metrics', {})
        return f"""
You are the StrategyAgent. Review strategy performance.

STRATEGY METRICS:
{json.dumps(strategy_metrics, indent=2)}

Identify which strategies are underperforming vs expected behavior in this regime.
Recommend: HOLD, PAUSE, or SCALE_UP for each.

Output JSON: {{ "recommendations": {{ "trend_credit_spread": "SCALE_UP", ... }} }}
"""
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        strategy_metrics = context.get('strategy_metrics', {})
        recommendations = {}
        
        for strategy, metrics in strategy_metrics.items():
            win_rate = metrics.get('win_rate', 0.5)
            if win_rate > 0.6:
                recommendations[strategy] = "SCALE_UP"
            elif win_rate < 0.4:
                recommendations[strategy] = "PAUSE"
            else:
                recommendations[strategy] = "HOLD"
        
        return {
            "agent": self.name,
            "recommendations": recommendations if recommendations else {"default": "HOLD"}
        }


# 3. RiskAgent
class RiskAgent(BaseAgent):
    """
    "The Shield" - Chief Risk Officer. Paranoid about drawdowns and gamma risk.
    """
    
    def __init__(self):
        super().__init__(
            "RiskAgent",
            "Chief Risk Officer. Paranoid about drawdowns and gamma risk."
        )
    
    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        portfolio_risk = context.get("portfolio_risk", {})
        net_delta = context.get('net_delta', 0)
        margin_used = portfolio_risk.get("margin_utilization_pct", 0.0)
        pnl = portfolio_risk.get("daily_pnl", 0.0)
        net_liquid = portfolio_risk.get("net_liquid", 1000000.0)
        pnl_pct = (pnl / net_liquid * 100) if net_liquid > 0 else 0.0
        
        return f"""
You are the RiskAgent. Protect the capital.

PORTFOLIO STATE:
- Net Delta: {net_delta}
- Margin Used: {margin_used:.1f}%
- Daily PnL: ₹{pnl:,.2f} ({pnl_pct:.2f}%)

Assess safety. If PnL is < -2% or Delta is dangerous, trigger DEFCON levels.
DEFCON 5 (Safe) to DEFCON 1 (Liquidate All).

Output JSON: {{ "defcon_level": 5, "action_required": "NONE", "max_allowed_allocation": 1.0 }}
"""
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        portfolio_risk = context.get("portfolio_risk", {})
        net_delta = abs(context.get('net_delta', 0))
        pnl = portfolio_risk.get("daily_pnl", 0.0)
        net_liquid = portfolio_risk.get("net_liquid", 1000000.0)
        pnl_pct = (pnl / net_liquid * 100) if net_liquid > 0 else 0.0
        
        # Determine DEFCON level
        # Check most severe conditions first (higher thresholds)
        # Note: pnl_pct is already calculated as percentage (e.g., -0.5 for -0.5%)
        # Priority: PnL first, then delta (delta alone doesn't escalate beyond PnL severity)
        if pnl_pct < -2.0 or (pnl_pct < -1.5 and net_delta > 200):
            defcon = 1
            action = "LIQUIDATE_ALL"
            max_alloc = 0.0
        elif pnl_pct < -1.5 or (pnl_pct < -1.0 and net_delta > 150):
            defcon = 2
            action = "REDUCE_EXPOSURE"
            max_alloc = 0.3
        elif pnl_pct < -1.0 or (pnl_pct < -0.5 and net_delta > 100):
            defcon = 3
            action = "CAUTION"
            max_alloc = 0.6
        elif pnl_pct <= -0.5 or net_delta > 50:  # DEFCON 4: -0.5% PnL OR delta > 50
            defcon = 4
            action = "MONITOR"
            max_alloc = 0.8
        else:
            defcon = 5
            action = "NONE"
            max_alloc = 1.0
        
        return {
            "agent": self.name,
            "defcon_level": defcon,
            "action_required": action,
            "max_allowed_allocation": max_alloc
        }


# 4. ExecutionAgent
class ExecutionAgent(BaseAgent):
    """
    "The Sniper" - Head of Execution. Obsessed with slippage and fill rates.
    """
    
    def __init__(self):
        super().__init__(
            "ExecutionAgent",
            "Head of Execution. Obsessed with slippage and fill rates."
        )
    
    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        execution_stats = context.get("execution_stats", {})
        avg_slippage = execution_stats.get("avg_slippage_bps", 0.0)
        chase_savings = execution_stats.get("avg_limit_chase_savings_bps", 0.0)
        
        return f"""
You are the ExecutionAgent. Optimize the Limit Chase Engine.

EXECUTION STATS:
- Avg Slippage: {avg_slippage:.2f} bps
- Limit Chase Savings: {chase_savings:.2f} bps

Should we be more aggressive (pay spread) or passive (chase longer)?

Output JSON: {{ "execution_mode": "PASSIVE", "suggested_timeout": 10 }}
"""
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        execution_stats = context.get("execution_stats", {})
        avg_slippage = execution_stats.get("avg_slippage_bps", 0.0)
        chase_savings = execution_stats.get("avg_limit_chase_savings_bps", 0.0)
        
        # If slippage is high but chase savings are good, stay passive
        if avg_slippage > 10 and chase_savings > 5:
            mode = "PASSIVE"
            timeout = 15
        elif avg_slippage > 5:
            mode = "MODERATE"
            timeout = 10
        else:
            mode = "AGGRESSIVE"
            timeout = 5
        
        return {
            "agent": self.name,
            "execution_mode": mode,
            "suggested_timeout": timeout
        }


# 5. AnalystAgent
class AnalystAgent(BaseAgent):
    """
    "The Historian" - Historian. Recalls past similarities.
    Now enhanced with Strategic Memory Engine (SME) for institutional memory.
    """
    
    def __init__(self, memory_module: RAGMemory, sme=None):
        """
        Initialize AnalystAgent.
        
        Args:
            memory_module: RAG Memory for recent episodes
            sme: Strategic Memory Engine for long-term institutional memory (optional)
        """
        super().__init__(
            "AnalystAgent",
            "Historian. Recalls past similarities. Enhanced with Strategic Memory Engine."
        )
        self.memory = memory_module
        self.sme = sme  # Strategic Memory Engine (Level 8)
    
    def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override to use RAG Memory + Strategic Memory Engine for historical context.
        """
        regime = context.get('market_regime', context.get('regime', 'UNKNOWN'))
        history = self.memory.retrieve_relevant_episodes(regime, limit=3)
        
        # Consult SME for strategic insights (Level 8)
        sme_insights = {}
        champion_strategies = []
        if self.sme:
            try:
                # Get top performers for this regime using query_best_strategies
                best_strategies = self.sme.query_best_strategies(regime)
                # Convert to dict format for compatibility
                champion_strategies = [
                    {"strategy_name": name, "win_rate": win_rate * 100}
                    for name, win_rate in best_strategies[:3]
                ]
                
                # Get seasonality patterns if available
                day_of_week = self._get_day_of_week(context)
                if day_of_week:
                    seasonality = self.sme.analyze_seasonality()
                    sme_insights["seasonality"] = seasonality.get(day_of_week, "UNKNOWN")
                
                sme_insights["champion_strategies"] = champion_strategies
                sme_insights["regime_fit"] = len(champion_strategies) > 0
            except Exception as e:
                logger.warning(f"[{self.name}] SME query failed: {e}")
        
        if not self.llm or not self.llm.is_available():
            # Heuristic fallback with SME insights
            insight = f"Found {len(history)} similar days. Win rate was usually {self._avg_win(history):.1f}%."
            
            if champion_strategies:
                top_strat = champion_strategies[0]
                insight += f" SME Champion: {top_strat.get('strategy_name', 'N/A')} (Win Rate: {top_strat.get('win_rate', 0):.1f}%)"
            
            return {
                "agent": self.name,
                "historical_precedent": history,
                "sme_insights": sme_insights,
                "champion_strategies": champion_strategies,
                "insight": insight
            }
        
        # Use LLM if available
        prompt = self._construct_prompt(context, history, sme_insights)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": f"You are {self.name}, {self.role}. Analyze historical context and respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                # GPT-5 uses default temperature
            )
            result_text = response.choices[0].message.content
            result = self._parse_json(result_text)
            result["historical_precedent"] = history
            result["sme_insights"] = sme_insights
            result["champion_strategies"] = champion_strategies
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return {
                "agent": self.name,
                "historical_precedent": history,
                "sme_insights": sme_insights,
                "champion_strategies": champion_strategies,
                "insight": f"Found {len(history)} similar days. Win rate was usually {self._avg_win(history):.1f}%."
            }
    
    def _construct_prompt(self, context: Dict[str, Any], history: list = None, sme_insights: Dict = None) -> str:
        regime = context.get('market_regime', context.get('regime', 'UNKNOWN'))
        history = history or []
        sme_insights = sme_insights or {}
        champion_strategies = sme_insights.get("champion_strategies", [])
        
        return f"""
You are the AnalystAgent. Analyze historical patterns with Strategic Memory Engine (SME) insights.

CURRENT REGIME: {regime}
HISTORICAL EPISODES (RAG Memory): {len(history)}

{json.dumps(history[:3], indent=2) if history else "No similar episodes found"}

STRATEGIC MEMORY ENGINE (SME) - CHAMPION STRATEGIES:
{json.dumps(champion_strategies, indent=2) if champion_strategies else "No SME data available for this regime"}

Analyze what worked/didn't work in similar past situations.
Consider both recent episodes (RAG Memory) and long-term champions (SME).
Recommend favoring champion strategies that have proven successful in this regime.

Output JSON: {{ "insight": "...", "historical_match": "STRONG|MODERATE|WEAK", "recommendation": "...", "champion_recommendation": "..." }}
"""
    
    def _avg_win(self, history: list) -> float:
        """Calculate average win rate from history."""
        if not history:
            return 0.0
        win_rates = [h.get('win_rate', 0.0) for h in history]
        return (sum(win_rates) / len(win_rates) * 100) if win_rates else 0.0
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        regime = context.get('market_regime', context.get('regime', 'UNKNOWN'))
        history = self.memory.retrieve_relevant_episodes(regime, limit=3)
        
        # Consult SME if available
        sme_insights = {}
        champion_strategies = []
        if self.sme:
            try:
                # Get top performers for this regime using query_best_strategies
                best_strategies = self.sme.query_best_strategies(regime)
                # Convert to dict format for compatibility
                champion_strategies = [
                    {"strategy_name": name, "win_rate": win_rate * 100}
                    for name, win_rate in best_strategies[:3]
                ]
                
                sme_insights = {
                    "champion_strategies": champion_strategies,
                    "regime_fit": len(champion_strategies) > 0
                }
            except Exception as e:
                logger.warning(f"[{self.name}] SME query failed in fallback: {e}")
        
        insight = f"Found {len(history)} similar days. Win rate was usually {self._avg_win(history):.1f}%."
        
        if champion_strategies:
            top_strat = champion_strategies[0]
            insight += f" SME Champion: {top_strat.get('strategy_name', 'N/A')} (Win Rate: {top_strat.get('win_rate', 0):.1f}%)"
        
        return {
            "agent": self.name,
            "historical_precedent": history,
            "sme_insights": sme_insights,
            "champion_strategies": champion_strategies,
            "insight": insight,
            "historical_match": "MODERATE" if history else "NONE"
        }
    
    def _get_day_of_week(self, context: Dict[str, Any]) -> Optional[str]:
        """Extract day of week from context timestamp"""
        try:
            timestamp = context.get("timestamp")
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime("%A").upper()
        except Exception:
            pass
        return None


# 6. AllocatorAgent
class AllocatorAgent(BaseAgent):
    """
    "The Treasurer" - Portfolio Manager. Allocates capital efficiently.
    """
    
    def __init__(self):
        super().__init__(
            "AllocatorAgent",
            "Portfolio Manager. Allocates capital efficiently."
        )
    
    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        market_analysis = context.get('market_analysis', {})
        strategy_recs = context.get('strategy_recs', {})
        risk_analysis = context.get('risk_analysis', {})
        defcon = risk_analysis.get('defcon_level', 5) if isinstance(risk_analysis, dict) else 5
        
        return f"""
You are the AllocatorAgent. Distribute capital based on inputs.

INPUTS:
- Market: {json.dumps(market_analysis, indent=2)}
- Strategy Recs: {json.dumps(strategy_recs, indent=2)}
- Risk DEFCON: {defcon}

Propose weights (0.0 to 1.0) for active strategies. Total must be <= 1.0.

Output JSON: {{ "allocations": {{ "trend_credit_spread": 0.4, ... }} }}
"""
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        strategy_recs = context.get('strategy_recs', {})
        risk_analysis = context.get('risk_analysis', {})
        defcon = risk_analysis.get('defcon_level', 5) if isinstance(risk_analysis, dict) else 5
        
        # Base allocations
        allocations = {}
        total = 0.0
        
        for strategy, rec in strategy_recs.items():
            if rec == "SCALE_UP":
                weight = 0.3
            elif rec == "HOLD":
                weight = 0.2
            elif rec == "PAUSE":
                weight = 0.0
            else:
                weight = 0.1
            allocations[strategy] = weight
            total += weight
        
        # Apply DEFCON multiplier
        if defcon <= 2:
            multiplier = 0.5
        elif defcon == 3:
            multiplier = 0.7
        elif defcon == 4:
            multiplier = 0.9
        else:
            multiplier = 1.0
        
        # Normalize
        if total > 0:
            for strategy in allocations:
                allocations[strategy] = (allocations[strategy] / total) * multiplier
        
        return {
            "agent": self.name,
            "allocations": allocations if allocations else {"default": 0.5}
        }


# 7. RefereeAgent
class RefereeAgent(BaseAgent):
    """
    "The Judge" - Supreme Decision Maker. Resolves conflicts and issues final directives.
    """
    
    def __init__(self):
        super().__init__(
            "RefereeAgent",
            "Supreme Decision Maker. Resolves conflicts and issues final directives."
        )
    
    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        market_analysis = context.get('market_analysis', {})
        strategy_recs = context.get('strategy_recs', {})
        risk_analysis = context.get('risk_analysis', {})
        exec_analysis = context.get('exec_analysis', {})
        historical_context = context.get('historical_context', {})
        allocation_proposal = context.get('allocation_proposal', {})
        
        return f"""
You are the RefereeAgent. Review the Board Meeting notes and issue a Binding Directive.

BOARD MEETING NOTES:
- Market: {json.dumps(market_analysis, indent=2)}
- Strategy: {json.dumps(strategy_recs, indent=2)}
- Risk: {json.dumps(risk_analysis, indent=2)}
- Execution: {json.dumps(exec_analysis, indent=2)}
- History: {json.dumps(historical_context, indent=2)}
- Allocator Proposal: {json.dumps(allocation_proposal, indent=2)}

DECISION LOGIC:
1. If Risk DEFCON < 3, override Allocator and cut sizes by 50%.
2. If Market is CHAOTIC, pause all buying.
3. Otherwise, approve Allocator.

Output JSON: 
{{ 
    "final_directive": "APPROVE_ALLOCATION", 
    "approved_allocations": {{...}}, 
    "global_override": "NONE",
    "reasoning": "..."
}}
"""
    
    def _heuristic_fallback(self, context: Dict[str, Any], llm_error: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        market_analysis = context.get('market_analysis', {})
        risk_analysis = context.get('risk_analysis', {})
        allocation_proposal = context.get('allocation_proposal', {})
        
        regime = market_analysis.get('regime', 'UNKNOWN') if isinstance(market_analysis, dict) else 'UNKNOWN'
        defcon = risk_analysis.get('defcon_level', 5) if isinstance(risk_analysis, dict) else 5
        allocations = allocation_proposal.get('allocations', {}) if isinstance(allocation_proposal, dict) else {}
        
        # Get net_delta from context for conditional logic
        net_delta = abs(context.get('net_delta', 0))
        
        # Apply decision logic
        if defcon < 3:
            # Cut sizes by 50%
            approved_allocations = {k: v * 0.5 for k, v in allocations.items()}
            directive = "REDUCE_ALLOCATION"
            override = "DEFCON_OVERRIDE"
            reasoning = f"Risk DEFCON {defcon} requires 50% size reduction"
        elif regime == "CHAOTIC":
            # Pause all buying
            approved_allocations = {k: 0.0 for k in allocations.keys()}
            directive = "PAUSE_ALL"
            override = "CHAOTIC_MARKET"
            reasoning = "Market is CHAOTIC - pausing all new positions"
        elif defcon == 4:
            # DEFCON 4: Conditional approval with risk warnings
            # Cap strategies that are risky (e.g., trend strategies with high delta exposure)
            approved_allocations = {}
            for strat, weight in allocations.items():
                # Cap trend strategies if delta is high
                if "trend" in strat.lower() and net_delta > 50:
                    approved_allocations[strat] = weight * 0.5  # Cap at 50%
                else:
                    approved_allocations[strat] = weight
            directive = "CONDITIONAL_APPROVE"
            override = "RISK_WARNING"
            reasoning = f"Approve Allocation but cap Trend Strategy due to Risk Warning (DEFCON {defcon}, Delta: {net_delta})"
        else:
            # Approve allocator
            approved_allocations = allocations
            directive = "APPROVE_ALLOCATION"
            override = "NONE"
            reasoning = "All conditions normal - approving allocation"
        
        return {
            "agent": self.name,
            "final_directive": directive,
            "approved_allocations": approved_allocations,
            "global_override": override,
            "reasoning": reasoning
        }
