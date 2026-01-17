
import sys
import os
from sqlalchemy import text

# Add the project root to the path so we can import app
sys.path.append(os.getcwd())

from app import create_app, db

app = create_app()

with app.app_context():
    print("Checking for missing columns in 'message' table...")
    with db.engine.connect() as conn:
        # Check if columns exist (SQLite specific pragma, but try catch for general SQL)
        try:
            conn.execute(text("ALTER TABLE message ADD COLUMN attachment_path VARCHAR(500)"))
            print("Added column attachment_path")
        except Exception as e:
            print(f"Column attachment_path likely exists or error: {e}")

        try:
            conn.execute(text("ALTER TABLE message ADD COLUMN attachment_type VARCHAR(50)"))
            print("Added column attachment_type")
        except Exception as e:
            print(f"Column attachment_type likely exists or error: {e}")
            
        conn.commit()
    print("Migration check complete.")
