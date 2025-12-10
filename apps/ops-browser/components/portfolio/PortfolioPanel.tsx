"use client";

import { usePortfolio } from "@/hooks/usePortfolio";

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

export function PortfolioPanel() {
  const { snapshot: snap, isLoading: loading, error: portfolioError } = usePortfolio();
  const error = portfolioError?.message || null;

  // Always show something so we know the component is rendering
  if (loading && !snap) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded-lg">
        ⏳ Loading broker state from Kite API...
      </div>
    );
  }

  if (error && !snap) {
    return (
      <div className="text-sm text-destructive p-4 border border-destructive rounded-lg bg-destructive/10">
        ❌ Error: {error}
        <div className="text-xs mt-2 text-muted-foreground">
          API endpoint: /api/portfolio/snapshot
        </div>
      </div>
    );
  }

  if (!snap) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded-lg">
        📊 No portfolio data available. Check API connection.
      </div>
    );
  }

  const driftOk = snap.drift_count === 0;

  return (
    <div className="space-y-4">
      {/* Funds Card */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold tracking-wide text-muted-foreground">
            CAPITAL & MARGIN
          </h3>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
            KITE • LIVE
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <Metric label="Net Value" value={snap.funds.net} format="₹" />
          <Metric label="Avail. Cash" value={snap.funds.available_cash} format="₹" />
          <Metric label="Used Margin" value={snap.funds.used_margin} format="₹" />
          <Metric
            label="Utilisation"
            value={snap.funds.utilisation_pct}
            format="%"
          />
          <Metric label="Collateral" value={snap.funds.collateral} format="₹" />
          <Metric label="Withdrawable" value={snap.funds.withdrawable} format="₹" />
        </div>
      </div>

      {/* Recon Strip */}
      <div className="rounded-lg border bg-card p-3 text-xs flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
            Broker vs Algo
          </div>
          <div className="text-foreground">
            {snap.broker_positions_count} broker •{" "}
            {snap.algo_positions_count} algo
          </div>
        </div>
        <div
          className={
            "px-2 py-1 rounded-full text-[10px] font-semibold " +
            (driftOk
              ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
              : "bg-amber-500/20 text-amber-600 dark:text-amber-400")
          }
        >
          {driftOk ? "MATCH" : `${snap.drift_count} DRIFT`}
        </div>
      </div>

      {/* Positions Table (top 4) */}
      <div className="rounded-lg border bg-card p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold tracking-wide text-muted-foreground">
            POSITIONS
          </h3>
          <span className="text-xs text-muted-foreground">
            {snap.positions.length} open
          </span>
        </div>
        {snap.positions.length === 0 ? (
          <div className="text-sm text-muted-foreground">No active positions.</div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {snap.positions.slice(0, 4).map((p, idx) => (
              <div
                key={`${p.instrument}-${p.segment}-${idx}`}
                className="flex items-center justify-between text-sm rounded-lg border bg-muted/50 px-3 py-2"
              >
                <div>
                  <div className="font-medium text-foreground">
                    {p.instrument}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {p.segment} • {p.strategy} • Δ {p.delta.toFixed(1)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-foreground">
                    {p.qty} @ {p.avg_price.toFixed(1)}
                  </div>
                  <div
                    className={
                      "text-xs font-medium " +
                      (p.pnl >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400")
                    }
                  >
                    PnL {p.pnl >= 0 ? "+" : ""}
                    {p.pnl.toFixed(0)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  format,
}: {
  label: string;
  value: number;
  format: "₹" | "%";
}) {
  const v =
    format === "₹"
      ? `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
      : `${value.toFixed(1)}%`;
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium text-foreground">{v}</div>
    </div>
  );
}

