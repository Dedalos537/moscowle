#!/usr/bin/env python3
"""
Simple migration: Add status tracking columns to Appointment table using raw SQL
"""

import sqlite3
import os

def add_status_tracking_columns():
    """Add status_changed_at and status_changed_by columns to appointment table"""
    
    # Get database path - the actual database file location
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
        
        has_status_changed_at = 'status_changed_at' in columns
        has_status_changed_by = 'status_changed_by' in columns
        
        if has_status_changed_at and has_status_changed_by:
            print("✓ Columns already exist. Migration skipped.")
            conn.close()
            return True
        
        print("Adding missing status tracking columns...")
        
        # Add status_changed_at column if missing
        if not has_status_changed_at:
            print("  - Adding status_changed_at column...")
            cursor.execute("ALTER TABLE appointment ADD COLUMN status_changed_at DATETIME")
            print("    ✓ status_changed_at added")
        
        # Add status_changed_by column if missing
        if not has_status_changed_by:
            print("  - Adding status_changed_by column...")
            cursor.execute("ALTER TABLE appointment ADD COLUMN status_changed_by INTEGER")
            print("    ✓ status_changed_by added")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        print("\nYou can now restart the application:")
        print("  python3 run.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        return False

if __name__ == '__main__':
    import sys
    try:
        success = add_status_tracking_columns()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
