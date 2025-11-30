"""
HiveMind - Level 7 Multi-Agent Council
======================================

Real-time "Board of Directors" with 7 specialized AI agents that debate,
analyze, and vote on every major trading decision.
"""

from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.agents import (
    MarketAgent, StrategyAgent, RiskAgent, ExecutionAgent,
    AnalystAgent, AllocatorAgent, RefereeAgent
)
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient

__all__ = [
    "HiveMindSwarm",
    "MarketAgent", "StrategyAgent", "RiskAgent", "ExecutionAgent",
    "AnalystAgent", "AllocatorAgent", "RefereeAgent",
    "KiteMCPAdapter", "MCPClient"
]
