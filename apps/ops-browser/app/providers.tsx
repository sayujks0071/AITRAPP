'use client';

import { useEffect, useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [mswReady, setMswReady] = useState(false);

  useEffect(() => {
    // Only enable MSW in mock mode
    const apiBase = process.env.NEXT_PUBLIC_API_BASE;
    if (apiBase === '/mock') {
      import('@/mocks/browser').then(({ worker }) => {
        worker.start({
          onUnhandledRequest: 'bypass',
        }).then(() => {
          setMswReady(true);
        }).catch((err) => {
          console.error('MSW failed to start:', err);
          setMswReady(true); // Continue anyway
        });
      }).catch((err) => {
        console.error('Failed to load MSW:', err);
        setMswReady(true); // Continue anyway
      });
    } else {
      // Not in mock mode, ready immediately
      setMswReady(true);
    }
  }, []);

  // Show loading only if we're actually waiting for MSW
  if (!mswReady && process.env.NEXT_PUBLIC_API_BASE === '/mock') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Initializing mock service worker...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

