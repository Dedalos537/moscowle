
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

    print("Migrating database to add Payment System...")

    # 1. Add columns to User table
    try:
        # Check if columns exist first to avoid errors on re-run
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'payment_plan' not in columns:
            print("Adding payment_plan to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN payment_plan TEXT DEFAULT 'monthly'")
        
        if 'payment_due_date' not in columns:
            print("Adding payment_due_date to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN payment_due_date DATE")
        
        if 'payment_amount' not in columns:
            print("Adding payment_amount to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN payment_amount FLOAT DEFAULT 0.0")
            
    except Exception as e:
        print(f"Error updating user table: {e}")

    # 2. Create Payment table
    try:
        print("Creating payment table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                amount FLOAT NOT NULL,
                date DATETIME NOT NULL,
                method VARCHAR(50) NOT NULL,
                reference VARCHAR(100),
                status VARCHAR(50) DEFAULT 'completed',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES user (id)
            )
        """)
        
        # Add index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_patient_id ON payment(patient_id)")
        
    except Exception as e:
        print(f"Error creating payment table: {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
