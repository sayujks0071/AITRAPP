#!/usr/bin/env python3
"""
Trading Analyst MCP Adapter

Python backend that:
1. Calls FastAPI bot endpoints for algo state
2. Calls Kite for broker state
3. Aggregates + normalizes into clean JSON for MCP tools

Usage:
    python3 trading_analyst_adapter.py <tool_name> <args_json>

Example:
    python3 trading_analyst_adapter.py get_live_risk_snapshot '{}'
"""

import sys
import json
import os
from typing import Dict, Any, List
from datetime import datetime, date
import requests

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages'))

from exchanges.kite_client import get_kite_client
from core.config import load_config


class TradingAnalystAdapter:
    """Adapter that fetches data from bot API + Kite and returns normalized JSON."""

    def __init__(self):
        # Bot API base URL (adjust if running on different port)
        self.bot_api_base = os.getenv('BOT_API_URL', 'http://localhost:8000')

        # Load config to get Kite credentials
        self.config = load_config()

        # Kite client (lazy init)
        self._kite = None

    @property
    def kite(self):
        """Lazy init Kite client."""
        if self._kite is None:
            self._kite = get_kite_client(self.config)
        return self._kite

    def call_bot_api(self, endpoint: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """Call bot's FastAPI endpoint."""
        url = f"{self.bot_api_base}{endpoint}"
        try:
            if method == 'GET':
                resp = requests.get(url, timeout=10, **kwargs)
            elif method == 'POST':
                resp = requests.post(url, timeout=10, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Bot API call failed: {str(e)}"}

    # ========== TOOL IMPLEMENTATIONS ==========

    def get_live_risk_snapshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool 1: Get comprehensive live risk snapshot.

        Aggregates:
        - Portfolio greeks from bot
        - Margin usage from Kite
        - Short premium + tail coverage from bot
        - Risk flags
        """
        timestamp = datetime.now().isoformat()

        # 1. Get portfolio greeks from bot (if you have /api/risk/greeks endpoint)
        greeks_data = self.call_bot_api('/api/risk/greeks')
        if 'error' in greeks_data:
            greeks_data = {
                'net_delta': 0.0,
                'net_gamma': 0.0,
                'net_vega': 0.0,
                'net_theta': 0.0,
                'note': 'Bot API not available - using zeros'
            }

        # 2. Get margin from Kite
        try:
            margins = self.kite.margins()
            equity_margin = margins.get('equity', {})
            used = equity_margin.get('used', {}).get('debits', 0)
            available = equity_margin.get('available', {}).get('cash', 0)
            utilisation_pct = (used / (used + available) * 100) if (used + available) > 0 else 0.0
        except Exception as e:
            used = 0
            available = 0
            utilisation_pct = 0.0
            print(f"Warning: Kite margin call failed: {e}", file=sys.stderr)

        # 3. Get short premium + tail coverage from bot
        short_premium_data = self.call_bot_api('/api/risk/short_premium')
        if 'error' in short_premium_data:
            short_premium_data = {
                'total_notional': 0,
                'by_underlying': {},
                'note': 'Bot API not available'
            }

        tail_coverage_data = self.call_bot_api('/api/risk/tail_coverage')
        if 'error' in tail_coverage_data:
            tail_coverage_data = {
                'overall_pct': 0.0,
                'by_underlying': {},
                'note': 'Bot API not available'
            }

        # 4. Compute risk flags
        risk_flags = []
        if utilisation_pct < 70:
            risk_flags.append('MARGIN_OK')
        else:
            risk_flags.append('MARGIN_HIGH')

        if tail_coverage_data.get('overall_pct', 0) >= 10:
            risk_flags.append('TAIL_COVERAGE_WITHIN_BOUNDS')
        else:
            risk_flags.append('TAIL_COVERAGE_LOW')

        if abs(greeks_data.get('net_delta', 0)) < 10:
            risk_flags.append('DELTA_NEUTRAL')

        # Assemble snapshot
        return {
            'timestamp': timestamp,
            'portfolio': {
                'net_delta': greeks_data.get('net_delta', 0.0),
                'net_gamma': greeks_data.get('net_gamma', 0.0),
                'net_vega': greeks_data.get('net_vega', 0.0),
                'net_theta': greeks_data.get('net_theta', 0.0),
            },
            'margin': {
                'used': used,
                'available': available,
                'utilisation_pct': round(utilisation_pct, 1),
            },
            'short_premium': short_premium_data,
            'tail_coverage': tail_coverage_data,
            'risk_flags': risk_flags,
        }

    def get_strategy_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool 2: Get per-strategy performance summary.

        Calls bot's /api/strategies/summary endpoint.
        """
        lookback_days = args.get('lookback_days', 60)

        data = self.call_bot_api(
            '/api/strategies/summary',
            params={'lookback_days': lookback_days}
        )

        if 'error' in data:
            # Fallback: read from daily report JSON if available
            return {
                'date': date.today().isoformat(),
                'strategies': [],
                'note': 'Bot API not available - no strategy data'
            }

        return data

    def get_broker_vs_algo_reconciliation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool 3: Compare Kite positions vs algo engine state.

        Detects:
        - Orphan positions (on broker but not in algo)
        - Ghost positions (in algo but not on broker)
        - Quantity mismatches
        """
        timestamp = datetime.now().isoformat()

        # 1. Get Kite positions
        try:
            kite_positions = self.kite.positions()['net']
            kite_map = {
                p['tradingsymbol']: p['quantity']
                for p in kite_positions
                if p['quantity'] != 0
            }
        except Exception as e:
            return {
                'timestamp': timestamp,
                'status': 'ERROR',
                'error': f'Failed to fetch Kite positions: {str(e)}',
                'mismatches': []
            }

        # 2. Get algo positions from bot
        algo_data = self.call_bot_api('/api/positions')
        if 'error' in algo_data:
            return {
                'timestamp': timestamp,
                'status': 'ERROR',
                'error': 'Bot API not available',
                'mismatches': []
            }

        algo_map = {
            pos['symbol']: pos['quantity']
            for pos in algo_data.get('positions', [])
            if pos['quantity'] != 0
        }

        # 3. Find mismatches
        mismatches = []
        all_symbols = set(kite_map.keys()) | set(algo_map.keys())

        for symbol in all_symbols:
            kite_qty = kite_map.get(symbol, 0)
            algo_qty = algo_map.get(symbol, 0)

            if kite_qty != algo_qty:
                if kite_qty != 0 and algo_qty == 0:
                    note = f"Orphan position on broker; algo thinks flat"
                elif kite_qty == 0 and algo_qty != 0:
                    note = f"Ghost position in algo; broker shows flat"
                else:
                    note = f"Quantity mismatch (diff: {kite_qty - algo_qty})"

                mismatches.append({
                    'symbol': symbol,
                    'broker_qty': kite_qty,
                    'algo_qty': algo_qty,
                    'note': note,
                })

        status = 'OK' if len(mismatches) == 0 else 'MISMATCH_DETECTED'

        return {
            'timestamp': timestamp,
            'status': status,
            'mismatches': mismatches,
        }

    def get_event_and_regime_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool 4: Get R1 regime + E1 event context.

        Calls bot's /api/regime/current and /api/events/today endpoints.
        """
        today = date.today().isoformat()

        # Get regime data
        regime_data = self.call_bot_api('/api/regime/current')
        if 'error' in regime_data:
            regime_data = {'underlyings': {}}

        # Get event data
        event_data = self.call_bot_api('/api/events/today')
        if 'error' in event_data:
            event_data = {'underlyings': {}}

        # Merge regime + event data per underlying
        underlyings = {}

        for symbol in set(regime_data.get('underlyings', {}).keys()) | set(event_data.get('underlyings', {}).keys()):
            regime_info = regime_data.get('underlyings', {}).get(symbol, {})
            event_info = event_data.get('underlyings', {}).get(symbol, {})

            underlyings[symbol] = {
                'r1_regime': regime_info.get('regime', 'UNKNOWN'),
                'iv_rank': regime_info.get('iv_rank', 0.0),
                'atr_pct': regime_info.get('atr_pct', 0.0),
                'rv_iv': regime_info.get('rv_iv', 0.0),
                'event': {
                    'day_type': event_info.get('day_type', 'NORMAL'),
                    'name': event_info.get('name', None),
                    'severity': event_info.get('severity', 0.0),
                }
            }

        return {
            'date': today,
            'underlyings': underlyings,
        }

    def propose_config_tweaks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool 5: Propose config changes based on recent performance.

        This is the most complex tool - it analyzes:
        - Strategy performance vs regimes
        - Hit rates vs expected
        - Drawdowns vs limits

        Returns patch proposals (NEVER applies them).
        """
        analysis_window_days = args.get('analysis_window_days', 30)
        focus = args.get('focus', 'all')

        # Get strategy summary with longer lookback
        strategy_data = self.get_strategy_summary({'lookback_days': analysis_window_days})

        if not strategy_data.get('strategies'):
            return {
                'note': 'No strategy data available for analysis',
                'allocator': {'suggested_weight_changes': []},
                'regimes': {'suggested_regime_band_edits': []},
                'strategies': {'suggested_param_edits': []},
            }

        result = {
            'analysis_window_days': analysis_window_days,
            'focus': focus,
        }

        # 1. Allocator suggestions (if focus=allocator or all)
        if focus in ['allocator', 'all']:
            weight_changes = []

            for strat in strategy_data['strategies']:
                name = strat['name']
                hit_rate = strat.get('hit_rate_20d', 0.5)
                max_dd = strat.get('max_dd_60d', 0)
                realised_pnl = strat.get('realised_pnl', 0)

                # Simple heuristics (you can make these more sophisticated)
                if hit_rate > 0.6 and realised_pnl > 0 and max_dd > -20000:
                    weight_changes.append({
                        'strategy': name,
                        'delta_weight_pct': +3,
                        'reason': f'Strong hit rate ({hit_rate:.1%}), positive PnL, controlled drawdown'
                    })
                elif hit_rate < 0.45 or max_dd < -30000:
                    weight_changes.append({
                        'strategy': name,
                        'delta_weight_pct': -5,
                        'reason': f'Low hit rate ({hit_rate:.1%}) or large drawdown (₹{max_dd:,.0f})'
                    })

            result['allocator'] = {
                'suggested_weight_changes': weight_changes
            }

        # 2. Regime suggestions (if focus=regimes or all)
        if focus in ['regimes', 'all']:
            # For now, placeholder - you'd analyze regime performance here
            result['regimes'] = {
                'suggested_regime_band_edits': [],
                'note': 'Regime analysis requires more historical data - implement after live data collection'
            }

        # 3. Strategy param suggestions (if focus=strategies or all)
        if focus in ['strategies', 'all']:
            result['strategies'] = {
                'suggested_param_edits': [],
                'note': 'Strategy param tuning requires walk-forward analysis - see tune_walkforward.py'
            }

        return result

    # ========== MAIN DISPATCHER ==========

    def dispatch(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to correct tool handler."""
        handlers = {
            'get_live_risk_snapshot': self.get_live_risk_snapshot,
            'get_strategy_summary': self.get_strategy_summary,
            'get_broker_vs_algo_reconciliation': self.get_broker_vs_algo_reconciliation,
            'get_event_and_regime_context': self.get_event_and_regime_context,
            'propose_config_tweaks': self.propose_config_tweaks,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {'error': f'Unknown tool: {tool_name}'}

        try:
            return handler(args)
        except Exception as e:
            return {'error': f'Tool execution failed: {str(e)}'}


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            'error': 'Usage: trading_analyst_adapter.py <tool_name> <args_json>'
        }))
        sys.exit(1)

    tool_name = sys.argv[1]
    args_json = sys.argv[2]

    try:
        args = json.loads(args_json)
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON args: {str(e)}'}))
        sys.exit(1)

    adapter = TradingAnalystAdapter()
    result = adapter.dispatch(tool_name, args)

    # Write result to stdout as JSON
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
