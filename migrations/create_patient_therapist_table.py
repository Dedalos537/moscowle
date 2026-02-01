
from app import create_app, db
from app.models import patient_therapist
from sqlalchemy import text

def run_migration():
    app = create_app()
    with app.app_context():
        print("Migrating: Creating patient_therapist association table...")
        
        # Create table using metadata
        try:
            patient_therapist.create(db.engine)
            print("Table 'patient_therapist' created successfully.")
        except Exception as e:
            # Check if it's "table already exists" error
            if "already exists" in str(e):
                print("Table 'patient_therapist' already exists.")
            else:
                print(f"Error creating table: {e}")
                
        # Optional: Migrate existing data from assigned_therapist_id
        # This is CRITICAL to keep existing relationships working in the new system
        print("Migrating existing relationships...")
        try:
            # We use text() for raw SQL to ensure compatibility or SQLAlchemy Core
            # But since we are in app context, we can use db.session or engine
            
            # Select existing assignments
            result = db.session.execute(text("SELECT id, assigned_therapist_id FROM user WHERE role='jugador' AND assigned_therapist_id IS NOT NULL"))
            
            migrated_count = 0
            for row in result:
                pid, tid = row[0], row[1]
                # Check if exists
                exists = db.session.execute(
                    text("SELECT 1 FROM patient_therapist WHERE patient_id=:pid AND therapist_id=:tid"),
                    {"pid": pid, "tid": tid}
                ).scalar()
                
                if not exists:
                    db.session.execute(
                        text("INSERT INTO patient_therapist (patient_id, therapist_id) VALUES (:pid, :tid)"),
                        {"pid": pid, "tid": tid}
                    )
                    migrated_count += 1
            
            db.session.commit()
            print(f"Migrated {migrated_count} existing relationships.")
            
        except Exception as e:
            print(f"Error migrating data: {e}")

if __name__ == "__main__":
    run_migration()
