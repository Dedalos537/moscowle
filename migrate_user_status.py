#!/usr/bin/env python3
"""
Script to migrate existing user status markers from notes to account_status field
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating user status data...")
    
    # Get all users
    users = User.query.all()
    migrated = 0
    
    for user in users:
        old_status = user.account_status
        
        # Determine status from existing data
        if not user.is_active:
            if user.notes:
                if '[RETIRED]' in user.notes:
                    user.account_status = 'retired'
                elif '[DEBTOR]' in user.notes:
                    user.account_status = 'debtor'
                else:
                    user.account_status = 'inactive'
            else:
                user.account_status = 'inactive'
        else:
            user.account_status = 'active'
        
        if old_status != user.account_status:
            print(f"  - {user.username}: {old_status or 'None'} → {user.account_status}")
            migrated += 1
    
    # Commit changes
    if migrated > 0:
        db.session.commit()
        print(f"\n✅ Successfully migrated {migrated} users!")
    else:
        print("\n✅ All users already have correct account_status")

print("Migration complete!")
