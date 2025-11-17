'use client';

import { useState, useEffect } from 'react';
import { fetchPositions } from '@/lib/api';

export interface Position {
  position_id: string;
  instrument: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_pct: number;
}

export function usePositions() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetch = async () => {
    try {
      const data = await fetchPositions();
      
      if (data === null) {
        setIsAvailable(false);
        setIsLoading(false);
        return;
      }
      
      setIsAvailable(true);
      setPositions(data.positions || []);
      setError(null);
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 5000); // Every 5s
    return () => clearInterval(interval);
  }, []);

  return {
    positions,
    isAvailable,
    error,
    isLoading,
    refetch: fetch,
  };
}



