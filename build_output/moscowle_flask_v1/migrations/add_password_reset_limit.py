
import sqlite3
import os

DB_PATH = 'instance/moscowle.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Migrating database to add admin_password_changed_count...")

    try:
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'admin_password_changed_count' not in columns:
            print("Adding admin_password_changed_count to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN admin_password_changed_count INTEGER DEFAULT 0")
        else:
            print("Column admin_password_changed_count already exists.")

    except Exception as e:
        print(f"Error updating user table: {e}")

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == '__main__':
    run_migration()
