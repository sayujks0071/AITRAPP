'use client';

import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Shield } from 'lucide-react';

interface ModeBadgeProps {
  mode: string;
  isLeader: boolean;
}

export function ModeBadge({ mode, isLeader }: ModeBadgeProps) {
  const isLive = mode === 'LIVE' || mode === 'CRYPTO_LIVE';
  const isPaper = mode === 'PAPER' || mode === 'CRYPTO_PAPER';

  return (
    <div className="flex items-center gap-2">
      <Badge
        variant={isLive ? 'destructive' : 'secondary'}
        className="text-sm font-semibold"
      >
        {isLive && <AlertTriangle className="h-3 w-3 mr-1" />}
        {mode}
      </Badge>
      <Badge
        variant={isLeader ? 'success' : 'destructive'}
        className="text-xs"
      >
        {isLeader ? (
          <>
            <Shield className="h-3 w-3 mr-1" />
            Leader
          </>
        ) : (
          'Not Leader'
        )}
      </Badge>
    </div>
  );
}











