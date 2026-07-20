#!/bin/sh
set -e

# ---------------------------------------------------------------
# Moscowle IA — Docker Entrypoint
# Uses only POSIX sh features — works on Linux, macOS, Windows/WSL
# ---------------------------------------------------------------

# --- Wait for database ---
if [ -n "$SQLALCHEMY_DATABASE_URI" ]; then
    echo "Waiting for database..."
    python -c "
import os, time, sqlalchemy
uri = os.environ['SQLALCHEMY_DATABASE_URI']
for i in range(30):
    try:
        sqlalchemy.create_engine(uri).connect()
        print('Database available')
        break
    except Exception as e:
        if i == 29:
            print(f'Database timeout: {e}')
            exit(1)
        time.sleep(1)
"
fi

# --- Run database migrations ---
echo "Running database migrations..."
python apply_itil_columns.py || echo "Warning: ITIL columns migration (non-fatal)"
flask db upgrade || echo "Warning: flask db upgrade failed (non-fatal)"

# --- Seed database if no admin user exists ---
echo "Checking if seed is needed..."
python -c "
import os
from app import create_app
from app.extensions import db, bcrypt

app = create_app()
with app.app_context():
    from app.models import User
    admin_email = os.environ.get('ADMIN_EMAIL', 'diegocenteno537@gmail.com')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            email=admin_email,
            password=bcrypt.generate_password_hash(admin_pass).decode('utf-8'),
            username='admin',
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin created: {admin_email}')
    else:
        try:
            if not bcrypt.check_password_hash(admin.password, admin_pass):
                admin.password = bcrypt.generate_password_hash(admin_pass).decode('utf-8')
                db.session.commit()
                print(f'Admin password reset: {admin_email}')
            else:
                print('Admin already exists and password is valid')
        except Exception:
            admin.password = bcrypt.generate_password_hash(admin_pass).decode('utf-8')
            db.session.commit()
            print(f'Admin password reset (hash incompatible): {admin_email}')
" || echo "Warning: seed failed (non-fatal)"

# --- Start nginx in background (production mode) ---
if [ "${FLASK_ENV}" = "production" ]; then
    echo "Starting nginx..."
    nginx -g "daemon off;" &
fi

# --- Execute the main command ---
exec "$@"
