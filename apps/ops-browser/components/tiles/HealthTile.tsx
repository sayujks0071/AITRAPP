'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getStatusColor, getStatusBgColor } from '@/lib/format';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';

interface HealthTileProps {
  title: string;
  value: number;
  unit?: string;
  thresholds?: { green: number; amber: number };
  formatValue?: (value: number) => string;
  icon?: React.ReactNode;
}

export function HealthTile({
  title,
  value,
  unit = '',
  thresholds = { green: 5, amber: 10 },
  formatValue = (v) => v.toFixed(2),
  icon,
}: HealthTileProps) {
  const color = getStatusColor(value, thresholds);
  const bgColor = getStatusBgColor(value, thresholds);
  const isHealthy = value <= thresholds.green;
  const isWarning = value > thresholds.green && value <= thresholds.amber;

  return (
    <Card className={bgColor}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          <span>{title}</span>
          {icon || (
            isHealthy ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : isWarning ? (
              <Clock className="h-4 w-4 text-amber-500" />
            ) : (
              <AlertCircle className="h-4 w-4 text-red-500" />
            )
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          <span className={color}>
            {formatValue(value)}
          </span>
          {unit && <span className="text-sm text-muted-foreground ml-1">{unit}</span>}
        </div>
      </CardContent>
    </Card>
  );
}



