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
        
        if 'discount' not in columns:
            print("Adding discount column to payment table...")
            cursor.execute("ALTER TABLE payment ADD COLUMN discount FLOAT DEFAULT 0.0")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column discount already exists.")

    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
