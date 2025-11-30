"""
Kite MCP Adapter for HiveMind
=============================

Standardized Adapter for HiveMind Agents to access Kite Data.

Modes:
1. MCP Mode: Uses Model Context Protocol tools (if configured).
2. SDK Mode: Fallback to direct KiteConnect calls (default).

Usage:
    adapter = KiteMCPAdapter(kite_client=kite, mcp_client=mcp)
    summary = adapter.get_portfolio_summary()
    quotes = adapter.get_market_quote(['NSE:INFY', 'NSE:SBIN'])
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("kite_mcp")


class KiteMCPAdapter:
    """
    Standardized Adapter for HiveMind Agents to access Kite Data.
    
    Modes:
    1. MCP Mode: Uses Model Context Protocol tools (if configured).
    2. SDK Mode: Fallback to direct KiteConnect calls (default).
    """
    
    def __init__(self, kite_client=None, mcp_client=None):
        """
        Initialize the adapter.
        
        Args:
            kite_client: KiteConnect client instance (for SDK mode)
            mcp_client: Optional MCP client for MCP mode
        """
        self.kite = kite_client
        self.mcp = mcp_client
        self.mode = "MCP" if mcp_client else "SDK"
        
        logger.info(f"🔌 KiteMCPAdapter initialized in {self.mode} mode")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Returns a rich context summary for the Council meeting.
        Combines Margins, Positions, and Day's PnL.
        """
        if self.mode == "MCP":
            try:
                return self.mcp.call_tool("kite_get_portfolio_summary", {})
            except Exception as e:
                logger.error(f"MCP get_portfolio_summary failed: {e}")
                # Fall through to SDK fallback
        
        # SDK Fallback Implementation
        if not self.kite:
            return {"status": "error", "message": "No Kite client available"}
        
        try:
            # 1. Margins
            margins = self.kite.margins()
            equity = margins.get("equity", {})
            available_cash = equity.get("net", 0.0)
            utilised = equity.get("utilised", {})
            margin_used = utilised.get("debits", 0.0) + utilised.get("exposure", 0.0)
            
            # 2. Positions
            pos = self.kite.positions()
            net_positions = pos.get("net", [])
            day_pnl = sum(p.get("pnl", 0) for p in net_positions)
            open_positions_count = len([p for p in net_positions if p.get("quantity", 0) != 0])
            
            return {
                "status": "success",
                "data": {
                    "capital": {
                        "available": available_cash,
                        "used": margin_used,
                        "pnl_day": day_pnl
                    },
                    "positions": {
                        "count": open_positions_count,
                        "net_exposure": self._calculate_exposure(net_positions)
                    },
                    "timestamp": "live"
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch portfolio summary: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_market_quote(self, instruments: List[str]) -> Dict[str, Any]:
        """
        Fetches live quotes for a list of symbols.
        
        Args:
            instruments: List of instruments in format ['NSE:INFY', 'NSE:SBIN']
        
        Returns:
            Dictionary with status and quote data
        """
        if self.mode == "MCP":
            try:
                return self.mcp.call_tool("kite_get_quotes", {"symbols": instruments})
            except Exception as e:
                logger.error(f"MCP get_market_quote failed: {e}")
                # Fall through to SDK fallback
        
        if not self.kite:
            return {"status": "error", "message": "No Kite client available"}
        
        try:
            quotes = self.kite.quote(instruments)
            return {"status": "success", "data": quotes}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _calculate_exposure(self, positions: List[Dict[str, Any]]) -> float:
        """
        Calculate net exposure from positions.
        
        Args:
            positions: List of position dictionaries
        
        Returns:
            Total exposure value
        """
        exposure = 0.0
        for p in positions:
            qty = p.get("quantity", 0)
            ltp = p.get("last_price", 0)
            exposure += abs(qty * ltp)
        return exposure
    
    # ========== Additional Methods for Backward Compatibility ==========
    
    def get_positions(self, from_idx: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get current positions (backward compatibility)"""
        if self.mode == "MCP":
            try:
                params = {"from": from_idx}
                if limit:
                    params["limit"] = limit
                result = self.mcp.call_tool("mcp_kite_get_positions", params)
                return result.get("positions", []) if isinstance(result, dict) else result
            except Exception as e:
                logger.error(f"MCP get_positions failed: {e}")
        
        if not self.kite:
            return []
        
        try:
            positions = self.kite.positions()
            return positions.get('net', [])
        except Exception as e:
            logger.error(f"get_positions failed: {e}")
            return []
    
    def get_margins(self) -> Dict[str, Any]:
        """Get margin information (backward compatibility)"""
        if self.mode == "MCP":
            try:
                return self.mcp.call_tool("mcp_kite_get_margins", {})
            except Exception as e:
                logger.error(f"MCP get_margins failed: {e}")
        
        if not self.kite:
            return {}
        
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"get_margins failed: {e}")
            return {}
    
    def get_orders(self, from_idx: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all orders (backward compatibility)"""
        if self.mode == "MCP":
            try:
                params = {"from": from_idx}
                if limit:
                    params["limit"] = limit
                result = self.mcp.call_tool("mcp_kite_get_orders", params)
                return result.get("orders", []) if isinstance(result, dict) else result
            except Exception as e:
                logger.error(f"MCP get_orders failed: {e}")
        
        if not self.kite:
            return []
        
        try:
            return self.kite.orders()
        except Exception as e:
            logger.error(f"get_orders failed: {e}")
            return []
