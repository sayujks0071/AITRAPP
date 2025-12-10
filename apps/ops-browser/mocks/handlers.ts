/**
 * MSW handlers for mocking API endpoints
 * Use with NEXT_PUBLIC_API_BASE=/mock
 */

import { http, HttpResponse } from 'msw';

export const handlers = [
  // Metrics endpoint
  http.get('/api/metrics', () => {
    return HttpResponse.text(`
# HELP trader_is_leader Leader lock status
# TYPE trader_is_leader gauge
trader_is_leader{instance_id="default"} 1

# HELP trader_marketdata_heartbeat_seconds Market data heartbeat
# TYPE trader_marketdata_heartbeat_seconds gauge
trader_marketdata_heartbeat_seconds 0.4

# HELP trader_order_stream_heartbeat_seconds Order stream heartbeat
# TYPE trader_order_stream_heartbeat_seconds gauge
trader_order_stream_heartbeat_seconds 1.2

# HELP trader_scan_heartbeat_seconds Scan loop heartbeat
# TYPE trader_scan_heartbeat_seconds gauge
trader_scan_heartbeat_seconds 2.5

# HELP trader_leader_changes_total Leader change counter
# TYPE trader_leader_changes_total counter
trader_leader_changes_total 0

# HELP trader_oco_orphans_total OCO orphan counter
# TYPE trader_oco_orphans_total counter
trader_oco_orphans_total 0

# HELP trader_scan_ticks_total Total scan cycles
# TYPE trader_scan_ticks_total counter
trader_scan_ticks_total 1234

# HELP trader_binance_used_weight_1m Binance rate limit
# TYPE trader_binance_used_weight_1m gauge
trader_binance_used_weight_1m 450

# HELP trader_binance_order_count_1m Binance order count
# TYPE trader_binance_order_count_1m gauge
trader_binance_order_count_1m 12

# HELP trader_binance_time_skew_ms Time skew
# TYPE trader_binance_time_skew_ms gauge
trader_binance_time_skew_ms 50

# HELP crypto_flatten_duration_seconds Flatten duration histogram
# TYPE crypto_flatten_duration_seconds histogram
crypto_flatten_duration_seconds_bucket{le="0.5",venue="BINANCE_SPOT"} 5
crypto_flatten_duration_seconds_bucket{le="1.0",venue="BINANCE_SPOT"} 10
crypto_flatten_duration_seconds_bucket{le="2.0",venue="BINANCE_SPOT"} 15
crypto_flatten_duration_seconds_bucket{le="+Inf",venue="BINANCE_SPOT"} 15
crypto_flatten_duration_seconds_sum{venue="BINANCE_SPOT"} 12.5
crypto_flatten_duration_seconds_count{venue="BINANCE_SPOT"} 15
`, {
      headers: { 'Content-Type': 'text/plain' },
    });
  }),

  // Health endpoint
  http.get('/api/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      mode: 'PAPER',
      is_paused: false,
      timestamp: new Date().toISOString(),
      crypto_venue: 'BINANCE_SPOT',
      allowed_symbols: ['BTCUSDT', 'ETHUSDT'],
      maker_fee_bps: 10,
      taker_fee_bps: 10,
    });
  }),

  // Ready endpoint
  http.get('/api/ready', () => {
    return HttpResponse.json({
      status: 'ready',
      leader: 1,
      marketdata_heartbeat: 0.4,
      order_stream_heartbeat: 1.2,
      scan_heartbeat: 2.5,
    });
  }),

  // Positions endpoint
  http.get('/api/positions', () => {
    return HttpResponse.json({
      positions: [
        {
          position_id: 'pos_1',
          instrument: 'BTCUSDT',
          side: 'LONG',
          quantity: 0.1,
          entry_price: 45000,
          current_price: 45200,
          unrealized_pnl: 20,
          pnl_pct: 0.044,
        },
      ],
      count: 1,
    });
  }),

  // Orders endpoint
  http.get('/api/orders', () => {
    return HttpResponse.json([
      {
        order_id: 'ord_1',
        client_order_id: 'client_123',
        symbol: 'BTCUSDT',
        side: 'BUY',
        quantity: 0.1,
        price: 45000,
        status: 'OPEN',
        filled_qty: 0,
        created_at: new Date().toISOString(),
      },
    ]);
  }),

  // Flatten endpoint
  http.post('/api/flatten', async ({ request }) => {
    const body = await request.json() as { reason?: string };
    return HttpResponse.json({
      status: 'flattened',
      reason: body.reason || 'manual',
      duration_seconds: 1.2,
      timestamp: new Date().toISOString(),
    });
  }),
];

