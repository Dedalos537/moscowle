#!/usr/bin/env python3
"""
Script to add account_status column to user table if it doesn't exist
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    # Get the inspector
    inspector = inspect(db.engine)
    
    # Check if the column exists
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    if 'account_status' not in columns:
        print("Adding account_status column to user table...")
        
        # Execute raw SQL to add the column
        try:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    ALTER TABLE user 
                    ADD COLUMN account_status VARCHAR(50) DEFAULT 'active'
                """))
                connection.commit()
            print("✅ Column account_status added successfully!")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("✅ Column account_status already exists!")

print("Done!")
