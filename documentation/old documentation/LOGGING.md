# Structured Logging (JSON)

This project now emits structured JSON logs using `python-json-logger`.

Why:
- JSON logs make it easy to parse, index, and query logs in log aggregation systems (ELK, Logflare, Datadog, etc.).
- We include `request_id` and `user_id` in each log record to correlate requests and user activity across services.

What was added:
- `python-json-logger` dependency added to `requirements.txt`.
- `app/__init__.py` configures a `RequestContextFilter` which injects `request_id` and `user_id` into log records when present.
- Each request gets an `X-Request-ID` header (generated if the client doesn't provide one) and it's added to responses.
- Logs are emitted as JSON to stdout by default.

Configuration (env vars):
- `LOG_LEVEL` — default `INFO`. Use `DEBUG` for local debugging.
- `SENTRY_DSN` — if present, Sentry integration will remain active (already implemented).

Notes & Recommendations:
- Deployments should capture stdout/stderr (systemd, Docker, or platform logging) and forward to a log aggregator.
- Add `request_id` as a tag in your log aggregation to make tracing easier.
- Consider log rotation and retention policies in production.

Example log record (single-line JSON):

{"asctime": "2026-01-14 16:42:00,000", "levelname": "INFO", "name": "app", "message": "User logged in", "request_id": "...", "user_id": "42"}

