#!/usr/bin/env python3
"""
Evolution Cycle - Self-Evolving Trading System
==============================================

Runs end-of-day analysis and config evolution:
1. Collects daily metrics from API
2. Determines current regime
3. Calculates win rate and PnL
4. Analyzes rejection reasons
5. Runs AI Analyst EOD analysis
6. Applies config patches if needed

Usage:
    python3 scripts/run_evolution_cycle.py [--config-path configs/kite_day1_live.yaml]
"""

import sys
import argparse
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.intelligence import AIAnalyst, Cortex
from packages.core.intelligence.log_parser import LogParser
from packages.core.rag_memory import RAGMemory
from packages.core.config import app_config, settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("evolution_cycle")

API_BASE = "http://localhost:8000"


def fetch_metrics() -> str:
    """Fetch Prometheus metrics from API"""
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=10)
        if response.status_code == 200:
            return response.text
        logger.warning(f"Failed to fetch metrics: HTTP {response.status_code}")
        return ""
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return ""


def fetch_state() -> Dict[str, Any]:
    """Fetch system state from API"""
    try:
        response = requests.get(f"{API_BASE}/state", timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"Failed to fetch state: HTTP {response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"Error fetching state: {e}")
        return {}


def fetch_execution_stats() -> Dict[str, Any]:
    """Fetch execution alpha stats from API"""
    try:
        response = requests.get(f"{API_BASE}/api/execution/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        logger.debug(f"Could not fetch execution stats: {e}")
        return {}


def parse_metric(metrics_text: str, metric_name: str, labels: Optional[Dict[str, str]] = None) -> float:
    """Parse a metric value from Prometheus text format"""
    if not metrics_text:
        return 0.0
    
    lines = metrics_text.split('\n')
    for line in lines:
        if line.startswith(metric_name):
            # Handle labels: metric_name{label="value"} value
            if '{' in line:
                # Extract value after closing brace
                if '}' in line:
                    parts = line.split('}')
                    if len(parts) > 1:
                        try:
                            value = float(parts[1].strip().split()[0])
                            return value
                        except (ValueError, IndexError):
                            pass
            else:
                # Simple metric without labels
                if ' ' in line:
                    try:
                        value = float(line.split()[-1])
                        return value
                    except (ValueError, IndexError):
                        pass
    return 0.0


def get_regime_from_metrics(metrics_text: str, underlying: str = "NIFTY") -> str:
    """Get current regime from metrics"""
    regime_code = parse_metric(
        metrics_text, 
        f'algo_vol_regime_code{{underlying="{underlying}"}}'
    )
    
    regime_map = {
        0: "UNKNOWN",
        1: "LOW_MEAN_REVERT",
        2: "MEDIUM_TREND",
        3: "HIGH_EVENT",
        4: "CHAOTIC"
    }
    
    regime = regime_map.get(int(regime_code), "UNKNOWN")
    
    # Also check for HIGH_VOL / LOW_VOL patterns
    if "HIGH" in regime or regime_code >= 3:
        return "HIGH_VOL"
    elif "LOW" in regime or regime_code <= 1:
        return "LOW_VOL"
    else:
        return "MEDIUM_VOL"


def parse_rejection_reasons(metrics_text: str) -> Dict[str, int]:
    """Parse rejection reasons from metrics"""
    rejections = {}
    
    # Common rejection reasons to look for
    rejection_patterns = [
        "MARGIN_LIMIT",
        "WEAK_TREND",
        "RISK_LIMIT",
        "POSITION_LIMIT",
        "LIQUIDITY",
        "TIMEOUT",
        "SLIPPAGE"
    ]
    
    for pattern in rejection_patterns:
        # Try different metric name formats
        metric_names = [
            f'aitrapp_decisions_rejected_total{{reason="{pattern}"}}',
            f'decisions_rejected_total{{reason="{pattern}"}}',
            f'rejections_total{{reason="{pattern}"}}'
        ]
        
        for metric_name in metric_names:
            value = parse_metric(metrics_text, metric_name)
            if value > 0:
                rejections[pattern] = int(value)
                break
    
    return rejections


def collect_daily_metrics(use_log_parser: bool = True) -> Dict[str, Any]:
    """
    Collect all daily metrics needed for EOD analysis.
    
    Returns:
        Dictionary with all metrics for AI Analyst
    """
    logger.info("📊 Collecting daily metrics...")
    
    # Fetch data from API
    metrics_text = fetch_metrics()
    state = fetch_state()
    execution_stats = fetch_execution_stats()
    
    if not metrics_text:
        logger.error("❌ Could not fetch metrics - API may not be running")
        raise RuntimeError("Metrics unavailable")
    
    # Get date
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Get PnL from state or metrics
    daily_pnl = state.get("daily_pnl", 0.0)
    if daily_pnl == 0.0:
        daily_pnl = parse_metric(metrics_text, "aitrapp_daily_pnl")
    
    # Get win rate (prefer log parser, fallback to API/metrics)
    trades_today = state.get("trades_today", 0)
    win_rate = state.get("win_rate", 0.0)
    
    # Prefer log parser win rate if available
    if log_metrics.get("win_rate", 0) > 0:
        win_rate = log_metrics["win_rate"]
        trades_today = log_metrics.get("wins", 0) + log_metrics.get("losses", 0)
    elif win_rate == 0.0 and trades_today > 0:
        # Fallback: calculate from metrics
        wins = parse_metric(metrics_text, "aitrapp_trades_won_total")
        losses = parse_metric(metrics_text, "aitrapp_trades_lost_total")
        total = wins + losses
        if total > 0:
            win_rate = wins / total
    
    # Get regime
    regime = get_regime_from_metrics(metrics_text)
    
    # Get rejection reasons (prefer log parser, merge with metrics)
    rejections = parse_rejection_reasons(metrics_text)
    
    # Merge with log parser rejections (log parser is more detailed)
    if log_metrics.get("rejections"):
        log_rejections = log_metrics["rejections"]
        # Merge: log parser takes precedence for counts
        for reason, count in log_rejections.items():
            rejections[reason] = max(rejections.get(reason, 0), count)
    
    # Find top rejection reason (prefer log parser)
    top_rejection = log_metrics.get("top_rejection", "NONE")
    if top_rejection == "NONE" and rejections:
        top_rejection = max(rejections.items(), key=lambda x: x[1])[0]
    
    # Get execution stats
    avg_limit_chase_savings = 0.0
    timeouts = 0
    
    if execution_stats:
        avg_limit_chase_savings = execution_stats.get("avg_limit_chase_savings", 0.0)
        timeouts = execution_stats.get("timeouts", 0)
    
    # Build metrics dictionary (merge API + Log metrics)
    daily_metrics = {
        "date": date,
        "pnl": float(daily_pnl),
        "win_rate": float(win_rate),
        "regime": log_metrics.get("regime", regime),  # Prefer log parser regime
        "top_rejection": top_rejection,
        "rejections": rejections,
        "avg_limit_chase_savings": float(avg_limit_chase_savings),
        "timeouts": int(timeouts),
        "trades_today": int(trades_today),
        # Additional log metrics
        "entries": log_metrics.get("entries", 0),
        "exits": log_metrics.get("exits", 0),
        "sl_hits": log_metrics.get("sl_hits", 0),
        "approval_rate": log_metrics.get("approval_rate", 0.0),
        "limit_chase_attempts": log_metrics.get("limit_chase_attempts", 0),
        "errors": log_metrics.get("errors", 0),
    }
    
    logger.info(f"✅ Collected metrics: PnL=₹{daily_pnl:.2f}, Win Rate={win_rate:.2%}, Regime={regime}")
    logger.info(f"   Rejections: {rejections}")
    
    return daily_metrics


def main():
    """Main evolution cycle"""
    parser = argparse.ArgumentParser(
        description="Run evolution cycle for self-evolving trading system"
    )
    parser.add_argument(
        "--config-path",
        type=str,
        default=None,
        help="Path to config YAML file (default: from APP_CONFIG env or app_config)"
    )
    parser.add_argument(
        "--memory-path",
        type=str,
        default="data/memory.json",
        help="Path to RAG memory JSON file"
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default="logs/trading.log",
        help="Path to trading log file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect metrics and analyze but don't apply patches"
    )
    parser.add_argument(
        "--use-cortex",
        action="store_true",
        help="Use The Cortex (integrated perception, cognition, evolution)"
    )
    
    args = parser.parse_args()
    
    # Determine config path
    if args.config_path:
        config_path = args.config_path
    elif settings.app_config_path:
        config_path = settings.app_config_path
    elif hasattr(app_config, 'config_path'):
        config_path = str(app_config.config_path)
    else:
        config_path = "configs/kite_day1_live.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        logger.error(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🧠 AI ANALYST - EVOLUTION CYCLE")
    logger.info("=" * 60)
    logger.info(f"📁 Config: {config_path}")
    logger.info(f"💾 Memory: {args.memory_path}")
    logger.info(f"🔍 Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("")
    
    try:
        # Initialize components
        logger.info("🔧 Initializing components...")
        
        if args.use_cortex:
            # Use The Cortex (integrated system)
            logger.info("🧠 Using The Cortex (Level 5 Self-Evolving System)")
            cortex = Cortex(
                config_path=str(config_path),
                log_path=args.log_path
            )
            logger.info("✅ Cortex initialized")
            logger.info("")
            
            # Run evolution cycle (simplified interface)
            result = cortex.run_evolution_cycle(dry_run=args.dry_run)
            
            logger.info("")
        else:
            # Use legacy mode (direct AI Analyst)
            memory = RAGMemory(db_path=args.memory_path)
            analyst = AIAnalyst(config_path=str(config_path), memory=memory)
            logger.info("✅ Components initialized")
            logger.info("")
            
            # Collect metrics
            daily_metrics = collect_daily_metrics(use_log_parser=True)
            logger.info("")
            
            # Run EOD analysis
            if args.dry_run:
                logger.info("🔍 DRY RUN: Would perform EOD analysis...")
                logger.info(f"   Metrics: {daily_metrics}")
                
                # Still generate suggestions but don't apply
                suggestions = analyst._generate_suggestions(
                    daily_metrics,
                    memory.retrieve_relevant_episodes(daily_metrics.get("regime", "UNKNOWN"), limit=10)
                )
                
                if suggestions:
                    logger.info(f"💡 Would apply patches: {suggestions}")
                else:
                    logger.info("💡 No patches suggested")
            else:
                logger.info("🧠 Running EOD analysis...")
                analyst.perform_eod_analysis(daily_metrics)
                logger.info("")
            
            # Show evolution history
            logger.info("📚 Recent Evolution History:")
            history = analyst.get_evolution_history(limit=5)
            if history:
                for episode in history:
                    logger.info(
                        f"   {episode.get('date')}: PnL=₹{episode.get('pnl', 0):.2f}, "
                        f"Regime={episode.get('dominant_regime', 'UNKNOWN')}, "
                        f"Patches={len(episode.get('config_snapshot', {}))}"
                    )
            else:
                logger.info("   (No evolution history yet)")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Evolution cycle complete!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Evolution cycle failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

