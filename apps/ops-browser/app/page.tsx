'use client';

import { useState, useEffect, useRef } from 'react';
import * as React from 'react';
import { useMetrics } from '@/hooks/useMetrics';
import { useHealth } from '@/hooks/useHealth';
import { useFlatten } from '@/hooks/useFlatten';
import { usePositions } from '@/hooks/usePositions';
import { useOrders } from '@/hooks/useOrders';
import { HealthTile } from '@/components/tiles/HealthTile';
import { ModeBadge } from '@/components/tiles/ModeBadge';
import { MetricCard } from '@/components/tiles/MetricCard';
import { PositionsTable } from '@/components/tables/PositionsTable';
import { OrdersTable } from '@/components/tables/OrdersTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatPercent, formatTime, formatDuration, getStatusColor } from '@/lib/format';
import { AlertCircle, RefreshCw, Zap, Keyboard } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useHotkeys } from '@/hooks/useHotkeys';
import { useToast } from '@/hooks/useToast';

export default function Dashboard() {
  const [timezone, setTimezone] = useState<'IST' | 'UTC'>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('ops-browser:timezone');
      return (stored as 'IST' | 'UTC') || 'IST';
    }
    return 'IST';
  });
  const [showFlattenDialog, setShowFlattenDialog] = useState(false);
  
  // Persist timezone preference
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('ops-browser:timezone', timezone);
    }
  }, [timezone]);
  const { snapshot, derived, error: metricsError, isLoading: metricsLoading, refetch: refetchMetrics } = useMetrics();
  const { health, ready, error: healthError } = useHealth();
  const { flatten, isLoading: flattenLoading, error: flattenError } = useFlatten();
  const { positions, isAvailable: positionsAvailable } = usePositions();
  const { orders, isAvailable: ordersAvailable } = useOrders();
  const { toast } = useToast();
  const prevStateRef = React.useRef<{
    isLeader?: boolean;
    ocoOrphans?: number;
    heartbeatWarned?: boolean;
  }>({});

  // Toast notifications for status changes (only on state transitions)
  useEffect(() => {
    if (!derived) return;
    
    const prev = prevStateRef.current;
    
    // Leader lost (only toast on transition from leader to not leader)
    if (!derived.isLeader && prev.isLeader === true) {
      toast({
        variant: 'destructive',
        title: 'Leader Lock Lost',
        description: 'Trading paused. Another instance may be running.',
      });
    }
    
    // Heartbeat warning (only once per session)
    const hasHighHeartbeat = derived.marketdataHeartbeat >= 5 || 
                             derived.orderStreamHeartbeat >= 5 || 
                             derived.scanHeartbeat >= 5;
    if (hasHighHeartbeat && !prev.heartbeatWarned) {
      toast({
        variant: 'warning',
        title: 'Heartbeat Warning',
        description: 'One or more heartbeats exceed 5s threshold.',
      });
      prev.heartbeatWarned = true;
    } else if (!hasHighHeartbeat) {
      prev.heartbeatWarned = false;
    }
    
    // OCO orphan detected (only on increase)
    if (derived.ocoOrphans > 0 && (prev.ocoOrphans === undefined || derived.ocoOrphans > prev.ocoOrphans)) {
      toast({
        variant: 'destructive',
        title: 'OCO Orphan Detected',
        description: `${derived.ocoOrphans} orphaned OCO group(s) found.`,
      });
    }
    
    // Update previous state
    prevStateRef.current = {
      isLeader: derived.isLeader,
      ocoOrphans: derived.ocoOrphans,
      heartbeatWarned: prev.heartbeatWarned,
    };
  }, [derived, toast]);

  const handleFlatten = async () => {
    try {
      const result = await flatten('manual');
      setShowFlattenDialog(false);
      toast({
        variant: 'success',
        title: 'Positions Flattened',
        description: result.duration_seconds 
          ? `Flatten completed in ${result.duration_seconds.toFixed(2)}s`
          : 'All positions closed successfully',
      });
      refetchMetrics();
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Flatten Failed',
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const isOffline = metricsError || healthError;
  const lastUpdate = snapshot?.timestamp ? formatTime(snapshot.timestamp.toISOString(), timezone) : 'Never';

  // Hotkeys
  useHotkeys({
    'f': () => setShowFlattenDialog(true),
    'r': (e) => {
      e.preventDefault();
      refetchMetrics();
    },
    '?': () => {
      // Show shortcuts modal (future enhancement)
      alert('Hotkeys:\nf = Flatten\nr = Refresh\n? = Show this help');
    },
  });

  return (
    <div className="min-h-screen bg-background p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Bar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <h1 className="text-3xl font-bold">Trading Ops Browser</h1>
            {health && (
              <ModeBadge mode={health.mode} isLeader={derived?.isLeader || false} />
            )}
          </div>
          
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Last update: {lastUpdate}</span>
              {snapshot?.isStale && (
                <Badge variant="warning" className="text-xs">Stale</Badge>
              )}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTimezone(timezone === 'IST' ? 'UTC' : 'IST')}
            >
              {timezone}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={refetchMetrics}
              disabled={metricsLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${metricsLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Error Banner */}
        {isOffline && (
          <Card className="border-red-500 bg-red-500/10">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="h-5 w-5" />
                <span className="font-medium">API Offline</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                {metricsError?.message || healthError?.message || 'Unable to connect to API'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Showing last known values. Retrying with exponential backoff...
              </p>
            </CardContent>
          </Card>
        )}

        {/* Health Tiles */}
        {derived && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <HealthTile
              title="Market Data Heartbeat"
              value={derived.marketdataHeartbeat}
              unit="s"
              thresholds={{ green: 5, amber: 10 }}
            />
            <HealthTile
              title="Order Stream Heartbeat"
              value={derived.orderStreamHeartbeat}
              unit="s"
              thresholds={{ green: 5, amber: 10 }}
            />
            <HealthTile
              title="Scan Heartbeat"
              value={derived.scanHeartbeat}
              unit="s"
              thresholds={{ green: 5, amber: 10 }}
            />
            <HealthTile
              title="Leader Changes"
              value={derived.leaderChanges}
              thresholds={{ green: 0, amber: 1 }}
              formatValue={(v) => v.toString()}
            />
          </div>
        )}

        {/* P&L Row */}
        {health && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              title="Mode"
              value={health.mode}
              subtitle={health.is_paused ? 'Paused' : 'Active'}
            />
            <MetricCard
              title="Scan Ticks"
              value={derived?.scanTicksTotal || 0}
              subtitle="Total scan cycles"
            />
            <MetricCard
              title="OCO Orphans"
              value={derived?.ocoOrphans || 0}
              subtitle={derived?.ocoOrphans === 0 ? 'Healthy' : 'Warning'}
              badge={derived?.ocoOrphans === 0 ? { label: 'OK', variant: 'success' } : { label: 'Issue', variant: 'warning' }}
            />
          </div>
        )}

        {/* Exchange Panel (Crypto) */}
        {health?.crypto_venue && derived && (
          <Card>
            <CardHeader>
              <CardTitle>Exchange: {health.crypto_venue}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                  title="Used Weight (1m)"
                  value={`${derived.binanceUsedWeight}/1200`}
                  subtitle="Rate limit"
                />
                <MetricCard
                  title="Order Count (1m)"
                  value={derived.binanceOrderCount.toString()}
                  subtitle="Rate limit"
                />
                <MetricCard
                  title="Time Skew"
                  value={`${derived.binanceTimeSkew}ms`}
                  subtitle={derived.binanceTimeSkew < 1000 ? 'OK' : 'Warning'}
                  badge={derived.binanceTimeSkew < 1000 ? { label: 'OK', variant: 'success' } : { label: 'High', variant: 'warning' }}
                />
                <MetricCard
                  title="Flatten P95"
                  value={formatDuration(derived.flattenDurationP95)}
                  subtitle={derived.flattenDurationP95 <= 2 ? 'OK' : 'Slow'}
                  badge={derived.flattenDurationP95 <= 2 ? { label: 'OK', variant: 'success' } : { label: 'Slow', variant: 'warning' }}
                />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Controls Panel */}
        <Card>
          <CardHeader>
            <CardTitle>Controls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <Button
                variant="destructive"
                onClick={() => setShowFlattenDialog(true)}
                disabled={flattenLoading}
                className="flex items-center gap-2"
              >
                <Zap className="h-4 w-4" />
                {flattenLoading ? 'Flattening...' : 'Flatten All Positions'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Flatten Confirmation Dialog */}
        <Dialog open={showFlattenDialog} onOpenChange={setShowFlattenDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Flatten All Positions</DialogTitle>
              <DialogDescription>
                This will close all open positions immediately. This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowFlattenDialog(false)}
                disabled={flattenLoading}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleFlatten}
                disabled={flattenLoading}
              >
                {flattenLoading ? 'Flattening...' : 'Confirm Flatten'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Positions Table */}
        {positionsAvailable === false ? (
          <Card>
            <CardHeader>
              <CardTitle>Positions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground">
                Positions endpoint not exposed by server
              </div>
            </CardContent>
          </Card>
        ) : (
          <PositionsTable positions={positions} />
        )}

        {/* Orders Table */}
        {ordersAvailable === false ? (
          <Card>
            <CardHeader>
              <CardTitle>Orders</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground">
                Orders endpoint not exposed by server
              </div>
            </CardContent>
          </Card>
        ) : (
          <OrdersTable orders={orders} />
        )}
      </div>
    </div>
  );
}

