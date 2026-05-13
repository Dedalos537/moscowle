# CSP Report-Only Mode and Reporting Endpoint

This document explains how to enable a Content Security Policy (CSP) in "report-only" mode to collect violations before enforcing the policy, and how to configure the app to receive and log CSP reports.

## How it works (what we added)
- `app/__init__.py` now reads two environment variables:
  - `CSP_REPORT_ONLY` (True/False) — when `True`, the CSP is sent in `Report-Only` mode so browsers only report violations without blocking resources.
  - `CSP_REPORT_URI` (string) — the path where the app will accept POST reports from browsers (default `/csp-report`).
- The app registers a POST endpoint at `CSP_REPORT_URI` that logs incoming reports as warnings. Reports are not stored in DB by default — you can add persistence/forwarding to Sentry or an external collector.

## Enabling report-only mode
Set these env vars in cPanel (or your environment manager):

```env
# Enable CSP report-only (collect reports before enforcing)
CSP_REPORT_ONLY=True
# Optional: change the report uri
CSP_REPORT_URI=/csp-report
```

After setting env vars, restart the Python application in cPanel.

## Sample browser report
Browsers send JSON like the following to the report endpoint:

```json
{
  "csp-report": {
    "document-uri": "https://your.domain/path",
    "referrer": "",
    "violated-directive": "script-src 'self'",
    "blocked-uri": "https://evil.example.com/script.js",
    "original-policy": "default-src 'self'; script-src 'self' 'unsafe-inline'"
  }
}
```

The app logs this payload as a warning. Two recommended aggregation options:

- Forwarding reports to Sentry: set `SENTRY_DSN` in the environment and the app will initialize `sentry-sdk` and send CSP reports as events. Configure `SENTRY_TRACES_SAMPLE_RATE` as needed.
- Persisting reports to a small DB table and building a lightweight UI for triage.

## Next steps (recommended)
- Enable `CSP_REPORT_ONLY=True` in staging for 1-2 weeks and monitor logs for legitimate violations.
- Tune `app/__init__.py` CSP settings to allow required third-party resources (analytics, CDNs, fonts).
- Once no critical violations appear, set `CSP_REPORT_ONLY=False` to start enforcing the policy.

## Troubleshooting
- If no reports appear, verify the browser's console for CSP reporting behavior and ensure the path is reachable.
- Ensure proxies or wafs do not drop `POST` requests to the report endpoint.

