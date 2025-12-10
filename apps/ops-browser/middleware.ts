import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  
  // Only add CSP in production (dev mode needs unsafe-inline/unsafe-eval for Next.js)
  const isDev = process.env.NODE_ENV === 'development';
  
  if (!isDev) {
    // Content Security Policy (production only)
    const apiBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
    const apiOrigin = new URL(apiBase).origin;
    
    response.headers.set(
      'Content-Security-Policy',
      `default-src 'self'; ` +
      `connect-src 'self' ${apiOrigin}; ` +
      `img-src 'self' data:; ` +
      `script-src 'self' 'unsafe-inline' 'unsafe-eval'; ` +  // Next.js needs these in production too
      `style-src 'self' 'unsafe-inline'; ` +  // Tailwind needs unsafe-inline
      `font-src 'self' data:;`
    );
  }
  
  // Security headers (always apply)
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  
  // HSTS (if HTTPS)
  if (request.nextUrl.protocol === 'https:') {
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  }
  
  return response;
}

export const config = {
  matcher: '/:path*',
};

