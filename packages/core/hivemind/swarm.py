"""
HiveMind Swarm Controller - Level 7
====================================

The orchestrator that conducts the "Board Meeting" with all 7 agents.
"""

import logging
import yaml
from typing import Dict, Any

from packages.core.hivemind.agents import (
    MarketAgent, StrategyAgent, RiskAgent, ExecutionAgent,
    AnalystAgent, AllocatorAgent, RefereeAgent
)
# Note: RAGMemory is in packages.core.rag_memory (not intelligence.memory)
from packages.core.rag_memory import RAGMemory
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter

logger = logging.getLogger("hivemind")


class HiveMindSwarm:
    """
    Level 7 Intelligence: A Multi-Agent System for Governance.
    
    Conducts real-time "Board Meetings" where all 7 agents:
    1. Analyze current trading context
    2. Provide their perspectives
    3. Vote on decisions
    4. Issue binding directives
    5. Enforce allocations
    """
    
    def __init__(self, config_path: str, sme=None, kite_mcp_adapter: KiteMCPAdapter = None):
        """
        Initialize the HiveMind Swarm.
        
        Args:
            config_path: Path to YAML config file to update with allocations
            sme: Strategic Memory Engine instance (optional, Level 8)
            kite_mcp_adapter: Optional KiteMCPAdapter for MCP tool access
        """
        self.config_path = config_path
        self.memory = RAGMemory()
        self.sme = sme  # Strategic Memory Engine (Level 8)
        self.kite_mcp_adapter = kite_mcp_adapter  # MCP adapter for Kite data
        
        # Initialize The Council
        self.agents = {
            "market": MarketAgent(),
            "strategy": StrategyAgent(),
            "risk": RiskAgent(),
            "execution": ExecutionAgent(),
            "analyst": AnalystAgent(self.memory, sme=self.sme),  # Enhanced with SME
            "allocator": AllocatorAgent(),
            "referee": RefereeAgent()
        }
        
        # Pass MCP adapter to agents that need it
        if self.kite_mcp_adapter:
            # Agents can access adapter through swarm instance
            logger.info("🧠 HiveMind Swarm initialized with Kite MCP adapter")
        
        if self.sme:
            logger.info("🧠 HiveMind Swarm initialized - The Council of Seven is ready (Enhanced with SME Level 8)")
        else:
            logger.info("🧠 HiveMind Swarm initialized - The Council of Seven is ready")
    
    def run_council_meeting(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete council meeting - all agents analyze and vote.
        
        Args:
            current_state: Current trading state dictionary
        
        Returns:
            Dictionary with verdict and all agent insights
        """
        logger.info("🧠 HIVEMIND: Calling Council to Order...")
        
        # Phase 1: Perception & Analysis (Parallelizable)
        # In a real async system, these would run concurrently
        market_insight = self.agents["market"].think(current_state)
        strategy_insight = self.agents["strategy"].think(current_state)
        risk_insight = self.agents["risk"].think(current_state)
        exec_insight = self.agents["execution"].think(current_state)
        
        # Inject Market Regime into Analyst Context
        current_state['market_regime'] = market_insight.get('regime', 'UNKNOWN')
        history_insight = self.agents["analyst"].think(current_state)
        
        # Phase 2: Synthesis
        synthesis_context = {
            "market_analysis": market_insight,
            "strategy_recs": strategy_insight.get("recommendations", {}) if isinstance(strategy_insight, dict) else {},
            "risk_analysis": risk_insight,
            "exec_analysis": exec_insight,
            "historical_context": history_insight,
            # Pass through key state variables for RefereeAgent
            "net_delta": current_state.get("net_delta", 0),
            "regime": current_state.get("market_regime", "UNKNOWN")
        }
        
        # Phase 3: Allocation Proposal
        alloc_proposal = self.agents["allocator"].think(synthesis_context)
        synthesis_context["allocation_proposal"] = alloc_proposal
        
        # Phase 4: Final Judgment
        verdict = self.agents["referee"].think(synthesis_context)
        
        logger.info(f"🧠 HIVEMIND VERDICT: {verdict.get('final_directive')} | {verdict.get('reasoning')}")
        
        # Phase 5: Enforcement (Apply to Config)
        if verdict.get("approved_allocations"):
            self._enforce_allocations(verdict["approved_allocations"])
        
        # Build comprehensive transparency report with all agent insights
        final_report = {
            # Referee's final decision (existing structure)
            "final_directive": verdict.get("final_directive", "PROCEED"),
            "reasoning": verdict.get("reasoning", ""),
            "approved_allocations": verdict.get("approved_allocations", {}),
            "voting_summary": verdict.get("voting_summary", {}),
            
            # Full agent insights for transparency
            "market_analysis": market_insight,
            "strategy_recs": strategy_insight if isinstance(strategy_insight, dict) else {"recommendations": strategy_insight},
            "risk_analysis": risk_insight,
            "exec_analysis": exec_insight,
            "historical_context": history_insight,
            "allocation_proposal": alloc_proposal,
            
            # Structured agent insights (for backward compatibility and clarity)
            "agent_insights": {
                "MarketAgent": market_insight,
                "StrategyAgent": strategy_insight if isinstance(strategy_insight, dict) else {"recommendations": strategy_insight},
                "RiskAgent": risk_insight,
                "ExecutionAgent": exec_insight,
                "AnalystAgent": history_insight,
                "AllocatorAgent": alloc_proposal,
                "RefereeAgent": verdict
            },
            
            # Metadata
            "timestamp": current_state.get("timestamp"),
            "context_snapshot": {
                "vix": current_state.get("vix", "N/A"),
                "regime": current_state.get("market_regime", "UNKNOWN"),
                "trend": current_state.get("trend", "N/A"),
                "pnl": current_state.get("pnl", 0.0),
                "net_delta": current_state.get("net_delta", 0)
            }
        }
        
        return final_report
    
    def _enforce_allocations(self, allocations: Dict[str, float]) -> None:
        """
        Updates the live YAML config with new weights.
        
        Args:
            allocations: Dictionary of strategy name -> allocation weight
        """
        try:
            from pathlib import Path
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Update Strategies
            strategies = config.get("strategies", {})
            changes = False
            
            for strat, weight in allocations.items():
                if strat in strategies:
                    # Assuming 'max_portfolio_heat' controls allocation size
                    old = strategies[strat].get("max_portfolio_heat", 0.0)
                    if old != weight:
                        strategies[strat]["max_portfolio_heat"] = weight
                        changes = True
                        logger.info(f"⚖️  Adjusting {strat}: {old} -> {weight}")
            
            if changes:
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False)
                logger.info("✅ HiveMind Directives Enforced.")
            else:
                logger.info("ℹ️  No allocation changes needed.")
                
        except Exception as e:
            logger.error(f"Failed to enforce HiveMind directives: {e}", exc_info=True)
    
    def convene_council(
        self,
        orchestrator: Any = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Convene a "Board Meeting" - wrapper for run_council_meeting.
        
        This method maintains backward compatibility with the previous interface.
        
        Args:
            orchestrator: TradingOrchestrator instance (optional, for state extraction)
            context: Pre-built context dictionary (optional)
        
        Returns:
            Dictionary with verdict and all agent insights
        """
        # Build context if not provided
        if context is None:
            context = self._build_context(orchestrator)
        
        # Run council meeting
        verdict = self.run_council_meeting(context)
        
        # Return in expected format
        return {
            "agent_insights": {
                "MarketAgent": context.get("market_analysis", {}),
                "StrategyAgent": context.get("strategy_recs", {}),
                "RiskAgent": context.get("risk_analysis", {}),
                "ExecutionAgent": context.get("exec_analysis", {}),
                "AnalystAgent": context.get("historical_context", {}),
                "AllocatorAgent": context.get("allocation_proposal", {}),
                "RefereeAgent": verdict
            },
            "binding_directive": verdict,
            "voting_summary": verdict.get("voting_summary", {}),
            "timestamp": context.get("timestamp")
        }
    
    def _build_context(self, orchestrator: Any = None) -> Dict[str, Any]:
        """
        Build comprehensive context for agents.
        
        Args:
            orchestrator: TradingOrchestrator instance
        
        Returns:
            Dictionary with all context needed by agents
        """
        from datetime import datetime
        
        context = {
            "timestamp": datetime.now().isoformat(),
            "regime": "UNKNOWN",
            "market_regime": "UNKNOWN",
            "vix": "N/A",
            "trend": "N/A",
            "events": "None",
            "iv_percentile": 0.5,
            "market_data_connected": False,
            "portfolio_risk": {
                "daily_pnl": 0.0,
                "portfolio_heat_pct": 0.0,
                "available_margin": 0.0,
                "margin_utilization_pct": 0.0,
                "net_liquid": 1000000.0,
                "used_margin": 0.0
            },
            "execution_stats": {
                "avg_slippage_bps": 0.0,
                "avg_slippage": 0.0,
                "avg_limit_chase_savings_bps": 0.0,
                "chase_savings": 0.0,
                "fill_rate": 1.0,
                "avg_order_latency_ms": 0.0
            },
            "strategy_metrics": {},
            "strategies": {},
            "signals_today": 0,
            "win_rate": 0.0,
            "net_delta": 0,
            "pnl": 0.0,
            "margin_used": 0.0
        }
        
        # If no orchestrator, use default mock state for testing
        if orchestrator is None:
            # Default test scenario: High delta, negative PnL
            context.update({
                "vix": 15.5,
                "trend": "UP",
                "events": "None",
                "net_delta": 120,  # High delta exposure
                "pnl": -5000.0,  # -0.5% of 1M
                "margin_used": 45.0,
                "portfolio_risk": {
                    "daily_pnl": -5000.0,
                    "portfolio_heat_pct": 1.2,
                    "available_margin": 550000.0,
                    "margin_utilization_pct": 45.0,
                    "net_liquid": 1000000.0,
                    "used_margin": 450000.0
                },
                "strategy_metrics": {
                    "trend_credit_spread": {"win_rate": 0.4, "pnl": -1000},
                    "intraday_short_strangle": {"win_rate": 0.8, "pnl": 2000}
                },
                "execution_stats": {
                    "avg_slippage": 2.0,
                    "chase_savings": 1500,
                    "avg_slippage_bps": 2.0,
                    "avg_limit_chase_savings_bps": 1.5
                }
            })
        
        # If MCP adapter available, enrich context with real-time Kite data
        if self.kite_mcp_adapter:
            try:
                portfolio_summary = self.kite_mcp_adapter.get_portfolio_summary()
                if portfolio_summary.get("status") == "success":
                    data = portfolio_summary.get("data", {})
                    capital = data.get("capital", {})
                    positions_data = data.get("positions", {})
                    
                    # Merge MCP data into context
                    context["portfolio_risk"].update({
                        "available_margin": capital.get("available", 0.0),
                        "used_margin": capital.get("used", 0.0),
                        "net_liquid": capital.get("available", 0.0) + capital.get("used", 0.0),
                        "margin_utilization_pct": (capital.get("used", 0.0) / (capital.get("available", 0.0) + capital.get("used", 0.0)) * 100) if (capital.get("available", 0.0) + capital.get("used", 0.0)) > 0 else 0.0,
                        "daily_pnl": capital.get("pnl_day", 0.0)
                    })
                    context["pnl"] = capital.get("pnl_day", 0.0)
                    context["positions"] = positions_data
                    logger.debug("Context enriched with MCP data")
            except Exception as e:
                logger.warning(f"Failed to enrich context with MCP data: {e}")
        
        # If orchestrator provided, extract real state
        if orchestrator:
            try:
                # Get system state
                system_state = orchestrator.get_system_state()
                
                # Portfolio risk
                portfolio_risk = orchestrator._get_portfolio_risk()
                context["portfolio_risk"] = {
                    "daily_pnl": portfolio_risk.daily_pnl,
                    "portfolio_heat_pct": portfolio_risk.portfolio_heat_pct,
                    "available_margin": portfolio_risk.available_margin,
                    "used_margin": portfolio_risk.used_margin,
                    "net_liquid": portfolio_risk.net_liquid,
                    "margin_utilization_pct": (portfolio_risk.used_margin / portfolio_risk.net_liquid * 100) if portfolio_risk.net_liquid > 0 else 0.0
                }
                context["pnl"] = portfolio_risk.daily_pnl
                context["margin_used"] = (portfolio_risk.used_margin / portfolio_risk.net_liquid * 100) if portfolio_risk.net_liquid > 0 else 0.0
                
                # Market data
                context["market_data_connected"] = orchestrator.market_data_stream.is_connected if orchestrator.market_data_stream else False
                
                # Trading stats
                context["signals_today"] = orchestrator.trades_completed_today
                context["win_rate"] = system_state.win_rate if hasattr(system_state, 'win_rate') else 0.0
                
                # Regime (if available)
                if hasattr(orchestrator, 'regime_engine') and orchestrator.regime_engine:
                    try:
                        regime_state = orchestrator.regime_engine.get_current_regime()
                        context["regime"] = regime_state.get("regime", "UNKNOWN")
                        context["market_regime"] = context["regime"]
                        context["iv_percentile"] = regime_state.get("iv_percentile", 0.5)
                    except:
                        pass
                
                # Net delta (if available)
                if hasattr(orchestrator, 'delta_neutralizer') and orchestrator.delta_neutralizer:
                    try:
                        context["net_delta"] = orchestrator.delta_neutralizer.get_net_delta()
                    except:
                        pass
                
                # Execution stats (if available)
                if hasattr(orchestrator, 'execution_engine') and orchestrator.execution_engine:
                    try:
                        # This would need to be implemented in execution engine
                        context["execution_stats"] = {
                            "avg_slippage_bps": 0.0,  # Would come from metrics
                            "avg_slippage": 0.0,
                            "avg_limit_chase_savings_bps": 0.0,
                            "chase_savings": 0.0,
                            "fill_rate": 1.0,
                            "avg_order_latency_ms": 0.0
                        }
                    except:
                        pass
                
                # Strategy metrics (if available)
                if hasattr(orchestrator, 'strategies') and orchestrator.strategies:
                    try:
                        strategy_metrics = {}
                        for strategy in orchestrator.strategies:
                            if hasattr(strategy, 'win_count') and hasattr(strategy, 'loss_count'):
                                total = strategy.win_count + strategy.loss_count
                                win_rate = strategy.win_count / total if total > 0 else 0.0
                                strategy_metrics[strategy.name] = {
                                    "win_rate": win_rate,
                                    "total_trades": total,
                                    "pnl": getattr(strategy, 'total_pnl', 0.0)
                                }
                        context["strategy_metrics"] = strategy_metrics
                    except:
                        pass
                
            except Exception as e:
                logger.warning(f"Failed to extract context from orchestrator: {e}")
        
        return context
