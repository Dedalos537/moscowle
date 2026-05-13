# cPanel Deployment Quick Guide

This document summarizes recommended steps to deploy the Flask app on a cPanel (Apache) environment and how to enable secure headers and environment variables.

## Set environment variables (Python App in cPanel)
- In cPanel, go to **Setup Python App** (or Application Manager) and configure your virtualenv and WSGI entry point.
- Add environment variables under the "Environment Variables" section. Required examples:

```
SECRET_KEY=your_secret
SQLALCHEMY_DATABASE_URI=sqlite:///moscowle.db
PREFERRED_URL_SCHEME=https
USE_PROXYFIX=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=True
HSTS_SECONDS=31536000
HSTS_INCLUDE_SUBDOMAINS=True
```

If the control panel does not offer env var UI, you can use a small wrapper in your WSGI or `passenger_wsgi.py` to load a `.env` file.

## .htaccess snippets (place in the app's public folder / document root)
- Force HTTPS redirects and set headers at Apache level. Ensure `mod_rewrite` and `mod_headers` are enabled on the server.

```apacheconf
# Redirect HTTP to HTTPS
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTPS} !=on
  RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>

# Security headers (set by Apache)
<IfModule mod_headers.c>
  Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  # Minimal CSP example — tune to your resources
  Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
</IfModule>
```

Notes:
- If you manage TLS at cPanel (AutoSSL), the redirect to HTTPS is safe. Confirm there is no redirect loop.
- If cPanel proxied requests to your WSGI app, enable `USE_PROXYFIX=True` in env so Flask honors `X-Forwarded-Proto` when generating `url_for` and secure cookies.

## Enabling ProxyFix
- In our app we added optional `ProxyFix` usage when `USE_PROXYFIX=True`. This is recommended for cPanel/Apache setups that use a reverse proxy or a front-facing load balancer.

## File uploads & static files
- Keep user uploads outside the document root if possible. If stored in `app/static/uploads` consider moving to a folder not served directly by Apache and serve through a secure endpoint that validates access.

## Troubleshooting
- If secure cookies are not set, verify the request scheme seen by the app. Use `USE_PROXYFIX=True` and ensure `X-Forwarded-Proto` is present from the proxy.
- If headers do not apply, check `mod_headers` is available in Apache on the cPanel instance.

## Quick checklist before promoting to production
- [ ] TLS certificate active (AutoSSL or Let's Encrypt)
- [ ] `SESSION_COOKIE_SECURE=True` and `USE_PROXYFIX=True` set in env
- [ ] `.htaccess` in place with redirects and headers (or set at server level)
- [ ] HSTS verified via response headers
- [ ] Content Security Policy tuned to allow third-party assets used by the site

