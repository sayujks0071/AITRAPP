'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchMetrics } from '@/lib/api';
import { parsePrometheusMetrics, getMetric, getHistogramP95, type ParsedMetrics, type HistogramValue } from '@/lib/prom';

export interface MetricsSnapshot {
  metrics: ParsedMetrics;
  timestamp: Date;
  isStale: boolean;
}

export interface DerivedHealth {
  isLeader: boolean;
  marketdataHeartbeat: number;
  orderStreamHeartbeat: number;
  scanHeartbeat: number;
  leaderChanges: number;
  ocoOrphans: number;
  binanceUsedWeight: number;
  binanceOrderCount: number;
  binanceTimeSkew: number;
  flattenDurationP95: number;
  scanTicksTotal: number;
}

const HEARTBEAT_THRESHOLD = 5;
const STALE_THRESHOLD_MS = 10000; // 10 seconds

export function useMetrics(intervalMs: number = 1500) {
  const [snapshot, setSnapshot] = useState<MetricsSnapshot | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const backoffRef = useRef(1000);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetch = useCallback(async () => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    
    try {
      const text = await fetchMetrics();
      const metrics = parsePrometheusMetrics(text);
      const now = new Date();
      
      setSnapshot({
        metrics,
        timestamp: now,
        isStale: false,
      });
      
      setError(null);
      setIsLoading(false);
      backoffRef.current = 1000; // Reset backoff on success
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return; // Ignore abort errors
      }
      
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setIsLoading(false);
      
      // Exponential backoff
      backoffRef.current = Math.min(backoffRef.current * 2, 30000);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetch();
    
    // Set up polling with jitter
    const scheduleNext = () => {
      const jitter = Math.random() * 200; // 0-200ms jitter
      const delay = backoffRef.current + jitter;
      
      intervalRef.current = setTimeout(() => {
        fetch();
        scheduleNext();
      }, delay);
    };
    
    scheduleNext();
    
    return () => {
      if (intervalRef.current) {
        clearTimeout(intervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetch]);

  // Mark as stale if too old
  useEffect(() => {
    if (!snapshot) return;
    
    const checkStale = () => {
      const age = Date.now() - snapshot.timestamp.getTime();
      if (age > STALE_THRESHOLD_MS && !snapshot.isStale) {
        setSnapshot(prev => prev ? { ...prev, isStale: true } : null);
      }
    };
    
    const interval = setInterval(checkStale, 1000);
    return () => clearInterval(interval);
  }, [snapshot]);

  const derived: DerivedHealth | null = snapshot ? {
    isLeader: getMetric(snapshot.metrics, 'trader_is_leader', 0) === 1,
    marketdataHeartbeat: getMetric(snapshot.metrics, 'trader_marketdata_heartbeat_seconds', 999),
    orderStreamHeartbeat: getMetric(snapshot.metrics, 'trader_order_stream_heartbeat_seconds', 999),
    scanHeartbeat: getMetric(snapshot.metrics, 'trader_scan_heartbeat_seconds', 999),
    leaderChanges: getMetric(snapshot.metrics, 'trader_leader_changes_total', 0),
    ocoOrphans: getMetric(snapshot.metrics, 'trader_oco_orphans_total', 0),
    binanceUsedWeight: getMetric(snapshot.metrics, 'trader_binance_used_weight_1m', 0),
    binanceOrderCount: getMetric(snapshot.metrics, 'trader_binance_order_count_1m', 0),
    binanceTimeSkew: getMetric(snapshot.metrics, 'trader_binance_time_skew_ms', 0),
    flattenDurationP95: (() => {
      const hist = snapshot.metrics['crypto_flatten_duration_seconds'] as HistogramValue | undefined;
      if (hist && typeof hist === 'object' && 'buckets' in hist) {
        return getHistogramP95(hist);
      }
      return 0;
    })(),
    scanTicksTotal: getMetric(snapshot.metrics, 'trader_scan_ticks_total', 0),
  } : null;

  return {
    snapshot,
    derived,
    error,
    isLoading,
    refetch: fetch,
  };
}






