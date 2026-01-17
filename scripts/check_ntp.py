#!/usr/bin/env python3
"""Check system time offset against an NTP server without requiring root.
Usage: python scripts/check_ntp.py [--server pool.ntp.org] [--threshold-seconds 5]
Exits with code 0 if offset <= threshold, 2 if greater, 1 on error.
"""
import argparse
import datetime
import sys

try:
    import ntplib
except Exception:
    ntplib = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default='pool.ntp.org')
    parser.add_argument('--threshold-seconds', type=float, default=5.0)
    args = parser.parse_args()

    if ntplib is None:
        print('ntplib not installed. Install with `pip install ntplib` or add to requirements.', file=sys.stderr)
        return 1

    client = ntplib.NTPClient()
    try:
        res = client.request(args.server, version=3)
    except Exception as e:
        print(f'NTP request failed: {e}', file=sys.stderr)
        return 1

    # NTP time
    ntp_time = datetime.datetime.utcfromtimestamp(res.tx_time)
    local_time = datetime.datetime.utcnow()
    offset = (local_time - ntp_time).total_seconds()

    print(f'NTP server: {args.server}')
    print(f'NTP time (UTC): {ntp_time.isoformat()}')
    print(f'Local time (UTC): {local_time.isoformat()}')
    print(f'Offset seconds (local - ntp): {offset:.3f}')

    if abs(offset) > args.threshold_seconds:
        print(f'WARNING: clock skew exceeds threshold ({args.threshold_seconds}s)')
        return 2

    print('OK: clock synchronized within threshold')
    return 0


if __name__ == '__main__':
    sys.exit(main())
