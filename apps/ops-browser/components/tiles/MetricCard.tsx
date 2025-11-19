'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: { label: string; variant?: 'default' | 'success' | 'warning' | 'destructive' };
  trend?: 'up' | 'down' | 'neutral';
}

export function MetricCard({
  title,
  value,
  subtitle,
  badge,
  trend,
}: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
        {badge && (
          <Badge variant={badge.variant || 'default'} className="mt-2">
            {badge.label}
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}






