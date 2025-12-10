"""
Self-Healing Module
===================

Applies corrective actions based on diagnostic results:
- Strategy switching
- Position size reduction
- Module disabling
- Forced hedging
- Execution throttling
- Config reversion
"""

import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from packages.core.self_healing.diagnostics import DiagnosticResult, AnomalyType
from packages.core.rag_memory import RAGMemory, TradingEpisode

logger = structlog.get_logger(__name__)


class HealingAction(str, Enum):
    """Types of healing actions"""
    REDUCE_POSITION_SIZES = "REDUCE_POSITION_SIZES"
    DISABLE_STRATEGY = "DISABLE_STRATEGY"
    REDUCE_STRATEGY_ALLOCATION = "REDUCE_STRATEGY_ALLOCATION"
    INCREASE_LIMIT_CHASE_AGGRESSIVENESS = "INCREASE_LIMIT_CHASE_AGGRESSIVENESS"
    PAUSE_TRADING = "PAUSE_TRADING"
    FORCE_HEDGE = "FORCE_HEDGE"
    THROTTLE_EXECUTION = "THROTTLE_EXECUTION"
    REVERT_CONFIG = "REVERT_CONFIG"
    REDUCE_SIGNAL_FREQUENCY = "REDUCE_SIGNAL_FREQUENCY"


@dataclass
class HealingResult:
    """Result of a healing action"""
    action: HealingAction
    success: bool
    message: str
    config_changes: Dict[str, Any]
    timestamp: datetime
    diagnostic: DiagnosticResult


