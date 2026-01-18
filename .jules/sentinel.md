## 2025-02-21 - [Added Security Headers]
**Vulnerability:** Missing HTTP security headers (X-Frame-Options, HSTS, CSP, etc.) and potentially permissive CORS.
**Learning:** The application was missing standard security headers which exposes it to clickjacking, MIME sniffing, and other attacks.
**Prevention:** Implemented a `SecurityHeadersMiddleware` that automatically adds these headers to every response. This ensures that security headers are consistently applied without relying on individual route handlers.
