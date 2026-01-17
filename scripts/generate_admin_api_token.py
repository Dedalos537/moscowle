#!/usr/bin/env python3
"""
Generate or rotate an ADMIN API token and store a bcrypt hash in the DB.
Usage:
  python scripts/generate_admin_api_token.py --rotate
  python scripts/generate_admin_api_token.py

Options:
  --rotate   Deactivate existing active tokens before creating a new one.
"""
import argparse
import secrets
import os
import sys

# Ensure project root is on sys.path when executed from scripts/
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
  sys.path.insert(0, ROOT)

from app import create_app
from app.extensions import db, bcrypt
from app.models import AdminAPIToken

parser = argparse.ArgumentParser()
parser.add_argument('--rotate', action='store_true', help='Deactivate existing tokens before creating a new one')
args = parser.parse_args()

app = create_app()
with app.app_context():
    if args.rotate:
        rows = AdminAPIToken.query.filter_by(is_active=True).all()
        for r in rows:
            r.deactivate()
        db.session.commit()
        print(f"Deactivated {len(rows)} existing token(s)")

    # Generate token
    token = secrets.token_urlsafe(32)
    token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
    new = AdminAPIToken(token_hash=token_hash, is_active=True)
    db.session.add(new)
    db.session.commit()

    print('\nNew ADMIN API token (copy and store securely):\n')
    print(token)
    print('\nStore this value in your environment as ADMIN_API_TOKEN or keep it secure.')
