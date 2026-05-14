import sqlite3
import os
from datetime import datetime

DB_PATH = 'instance/moscowle.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Migrating database to add Sedes (Branches)...")

    try:
        # 1. Create Sede table
        print("Creating sede table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sede (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                address VARCHAR(255),
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert initial data if empty
        cursor.execute("SELECT count(*) FROM sede")
        if cursor.fetchone()[0] == 0:
            print("Inserting default sedes: Talara, Piura")
            cursor.execute("INSERT INTO sede (name, active, created_at) VALUES (?, ?, ?)", 
                           ('Talara', 1, datetime.utcnow()))
            cursor.execute("INSERT INTO sede (name, active, created_at) VALUES (?, ?, ?)", 
                           ('Piura', 1, datetime.utcnow()))

    except Exception as e:
        print(f"Error creating sede table: {e}")

    try:
        # 2. Add sede_id to User table (for Patients mostly, but available to all users)
        # Check if column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'sede_id' not in columns:
            print("Adding sede_id to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN sede_id INTEGER REFERENCES sede(id)")
    except Exception as e:
        print(f"Error adding sede_id to user table: {e}")

    try:
        # 3. Create therapist_sede association table
        print("Creating therapist_sede table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS therapist_sede (
                therapist_id INTEGER NOT NULL,
                sede_id INTEGER NOT NULL,
                PRIMARY KEY (therapist_id, sede_id),
                FOREIGN KEY (therapist_id) REFERENCES user (id),
                FOREIGN KEY (sede_id) REFERENCES sede (id)
            )
        """)
    except Exception as e:
        print(f"Error creating therapist_sede table: {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
