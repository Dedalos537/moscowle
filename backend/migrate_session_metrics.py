#!/usr/bin/env python3
"""
Migration script to create the session_metrics table.
This can be run independently or called from the Flask-Migrate system.

Usage:
    python migrate_session_metrics.py
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import create_app
from app.extensions import db
from app.models.session_metrics import SessionMetrics


def run_migration():
    """Create the session_metrics table."""
    app = create_app()
    
    with app.app_context():
        print("[Migration] Starting session_metrics table creation...")
        
        try:
            # Create the table
            db.create_all()
            print("[Migration] ✅ SessionMetrics table created successfully!")
            
            # Verify the table exists
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'session_metrics' in tables:
                print("[Migration] ✅ Table 'session_metrics' verified in database")
                
                # Print column info
                columns = inspector.get_columns('session_metrics')
                print("\n[Migration] Table structure:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            else:
                print("[Migration] ❌ Table 'session_metrics' not found!")
                return False
                
            return True
            
        except Exception as e:
            print(f"[Migration] ❌ Error creating table: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
