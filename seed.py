#!/usr/bin/env python3
"""Seed the database with an admin user from .env.local or defaults."""
import os
import sys
from dotenv import load_dotenv

# Load .env.local first, then .env
load_dotenv('.env.local')
load_dotenv('.env')

sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.extensions import db, bcrypt
from app.models import User

app = create_app()

with app.app_context():
    email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    password = os.getenv('ADMIN_PASSWORD', 'admin123')
    username = os.getenv('ADMIN_USERNAME', 'Admin')

    existing = User.query.filter_by(email=email).first()
    if existing:
        print(f'Admin user already exists: {existing.email} (role: {existing.role})')
    else:
        admin = User(
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role='admin',
            username=username,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user created: {email} / {password}')

    print(f'\nUsers in database: {User.query.count()}')
    for u in User.query.all():
        print(f'  - {u.id}: {u.email} ({u.role}) active={u.is_active}')
