#!/usr/bin/env python3
"""
Create or update administrator user in the database using SQLAlchemy models.
Run from the `backend` folder, with your virtualenv activated.

Usage:
    python create_admin.py --email admin@example.com --password S3cret

If no args provided, defaults are read from environment or fall back to:
    mamiebamos2@gmail.com / 18marzo69!

This script uses the same app factory and models to safely insert the admin user.
"""
import os
import argparse

from app import create_app
from app.extensions import db
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description='Create admin user')
    parser.add_argument('--email', type=str, help='Admin email')
    parser.add_argument('--password', type=str, help='Admin password')
    args = parser.parse_args()

    email = args.email or os.getenv('ADMIN_EMAIL') or 'mamiebamos2@gmail.com'
    password = args.password or os.getenv('ADMIN_PASSWORD') or '18marzo69!'

    app = create_app()
    with app.app_context():
        # Ensure roles table has an 'admin' role and get its id (schema requires non-null role_id)
        from sqlalchemy import text
        role_row = db.session.execute(text("SELECT id FROM roles WHERE name = :name"), {'name': 'admin'}).fetchone()
        if not role_row:
            print('No "admin" role found in roles table — creating one.')
            db.session.execute(text("INSERT INTO roles (name, description, permissions) VALUES (:name, :desc, :perms)"),
                               {'name': 'admin', 'desc': 'Administrator role', 'perms': '{}'})
            db.session.commit()
            role_row = db.session.execute(text("SELECT id FROM roles WHERE name = :name"), {'name': 'admin'}).fetchone()

        admin_role_id = role_row[0] if role_row else None

        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"User with email {email} already exists (id={existing.id}). Updating password and activating.")
            existing.set_password(password)
            # set role_id if schema requires it
            if admin_role_id is not None:
                try:
                    existing.role_id = admin_role_id
                except Exception:
                    pass
            # set active/status fields if present
            try:
                existing.status = 'active'
            except Exception:
                pass
            db.session.commit()
            print("Updated password and activated user.")
            return

        # create user with email (schema doesn't have username column)
        user = User(email=email)
        user.set_password(password)
        # assign admin role id if available (schema requires role_id non-null)
        if admin_role_id is not None:
            try:
                user.role_id = admin_role_id
            except Exception:
                pass
        try:
            user.status = 'active'
        except Exception:
            pass
        db.session.add(user)
        db.session.commit()
        print(f"Created admin user {email} with id={user.id}")


if __name__ == '__main__':
    main()
