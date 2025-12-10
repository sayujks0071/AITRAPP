'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatTime } from '@/lib/format';
import type { Order } from '@/hooks/useOrders';

interface OrdersTableProps {
  orders: Order[];
  isLoading?: boolean;
}

export function OrdersTable({ orders, isLoading }: OrdersTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  if (orders.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">No active orders</div>
        </CardContent>
      </Card>
    );
  }

  const getStatusVariant = (status: string) => {
    if (status === 'COMPLETE' || status === 'FILLED') return 'success';
    if (status === 'REJECTED' || status === 'CANCELLED') return 'destructive';
    return 'default';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Orders ({orders.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">ID</th>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Side</th>
                <th className="text-right p-2">Qty</th>
                <th className="text-right p-2">Price</th>
                <th className="text-right p-2">Filled</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">OCO Group</th>
                <th className="text-left p-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.order_id} className="border-b hover:bg-muted/50">
                  <td className="p-2 font-mono text-xs">{order.client_order_id.slice(0, 8)}...</td>
                  <td className="p-2 font-medium">{order.symbol}</td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      order.side === 'BUY' ? 'bg-green-500/20 text-green-700 dark:text-green-400' : 'bg-red-500/20 text-red-700 dark:text-red-400'
                    }`}>
                      {order.side}
                    </span>
                  </td>
                  <td className="p-2 text-right">{order.quantity}</td>
                  <td className="p-2 text-right">{order.price ? formatCurrency(order.price) : '-'}</td>
                  <td className="p-2 text-right">
                    {order.filled_qty || 0} / {order.quantity}
                  </td>
                  <td className="p-2">
                    <Badge variant={getStatusVariant(order.status)}>
                      {order.status}
                    </Badge>
                  </td>
                  <td className="p-2 font-mono text-xs">
                    {order.oco_group ? order.oco_group.slice(0, 8) + '...' : '-'}
                  </td>
                  <td className="p-2 text-xs text-muted-foreground">
                    {order.created_at ? formatTime(order.created_at, 'IST') : '-'}
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











