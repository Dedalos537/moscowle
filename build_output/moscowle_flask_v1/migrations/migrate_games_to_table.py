#!/usr/bin/env python3
"""
Migration script: Move games from JSON column to AppointmentGame table

This script migrates game assignments from the legacy Appointment.games JSON column
to the normalized AppointmentGame table.

Usage:
    python migrations/migrate_games_to_table.py [--dry-run]
    
Options:
    --dry-run    Show what would be migrated without making changes
"""

import sys
import os
import json

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from app.models import Appointment, Game, AppointmentGame
from flask import Flask
from config import Config

def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def migrate_games(dry_run=False):
    """Migrate games from JSON to AppointmentGame table"""
    
    app = create_app()
    
    with app.app_context():
        # Find all appointments with games in JSON column
        appointments = Appointment.query.filter(Appointment.games.isnot(None)).all()
        
        total = len(appointments)
        migrated = 0
        errors = []
        skipped = 0
        
        print(f"Found {total} appointments with games in JSON column")
        print("=" * 60)
        
        for appt in appointments:
            try:
                # Parse games JSON
                games_json = json.loads(appt.games)
                
                if not games_json:
                    skipped += 1
                    continue
                
                # Check if already migrated
                existing_count = AppointmentGame.query.filter_by(appointment_id=appt.id).count()
                if existing_count > 0:
                    print(f"⚠️  Appointment {appt.id}: Already has {existing_count} games in table, skipping")
                    skipped += 1
                    continue
                
                print(f"\n📋 Appointment {appt.id} ({appt.title}):")
                print(f"   JSON games: {games_json}")
                
                # Extract filenames (support both string and dict formats)
                filenames = []
                for game in games_json:
                    if isinstance(game, dict):
                        filename = game.get('name', '')
                    else:
                        filename = game
                    
                    if filename:
                        filenames.append(filename)
                
                if not filenames:
                    print(f"   ⚠️  No valid filenames found, skipping")
                    skipped += 1
                    continue
                
                # Find or create Game records
                for filename in filenames:
                    game = Game.query.filter_by(filename=filename).first()
                    
                    if not game:
                        # Check if file exists
                        game_path = os.path.join(app.static_folder, 'games', filename)
                        
                        if not os.path.exists(game_path):
                            print(f"   ⚠️  Game file not found: {filename}, skipping")
                            continue
                        
                        # Create Game record
                        game = Game(
                            title=filename.replace('.html', '').replace('_', ' ').title(),
                            filename=filename,
                            is_active=True
                        )
                        
                        if not dry_run:
                            db.session.add(game)
                            db.session.flush()
                        
                        print(f"   ✅ Created Game: {game.title} ({filename})")
                    else:
                        print(f"   ✓ Found Game: {game.title} ({filename})")
                    
                    # Create AppointmentGame association
                    if not dry_run:
                        assoc = AppointmentGame(
                            appointment_id=appt.id,
                            game_id=game.id if hasattr(game, 'id') else None
                        )
                        db.session.add(assoc)
                
                if not dry_run:
                    db.session.commit()
                
                migrated += 1
                print(f"   ✅ Migrated {len(filenames)} games")
                
            except Exception as e:
                error_msg = f"Appointment {appt.id}: {str(e)}"
                errors.append(error_msg)
                print(f"   ❌ Error: {error_msg}")
                
                if not dry_run:
                    db.session.rollback()
        
        print("\n" + "=" * 60)
        print(f"Migration {'DRY RUN ' if dry_run else ''}Summary:")
        print(f"  Total appointments: {total}")
        print(f"  Migrated: {migrated}")
        print(f"  Skipped: {skipped}")
        print(f"  Errors: {len(errors)}")
        
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"  - {error}")
        
        if dry_run:
            print("\n⚠️  DRY RUN: No changes were made to the database")
        else:
            print("\n✅ Migration completed successfully!")
        
        return migrated, skipped, errors

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("🔍 Running in DRY RUN mode - no changes will be made\n")
    
    try:
        migrate_games(dry_run=dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)
