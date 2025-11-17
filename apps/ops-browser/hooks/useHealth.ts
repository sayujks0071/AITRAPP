'use client';

import { useState, useEffect } from 'react';
import { fetchHealth, fetchReady } from '@/lib/api';

export interface HealthData {
  status: string;
  mode: string;
  is_paused?: boolean;
  timestamp?: string;
  crypto_venue?: string;
  allowed_symbols?: string[];
  maker_fee_bps?: number;
  taker_fee_bps?: number;
  precision?: Record<string, any>;
}

export interface ReadyData {
  status: string;
  leader: number;
  marketdata_heartbeat: number;
  order_stream_heartbeat: number;
  scan_heartbeat: number;
}

export function useHealth() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [ready, setReady] = useState<ReadyData | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetch = async () => {
    try {
      const [healthData, readyData] = await Promise.all([
        fetchHealth().catch((err) => {
          // Silently handle health errors (expected if API is down)
          return null;
        }),
        fetchReady().catch((err) => {
          // Silently handle ready errors (expected if trader isn't started)
          // This endpoint returns 500 when trader isn't running, which is OK
          return null;
        }),
      ]);
      
      if (healthData) setHealth(healthData);
      if (readyData) setReady(readyData);
      
      setError(null);
      setIsLoading(false);
    } catch (err) {
      // Only set error for unexpected failures
      if (err instanceof Error && !err.message.includes('CORS')) {
        setError(err);
      }
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 10000); // Every 10s
    return () => clearInterval(interval);
  }, []);

  return { health, ready, error, isLoading, refetch: fetch };
}

