#!/usr/bin/env python3
"""
Migration: Add session_image table
"""

import sqlite3
import os

def add_session_images_table():
    """Create session_image table"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'moscowle.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        # Try to find it in current directory if running from instance
        db_path = 'moscowle.db'
        if not os.path.exists(db_path):
             print(f"❌ Database not found at: {db_path}")
             return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Checking if session_image table exists...")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_image'")
        if cursor.fetchone():
            print("✓ Table session_image already exists. Migration skipped.")
            conn.close()
            return True
        
        print("Creating session_image table...")
        
        create_table_sql = """
        CREATE TABLE session_image (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            image_path VARCHAR(500) NOT NULL,
            image_type VARCHAR(50) DEFAULT 'session_photo',
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            uploaded_by_id INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY(appointment_id) REFERENCES appointment(id),
            FOREIGN KEY(uploaded_by_id) REFERENCES user(id)
        );
        """
        
        cursor.execute(create_table_sql)
        print("✓ Table session_image created successfully")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    add_session_images_table()
