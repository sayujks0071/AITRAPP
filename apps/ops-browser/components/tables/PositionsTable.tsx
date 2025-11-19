'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent, formatTime } from '@/lib/format';
import type { Position } from '@/hooks/usePositions';

interface PositionsTableProps {
  positions: Position[];
  isLoading?: boolean;
}

export function PositionsTable({ positions, isLoading }: PositionsTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  if (positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">No open positions</div>
        </CardContent>
      </Card>
    );
  }

  const totalUPL = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Positions ({positions.length})</span>
          <span className={`text-sm font-normal ${totalUPL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            Total UPL: {formatCurrency(totalUPL)}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Side</th>
                <th className="text-right p-2">Qty</th>
                <th className="text-right p-2">Entry</th>
                <th className="text-right p-2">LTP</th>
                <th className="text-right p-2">UPL</th>
                <th className="text-right p-2">UPL %</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => (
                <tr key={pos.position_id} className="border-b hover:bg-muted/50">
                  <td className="p-2 font-medium">{pos.instrument}</td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      pos.side === 'LONG' ? 'bg-green-500/20 text-green-700 dark:text-green-400' : 'bg-red-500/20 text-red-700 dark:text-red-400'
                    }`}>
                      {pos.side}
                    </span>
                  </td>
                  <td className="p-2 text-right">{pos.quantity}</td>
                  <td className="p-2 text-right">{formatCurrency(pos.entry_price)}</td>
                  <td className="p-2 text-right">{formatCurrency(pos.current_price)}</td>
                  <td className={`p-2 text-right font-medium ${
                    pos.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {formatCurrency(pos.unrealized_pnl)}
                  </td>
                  <td className={`p-2 text-right ${
                    pos.pnl_pct >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {formatPercent(pos.pnl_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}