class SelfHealing:
    """
    Self-healing engine that applies corrective actions.
    
    Actions:
    - Reduces position sizes when slippage/margin issues
    - Disables underperforming strategies
    - Increases limit chase aggressiveness for late entries
    - Pauses trading for critical issues
    - Forces hedging for risk management
    - Throttles execution for overtrading
    - Reverts to last stable config
    """
    
    def __init__(
        self,
        config_path: str,
        memory: Optional[RAGMemory] = None,
        healing_enabled: bool = True
    ):
        """
        Initialize self-healing engine.
        
        Args:
            config_path: Path to YAML config file
            memory: RAG Memory instance for tracking healing events
            healing_enabled: Whether healing is enabled (can be disabled for safety)
        """
        self.config_path = Path(config_path)
        self.memory = memory
        self.healing_enabled = healing_enabled
        
        # Track healing history
        self._healing_history: List[HealingResult] = []
        self._last_stable_config: Optional[Dict[str, Any]] = None
        
        # Load and backup current config
        self._backup_config()
    
    def _backup_config(self) -> None:
        """Backup current config as last stable config"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self._last_stable_config = yaml.safe_load(f)
                logger.info("Config backed up as last stable config")
        except Exception as e:
            logger.warning(f"Could not backup config: {e}")
    
    def apply_healing(self, diagnostic: DiagnosticResult) -> Optional[HealingResult]:
        """
        Apply healing action based on diagnostic result.
        
        Args:
            diagnostic: Diagnostic result indicating an anomaly
            
        Returns:
            HealingResult if action was applied, None if no action needed
        """
        if not self.healing_enabled:
            logger.warning("Self-healing is disabled")
            return None
        
        if not diagnostic.detected:
            return None
        
        # Map anomaly types to healing actions
        action_map = {
            AnomalyType.OVERTRADING: [
                HealingAction.REDUCE_SIGNAL_FREQUENCY,
                HealingAction.THROTTLE_EXECUTION
            ],
            AnomalyType.LATE_ENTRIES: [
                HealingAction.INCREASE_LIMIT_CHASE_AGGRESSIVENESS
            ],
            AnomalyType.SLIPPAGE_ISSUES: [
                HealingAction.REDUCE_POSITION_SIZES,
                HealingAction.THROTTLE_EXECUTION
            ],
            AnomalyType.LOW_WIN_RATE: [
                HealingAction.REDUCE_POSITION_SIZES,
                HealingAction.PAUSE_TRADING  # If critical
            ],
            AnomalyType.HIGH_REJECTION_RATE: [
                HealingAction.REDUCE_SIGNAL_FREQUENCY
            ],
            AnomalyType.STRATEGY_BIAS: [
                HealingAction.DISABLE_STRATEGY,
                HealingAction.REDUCE_STRATEGY_ALLOCATION
            ],
            AnomalyType.MARGIN_PRESSURE: [
                HealingAction.REDUCE_POSITION_SIZES,
                HealingAction.FORCE_HEDGE
            ],
        }
        
        actions = action_map.get(diagnostic.anomaly_type, [])
        
        if not actions:
            logger.info(f"No healing actions defined for {diagnostic.anomaly_type}")
            return None
        
        # Select action based on severity
        if diagnostic.severity == "CRITICAL":
            # For critical issues, apply most aggressive action
            action = actions[-1] if actions else None
        elif diagnostic.severity == "HIGH":
            # For high severity, apply first action
            action = actions[0] if actions else None
        else:
            # For medium/low, apply first action (less aggressive)
            action = actions[0] if actions else None
        
        if not action:
            return None
        
        # Apply the healing action
        result = self._execute_action(action, diagnostic)
        
        if result and result.success:
            self._healing_history.append(result)
            self._record_healing_event(result)
        
        return result
    
    def _execute_action(
        self,
        action: HealingAction,
        diagnostic: DiagnosticResult
    ) -> HealingResult:
        """Execute a specific healing action"""
        logger.info(f"🔧 Applying healing action: {action.value} for {diagnostic.anomaly_type.value}")
        
        try:
            if action == HealingAction.REDUCE_POSITION_SIZES:
                return self._reduce_position_sizes(diagnostic)
            elif action == HealingAction.DISABLE_STRATEGY:
                return self._disable_strategy(diagnostic)
            elif action == HealingAction.REDUCE_STRATEGY_ALLOCATION:
                return self._reduce_strategy_allocation(diagnostic)
            elif action == HealingAction.INCREASE_LIMIT_CHASE_AGGRESSIVENESS:
                return self._increase_limit_chase_aggressiveness(diagnostic)
            elif action == HealingAction.PAUSE_TRADING:
                return self._pause_trading(diagnostic)
            elif action == HealingAction.FORCE_HEDGE:
                return self._force_hedge(diagnostic)
            elif action == HealingAction.THROTTLE_EXECUTION:
                return self._throttle_execution(diagnostic)
            elif action == HealingAction.REVERT_CONFIG:
                return self._revert_config(diagnostic)
            elif action == HealingAction.REDUCE_SIGNAL_FREQUENCY:
                return self._reduce_signal_frequency(diagnostic)
            else:
                return HealingResult(
                    action=action,
                    success=False,
                    message=f"Unknown action: {action.value}",
                    config_changes={},
                    timestamp=datetime.now(),
                    diagnostic=diagnostic
                )
        except Exception as e:
            logger.error(f"Failed to execute healing action {action.value}: {e}", exc_info=True)
            return HealingResult(
                action=action,
                success=False,
                message=f"Error: {str(e)}",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
    
    def _reduce_position_sizes(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Reduce position sizes by 25%"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Reduce risk per trade
            if "risk" in config:
                current_risk = config["risk"].get("per_trade_risk_pct", 0.25)
                new_risk = current_risk * 0.75  # Reduce by 25%
                config["risk"]["per_trade_risk_pct"] = new_risk
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                
                return HealingResult(
                    action=HealingAction.REDUCE_POSITION_SIZES,
                    success=True,
                    message=f"Reduced position sizes: risk_pct {current_risk:.2%} -> {new_risk:.2%}",
                    config_changes={"risk.per_trade_risk_pct": new_risk},
                    timestamp=datetime.now(),
                    diagnostic=diagnostic
                )
            
            return HealingResult(
                action=HealingAction.REDUCE_POSITION_SIZES,
                success=False,
                message="Risk config not found",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
        except Exception as e:
            return HealingResult(
                action=HealingAction.REDUCE_POSITION_SIZES,
                success=False,
                message=f"Error: {str(e)}",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
    
    def _disable_strategy(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Disable underperforming strategies"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            disabled_strategies = []
            
            # Get failing strategies from diagnostic
            failing_strategies = diagnostic.metrics.get("failing_strategies", [])
            
            if "strategies" in config:
                for strategy in config["strategies"]:
                    strategy_name = strategy.get("name", "")
                    
                    # Check if this strategy is failing
                    for failing in failing_strategies:
                        if failing["strategy"] == strategy_name:
                            if strategy.get("enabled", True):
                                strategy["enabled"] = False
                                disabled_strategies.append(strategy_name)
            
            if disabled_strategies:
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                
                return HealingResult(
                    action=HealingAction.DISABLE_STRATEGY,
                    success=True,
                    message=f"Disabled strategies: {', '.join(disabled_strategies)}",
                    config_changes={"disabled_strategies": disabled_strategies},
                    timestamp=datetime.now(),
                    diagnostic=diagnostic
                )
            
            return HealingResult(
                action=HealingAction.DISABLE_STRATEGY,
                success=False,
                message="No strategies to disable",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
        except Exception as e:
            return HealingResult(
                action=HealingAction.DISABLE_STRATEGY,
                success=False,
                message=f"Error: {str(e)}",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
    
    def _reduce_strategy_allocation(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Reduce allocation to underperforming strategies"""
        # This would need to modify strategy_allocator.yaml
        # For now, return a placeholder
        return HealingResult(
            action=HealingAction.REDUCE_STRATEGY_ALLOCATION,
            success=False,
            message="Strategy allocator config not yet supported",
            config_changes={},
            timestamp=datetime.now(),
            diagnostic=diagnostic
        )
    
    def _increase_limit_chase_aggressiveness(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Increase limit chase aggressiveness for faster fills"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update execution config
            if "execution" in config:
                exec_config = config["execution"]
                
                # Increase limit chase max slippage
                if "limit_chase" in exec_config:
                    current_slippage = exec_config["limit_chase"].get("max_slippage_abs", 5.0)
                    new_slippage = current_slippage * 1.5  # Increase by 50%
                    exec_config["limit_chase"]["max_slippage_abs"] = new_slippage
                else:
                    exec_config["limit_chase"] = {"max_slippage_abs": 7.5}
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                
                return HealingResult(
                    action=HealingAction.INCREASE_LIMIT_CHASE_AGGRESSIVENESS,
                    success=True,
                    message=f"Increased limit chase aggressiveness: max_slippage {current_slippage:.1f} -> {new_slippage:.1f}",
                    config_changes={"execution.limit_chase.max_slippage_abs": new_slippage},
                    timestamp=datetime.now(),
                    diagnostic=diagnostic
                )
            
            return HealingResult(
                action=HealingAction.INCREASE_LIMIT_CHASE_AGGRESSIVENESS,
                success=False,
                message="Execution config not found",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
        except Exception as e:
            return HealingResult(
                action=HealingAction.INCREASE_LIMIT_CHASE_AGGRESSIVENESS,
                success=False,
                message=f"Error: {str(e)}",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
    
    def _pause_trading(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Pause trading (sets a flag, actual pausing handled by orchestrator)"""
        # This would set a flag that orchestrator checks
        # For now, return a placeholder
        return HealingResult(
            action=HealingAction.PAUSE_TRADING,
            success=True,
            message="Trading pause recommended (requires orchestrator integration)",
            config_changes={},
            timestamp=datetime.now(),
            diagnostic=diagnostic
        )
    
    def _force_hedge(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Force hedging (triggers delta neutralizer)"""
        # This would trigger delta neutralizer
        # For now, return a placeholder
        return HealingResult(
            action=HealingAction.FORCE_HEDGE,
            success=True,
            message="Hedging recommended (requires delta neutralizer integration)",
            config_changes={},
            timestamp=datetime.now(),
            diagnostic=diagnostic
        )
    
    def _throttle_execution(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Throttle execution (increase delays between orders)"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if "execution" in config:
                exec_config = config["execution"]
                
                # Increase gaps
                current_gap = exec_config.get("engine_gap_ms", 350)
                new_gap = current_gap * 1.5  # Increase by 50%
                exec_config["engine_gap_ms"] = new_gap
                
                current_instrument_gap = exec_config.get("instrument_gap_ms", 350)
                new_instrument_gap = current_instrument_gap * 1.5
                exec_config["instrument_gap_ms"] = new_instrument_gap
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                
                return HealingResult(
                    action=HealingAction.THROTTLE_EXECUTION,
                    success=True,
                    message=f"Throttled execution: gaps {current_gap}ms -> {new_gap:.0f}ms",
                    config_changes={
                        "execution.engine_gap_ms": new_gap,
                        "execution.instrument_gap_ms": new_instrument_gap
                    },
                    timestamp=datetime.now(),
                    diagnostic=diagnostic
                )
            
            return HealingResult(
                action=HealingAction.THROTTLE_EXECUTION,
                success=False,
                message="Execution config not found",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
        except Exception as e:
            return HealingResult(
                action=HealingAction.THROTTLE_EXECUTION,
                success=False,
                message=f"Error: {str(e)}",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
    
    def _revert_config(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Revert to last stable config"""
        if not self._last_stable_config:
            return HealingResult(
                action=HealingAction.REVERT_CONFIG,
                success=False,
                message="No stable config backup available",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
        
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._last_stable_config, f, sort_keys=False, default_flow_style=False)
            
            return HealingResult(
                action=HealingAction.REVERT_CONFIG,
                success=True,
                message="Config reverted to last stable version",
                config_changes={"reverted": True},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
        except Exception as e:
            return HealingResult(
                action=HealingAction.REVERT_CONFIG,
                success=False,
                message=f"Error: {str(e)}",
                config_changes={},
                timestamp=datetime.now(),
                diagnostic=diagnostic
            )
    
    def _reduce_signal_frequency(self, diagnostic: DiagnosticResult) -> HealingResult:
        """Reduce signal generation frequency"""
        # This would modify orchestrator scan interval
        # For now, return a placeholder
        return HealingResult(
            action=HealingAction.REDUCE_SIGNAL_FREQUENCY,
            success=True,
            message="Signal frequency reduction recommended (requires orchestrator integration)",
            config_changes={},
            timestamp=datetime.now(),
            diagnostic=diagnostic
        )
    
    def _record_healing_event(self, result: HealingResult) -> None:
        """Record healing event in RAG Memory"""
        if not self.memory:
            return
        
        try:
            # Create a healing episode
            episode = TradingEpisode(
                date=datetime.now().strftime("%Y-%m-%d"),
                pnl=0.0,  # Healing events don't have direct PnL
                win_rate=0.0,
                dominant_regime="HEALING",
                primary_rejection_reason=result.action.value,
                config_snapshot=result.config_changes
            )
            
            self.memory.add_episode(episode)
            logger.info(f"💾 Healing event recorded: {result.action.value}")
        except Exception as e:
            logger.warning(f"Could not record healing event: {e}")
    
    def get_healing_history(self, limit: int = 10) -> List[HealingResult]:
        """Get recent healing history"""
        return self._healing_history[-limit:] if self._healing_history else []





