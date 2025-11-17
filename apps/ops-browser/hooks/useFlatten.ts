'use client';

import { useState } from 'react';
import { postFlatten } from '@/lib/api';

export function useFlatten() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastResult, setLastResult] = useState<any>(null);

  const flatten = async (reason: string = 'manual') => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await postFlatten(reason);
      setLastResult(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to flatten');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    flatten,
    isLoading,
    error,
    lastResult,
  };
}



