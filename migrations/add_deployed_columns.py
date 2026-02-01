#!/usr/bin/env python3
"""
Migration: Add deployed columns (therapy_type, duration_minutes) to Appointment table
"""

import sqlite3
import os

def add_deployed_columns():
    """Add existing production columns to local appointment table"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'moscowle.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Checking existing columns in appointment table...")
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(appointment)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Check and add therapy_type
        if 'therapy_type' in columns:
            print("✅ 'therapy_type' column already exists.")
        else:
            print("Adding 'therapy_type' column...")
            cursor.execute("ALTER TABLE appointment ADD COLUMN therapy_type VARCHAR(120)")
            print("✅ Added 'therapy_type' column.")

        # Check and add duration_minutes
        if 'duration_minutes' in columns:
            print("✅ 'duration_minutes' column already exists.")
        else:
            print("Adding 'duration_minutes' column...")
            cursor.execute("ALTER TABLE appointment ADD COLUMN duration_minutes INTEGER")
            print("✅ Added 'duration_minutes' column.")
        
        conn.commit()
        print("✅ Migration successful.")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    add_deployed_columns()
