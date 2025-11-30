import { useState, useEffect } from 'react';

type BrokerFunds = {
  net: number;
  available_cash: number;
  withdrawable: number;
  used_margin: number;
  utilisation_pct: number;
  collateral: number;
};

type BrokerPosition = {
  instrument: string;
  segment: string;
  qty: number;
  avg_price: number;
  last_price: number;
  pnl: number;
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  strategy: string;
};

type PortfolioSnapshot = {
  funds: BrokerFunds;
  positions: BrokerPosition[];
  broker_positions_count: number;
  algo_positions_count: number;
  drift_count: number;
  drift_details: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export function usePortfolio() {
  const [snap, setSnap] = useState<PortfolioSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSnapshot = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('[PortfolioPanel] Fetching from:', `${API_BASE}/api/portfolio/snapshot`);
      const res = await fetch(`${API_BASE}/api/portfolio/snapshot`, {
        cache: 'no-store',
        next: { revalidate: 0 },
      });
      console.log('[PortfolioPanel] Response status:', res.status);
      if (!res.ok) {
        const errorText = await res.text();
        console.error('[PortfolioPanel] Error response:', errorText);
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const data = await res.json();
      console.log('[PortfolioPanel] Data received:', data);
      setSnap(data);
    } catch (err) {
      console.error('[PortfolioPanel] Fetch error:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch portfolio'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSnapshot();
    const id = setInterval(fetchSnapshot, 10_000); // refresh every 10s
    return () => clearInterval(id);
  }, []);

  return {
    snapshot: snap,
    isLoading: loading,
    error,
    refetch: fetchSnapshot,
  };
}

