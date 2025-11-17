'use client';

import { useState, useEffect } from 'react';
import { fetchOrders } from '@/lib/api';

export interface Order {
  order_id: string;
  client_order_id: string;
  symbol: string;
  side: string;
  quantity: number;
  price?: number;
  status: string;
  filled_qty?: number;
  average_price?: number;
  created_at?: string;
  updated_at?: string;
  oco_group?: string;
}

export function useOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetch = async () => {
    try {
      const data = await fetchOrders();
      
      if (data === null) {
        setIsAvailable(false);
        setIsLoading(false);
        return;
      }
      
      setIsAvailable(true);
      setOrders(Array.isArray(data) ? data : []);
      setError(null);
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 3000); // Every 3s
    return () => clearInterval(interval);
  }, []);

  return {
    orders,
    isAvailable,
    error,
    isLoading,
    refetch: fetch,
  };
}



