#!/usr/bin/env python3
"""
Migration: Add attendance column to Appointment table
"""

import sqlite3
import os

def add_attendance_column():
    """Add attendance column to appointment table"""
    
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
        
        if 'attendance' in columns:
            print("✅ 'attendance' column already exists.")
            return True
        
        print("Adding 'attendance' column...")
        # 'pending', 'present', 'absent'
        cursor.execute("ALTER TABLE appointment ADD COLUMN attendance TEXT DEFAULT 'pending'")
        
        conn.commit()
        print("✅ Migration successful: Added 'attendance' column.")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    add_attendance_column()
