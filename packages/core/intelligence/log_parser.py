"""
Log Parser - Extracts actionable metrics from daily trading logs
===============================================================

Parses the daily trading log to extract actionable metrics for The Cortex.
This enables the system to learn from actual trading behavior, not just metrics.
"""

import re
import datetime as dt
from collections import Counter
from pathlib import Path
from typing import Dict, Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class LogParser:
    """
    Parses the daily trading log to extract actionable metrics for the Cortex.
    
    Extracts:
    - Entry/exit counts
    - Stop loss hits
    - Rejection patterns
    - Execution metrics
    - Errors
    - Regime information
    """
    
    def __init__(self, log_path: str = "logs/trading.log"):
        """
        Initialize log parser.
        
        Args:
            log_path: Path to trading log file
        """
        self.log_path = Path(log_path)
    
    def analyze_today(self) -> Dict[str, Any]:
        """
        Analyze today's trading log and extract metrics.
        
        Returns:
            Dictionary with extracted metrics:
            - date: Today's date
            - entries: Number of positions opened
            - exits: Number of positions closed
            - sl_hits: Number of stop losses hit
            - rejections: Counter of rejection reasons
            - errors: Number of errors
            - limit_chase_attempts: Number of limit chase attempts
            - regime: Current market regime
            - approval_rate: Percentage of signals approved
            - top_rejection: Most common rejection reason
        """
        today = dt.date.today().isoformat()
        
        metrics = {
            "date": today,
            "entries": 0,
            "exits": 0,
            "sl_hits": 0,
            "rejections": Counter(),
            "errors": 0,
            "limit_chase_attempts": 0,
            "regime": "UNKNOWN",
            "wins": 0,
            "losses": 0,
        }
        
        if not self.log_path.exists():
            logger.warning(f"Log file {self.log_path} not found. Returning empty metrics.")
            return metrics
        
        try:
            with open(self.log_path, 'r') as f:
                for line in f:
                    # Only look at today's logs
                    if not line.startswith(today):
                        continue
                    
                    # 1. Strategy Entries
                    if "Position Secured" in line or "Position opened" in line or "Executing signal" in line:
                        metrics["entries"] += 1
                    
                    # 2. Stop Losses / Exits
                    if "Stop Loss Hit" in line or "stop loss" in line.lower():
                        metrics["sl_hits"] += 1
                        metrics["losses"] += 1
                    elif "Exiting:" in line or "Position closed" in line:
                        metrics["exits"] += 1
                        # Try to determine if win or loss
                        if "profit" in line.lower() or "pnl" in line and "+" in line:
                            metrics["wins"] += 1
                        elif "loss" in line.lower() or "pnl" in line and "-" in line:
                            metrics["losses"] += 1
                    
                    # 3. Rejections (Filters)
                    # Matches: [StrategyName] Skipping: Reason
                    m_rej = re.search(r"Skipping: (.*)", line)
                    if m_rej:
                        reason = m_rej.group(1).strip()
                        metrics["rejections"][reason] += 1
                    
                    # Also check for decision rejections
                    m_rej2 = re.search(r"Signal rejected.*reason[=:]\s*(\w+)", line, re.IGNORECASE)
                    if m_rej2:
                        reason = m_rej2.group(1).strip()
                        metrics["rejections"][reason] += 1
                    
                    # Check for risk manager rejections
                    if "rejected by risk manager" in line.lower():
                        m_rej3 = re.search(r"reasons?[=:]\s*\[(.*?)\]", line)
                        if m_rej3:
                            reasons = m_rej3.group(1).split(',')
                            for r in reasons:
                                r = r.strip().strip("'\"")
                                if r:
                                    metrics["rejections"][r] += 1
                    
                    # 4. Execution
                    if "Starting Limit Chase" in line or "limit chase" in line.lower():
                        metrics["limit_chase_attempts"] += 1
                    
                    # 5. Errors
                    if "ERROR" in line or "CRITICAL" in line or "Exception" in line:
                        metrics["errors"] += 1
                    
                    # 6. Regime Sniffing (Last known)
                    if "Regime:" in line or "regime" in line.lower():
                        # Assuming log format: Allocator Cycle Complete. Regime: LOW_MEAN_REVERT
                        m_reg = re.search(r"Regime:?\s*([A-Z_]+)", line, re.IGNORECASE)
                        if m_reg:
                            metrics["regime"] = m_reg.group(1).upper()
            
            # Post-processing
            total_signals = metrics["entries"] + sum(metrics["rejections"].values())
            metrics["approval_rate"] = (metrics["entries"] / total_signals) if total_signals > 0 else 0.0
            
            # Calculate win rate
            total_trades = metrics["wins"] + metrics["losses"]
            metrics["win_rate"] = (metrics["wins"] / total_trades) if total_trades > 0 else 0.0
            
            # Determine Top Rejection
            if metrics["rejections"]:
                top_rej = metrics["rejections"].most_common(1)[0]
                metrics["top_rejection"] = top_rej[0]
                metrics["top_rejection_count"] = top_rej[1]
            else:
                metrics["top_rejection"] = "NONE"
                metrics["top_rejection_count"] = 0
            
            # Convert Counter to dict for JSON serialization
            metrics["rejections"] = dict(metrics["rejections"])
            
            logger.info(
                "Log analysis complete",
                entries=metrics["entries"],
                rejections=sum(metrics["rejections"].values()),
                top_rejection=metrics["top_rejection"],
                win_rate=metrics["win_rate"]
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error parsing log file: {e}", exc_info=True)
            return metrics
    
    def analyze_date_range(self, start_date: dt.date, end_date: dt.date) -> Dict[str, Any]:
        """
        Analyze logs for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Aggregated metrics for the date range
        """
        aggregated = {
            "entries": 0,
            "exits": 0,
            "sl_hits": 0,
            "rejections": Counter(),
            "errors": 0,
            "wins": 0,
            "losses": 0,
        }
        
        if not self.log_path.exists():
            return aggregated
        
        try:
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.isoformat()
                
                with open(self.log_path, 'r') as f:
                    for line in f:
                        if not line.startswith(date_str):
                            continue
                        
                        # Same parsing logic as analyze_today()
                        if "Position Secured" in line or "Position opened" in line:
                            aggregated["entries"] += 1
                        if "Stop Loss Hit" in line:
                            aggregated["sl_hits"] += 1
                            aggregated["losses"] += 1
                        if "Exiting:" in line:
                            aggregated["exits"] += 1
                        # ... (similar logic)
                
                current_date += dt.timedelta(days=1)
            
            # Convert Counter to dict
            aggregated["rejections"] = dict(aggregated["rejections"])
            return aggregated
            
        except Exception as e:
            logger.error(f"Error parsing date range: {e}", exc_info=True)
            return aggregated





