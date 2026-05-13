# Rate Limiting

This document explains how to configure `Flask-Limiter` for production and development.

## Overview
- The app uses `flask-limiter` for per-IP and per-route throttling. Some routes already have decorators (e.g., login).
- In development the default storage is in-memory (not persisted) which is fine for local testing but not for multi-process/prod.

## Configuration
Set the following environment variables in your `.env` or hosting provider:

- `RATELIMIT_STORAGE_URL` - storage backend for limiter. Examples:
  - Redis: `redis://:password@redis-host:6379/0`
  - Memcached (pylibmc): `memcached://127.0.0.1:11211`
  - Leave empty for in-memory (dev only)

- `RATELIMIT_HEADERS_ENABLED` - `True` to enable `X-RateLimit-*` response headers.
- `RATELIMIT_DEFAULT` - default rate limits, e.g. `"200 per day,50 per hour"`.

## Recommended production setup
1. Run a Redis instance accessible by the app.
2. Set `RATELIMIT_STORAGE_URL` to the Redis URI.
3. Keep per-route limits for sensitive endpoints like `/login` and adding a global default.

## Example `.env`

RATELIMIT_STORAGE_URL=redis://:s3cr3t@redis.example.com:6379/0
RATELIMIT_HEADERS_ENABLED=True
RATELIMIT_DEFAULT="200 per day,50 per hour"

## Notes
- If you deploy behind a load balancer or multiple workers, using Redis ensures limits apply globally.
- Adjust limits based on traffic patterns and monitoring. Use `429` responses for blocked requests.

