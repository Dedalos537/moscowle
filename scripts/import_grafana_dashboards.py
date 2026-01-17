#!/usr/bin/env python3
"""
Simple Grafana dashboard importer.

Usage:
  python3 scripts/import_grafana_dashboards.py --url http://localhost:3000 --api-key <KEY>
or
  python3 scripts/import_grafana_dashboards.py --url http://localhost:3000 --user admin --password admin

This script reads the two dashboard JSON files under `documentation/` and POSTs them
to the Grafana API `/api/dashboards/db` with `overwrite=true`.
"""

import argparse
import json
import os
import sys
import requests


def import_dashboard(session, url, path):
    with open(path, 'r') as f:
        dashboard = json.load(f)
    payload = {'dashboard': dashboard, 'overwrite': True}
    resp = session.post(f"{url.rstrip('/')}/api/dashboards/db", json=payload)
    return resp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='Grafana base URL (e.g. http://localhost:3000)')
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument('--api-key', help='Grafana API key with Editor privileges')
    auth.add_argument('--user', help='Grafana username (use with --password)')
    parser.add_argument('--password', help='Grafana password (use with --user)')
    parser.add_argument('--files', nargs='*', default=[
        'documentation/grafana_dashboard_rate_limit.json',
        'documentation/grafana_dashboard_rate_limit_expanded.json'
    ])
    args = parser.parse_args()

    session = requests.Session()
    headers = {'Content-Type': 'application/json'}
    if args.api_key:
        session.headers.update({'Authorization': f'Bearer {args.api_key}'})
    else:
        if not args.password:
            print('When using --user you must provide --password', file=sys.stderr)
            sys.exit(2)
        session.auth = (args.user, args.password)

    for p in args.files:
        if not os.path.exists(p):
            print('Skipping missing file:', p)
            continue
        print('Importing', p)
        r = import_dashboard(session, args.url, p)
        try:
            print('Result:', r.status_code, r.json())
        except Exception:
            print('Result:', r.status_code, r.text)


if __name__ == '__main__':
    main()
