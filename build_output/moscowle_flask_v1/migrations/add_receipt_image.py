import sqlite3
import os

DB_PATH = 'instance/moscowle.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(payment)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'receipt_image_path' not in columns:
            print("Adding receipt_image_path column to payment table...")
            cursor.execute("ALTER TABLE payment ADD COLUMN receipt_image_path VARCHAR(255)")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column receipt_image_path already exists.")
            
        # Add notes column if not exists (saw it used in template but not in model definition I read, just to be safe)
        if 'notes' not in columns:
             print("Adding notes column to payment table...")
             cursor.execute("ALTER TABLE payment ADD COLUMN notes TEXT")
             conn.commit()
             print("Migration for notes successful.")

    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
