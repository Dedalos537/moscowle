# CSP Reports Stored in the Database

This document describes the `csp_report` table and how to inspect CSP violation reports saved by the app.

## Table: `csp_report`
Columns:
- `id` (int): primary key
- `received_at` (datetime): when the report was received
- `document_uri` (string): URL where the violation happened
- `violated_directive` (string): which directive was violated (e.g., `script-src`)
- `blocked_uri` (string): resource that was blocked
- `original_policy` (text): the policy string sent to the browser
- `raw_report` (text): full JSON payload received
- `ip_address` (string): client IP captured from request
- `user_id` (int): optional user id if the user was authenticated when report received

## How reports are inserted
- The app registers a POST endpoint (default `/csp-report`) and persists incoming reports into `csp_report`.
- If `SENTRY_DSN` is configured, the same report is also forwarded to Sentry.

## Query examples (SQLite)
- Show recent reports:

```sql
SELECT id, received_at, document_uri, violated_directive, blocked_uri
FROM csp_report
ORDER BY received_at DESC
LIMIT 50;
```

- Count violations by blocked URI:

```sql
SELECT blocked_uri, COUNT(*) as cnt
FROM csp_report
GROUP BY blocked_uri
ORDER BY cnt DESC
LIMIT 20;
```

## Notes
- `raw_report` stores the original payload as text; you can parse it in Python for deeper analysis.
- For long-term retention, consider exporting reports to an external analytics platform or periodically archiving older rows.
