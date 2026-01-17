# Monitoring: Rate-limit metrics + Grafana/Loki samples

This document shows how to collect and visualize rate-limit metrics and related logs from the app.

What we added

- `/metrics` endpoint: JSON payload with simple counters for rate-limited events.
  - If `RATELIMIT_STORAGE_URL` is configured and reachable, counters are stored in Redis keys:
    - `ratelimit:total` — total number of 429 events
    - `ratelimit:by_endpoint:{endpoint}` — counts per Flask endpoint
  - Otherwise the app keeps counters in-memory (best-effort for single-process dev only).
  - Optional header-based auth: set `METRICS_AUTH_TOKEN` in `.env` and call with `Authorization: Bearer <token>`.

- 429 handler logs a `rate_limited` warning with `endpoint` and `request_id` (for Loki searching).

Quickstart (recommended production): Redis + redis_exporter + Prometheus + Grafana

1) Run Redis and set `RATELIMIT_STORAGE_URL` in your environment, e.g.:

RATELIMIT_STORAGE_URL=redis://:password@redis-host:6379/0

2) Install and run `redis_exporter` (https://github.com/oliver006/redis_exporter) to expose Redis metrics to Prometheus.
   Configure `redis_exporter` to collect the keys you're interested in or use a small script to transform keys to Prometheus metrics.

3) Prometheus can scrape `redis_exporter` and store `redis_key_*` metrics. Add a dashboard in Grafana to visualize `ratelimit_total` and per-endpoint metrics.

Alternative: Use Grafana Loki to monitor logs directly (no extra exporter)

- We log `rate_limited` as a warning message. In Grafana explore (Loki datasource) you can use queries like:

{app="moscowle"} |= "rate_limited"

- Convert to a time series in Grafana with `count_over_time()`:

count_over_time({app="moscowle"} |= "rate_limited"[5m])

This returns the number of rate-limited events in 5-minute windows.

Sample Loki panel for rate-limits per route (LogQL):

sum by (endpoint) (count_over_time({app="moscowle"} |= "rate_limited" | json | unwrap endpoint [5m]))

Notes:
- To make `endpoint` available as a field in logs, ensure logs are JSON (we emit JSON logs with `request_id`, `user_id`). The `extra` fields added in the log call may appear as labels or need to be parsed via `| json`.
- Loki works best when your logs include stable labels (e.g., `app="moscowle"`, `env="prod"`). Add these via your log shipping configuration.

Prometheus scraping /metrics (optional)

- Our `/metrics` endpoint returns JSON, not Prometheus text exposition format. To scrape for Prometheus you can:
  - Add a tiny exporter service that reads `/metrics` and converts JSON to Prometheus metrics (simple Flask/Prometheus client script), or
  - Use Redis as the source of truth and `redis_exporter` + Prometheus to get numerical metrics directly.

Example: small Redis -> Prometheus exporter idea

- Create a cron or small service that periodically reads Redis keys `ratelimit:*` and exposes them at `/metrics` in Prometheus format using `prometheus_client` Python library.
- Scrape that endpoint from Prometheus and build Grafana panels.

Example Grafana queries

- Rate-limited events per minute (Prometheus):
  - `increase(ratelimit_total[1m])`

- Rate-limited events per endpoint (Prometheus):
  - `increase(ratelimit_by_endpoint{endpoint="/admin/payments/register"}[5m])`

Security and access

- Protect `/metrics` behind a network ACL, internal LB or set `METRICS_AUTH_TOKEN` and use `Authorization: Bearer <token>`.
- Prefer not exposing Redis directly to the public internet.

Summary

- Lightweight options:
  - Use Loki to create dashboards directly from logs (fast to iterate).
  - Use Redis counters + redis_exporter + Prometheus for precise numeric metrics and alerting.

If you want, I can:
- Add a tiny Prometheus exporter that converts the `/metrics` JSON (or Redis keys) into Prometheus exposition format and run it locally, or
- Show example Grafana dashboard JSON for rate-limits and provide a Loki query snippet you can import.

I added a ready-to-import Grafana dashboard JSON to the repository:

- File: [documentation/grafana_dashboard_rate_limit.json](documentation/grafana_dashboard_rate_limit.json)

Import steps (quick):

1. Grafana → Create → Import → Upload the JSON file above (or paste contents).
2. Select your Prometheus datasource for the Prometheus panels and your Loki datasource for the Loki panel.
3. Adjust Prometheus expressions or log labels if your metric names or log labels differ from the examples.

Example queries used by the dashboard:

- Prometheus (rate-limited total):

  `sum(rate(app_rate_limited_total[5m]))`

- Prometheus (rate-limited by endpoint):

  `sum by (endpoint) (rate(app_rate_limited_total[5m]))`

- Loki (recent rate_limited log entries):

  `{app="moscowle"} |= "rate_limited"`

Notes:
- The dashboard expects either a Prometheus metric `app_rate_limited_total` (use an exporter if needed) or structured logs with `rate_limited` occurrences for the Loki panel.
- If you prefer, I can now:
  - Add the small Redis→Prometheus exporter (implement and test locally), or
  - Expand the Grafana dashboard (add alerts, single-stat panels, and templated variables).

Tell me which next step you want: "exporter" or "expand dashboard".

Alerts and Prometheus rules

I added a sample Prometheus alerting rules file to the repo:

- File: [documentation/prometheus_alerts_rate_limit.yml](documentation/prometheus_alerts_rate_limit.yml)

Contents (summary):

- `HighRateLimitTotal`: fires when `sum(rate(app_rate_limited_total[5m])) > 10` for 5 minutes (severity: warning).
- `HighRateLimitByEndpoint`: fires when an endpoint has `rate(...) > 5` per 5m for 5 minutes (severity: critical).

How to enable the rules

1. Copy `documentation/prometheus_alerts_rate_limit.yml` to your Prometheus rules directory (e.g., `/etc/prometheus/rules/`).
2. Reload Prometheus or restart the service so it picks up the new rules.
3. Configure Alertmanager with receivers (email, Slack, PagerDuty) and routing based on the `severity` label.

Example Alertmanager snippet (routes):

```yaml
route:
  receiver: 'default'
  routes:
  - match:
      severity: 'critical'
    receiver: 'oncall'
  - match:
      severity: 'warning'
    receiver: 'team-notify'
```

Next steps I can take now:
- Import and test the expanded Grafana dashboard locally (I can attempt a local Grafana import if you want).
- Implement the Redis→Prometheus exporter service to expose `app_rate_limited_total` and per-endpoint metrics directly for Prometheus scraping.

Which do you want: `import-dashboard` (try import locally) or `exporter` (implement exporter)?