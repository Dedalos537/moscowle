import sqlite3
import os

DB_PATH = 'instance/moscowle.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Migrating database to add ContactMessage table...")

    # Create table
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_message (
            id INTEGER PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL,
            phone VARCHAR(50),
            subject VARCHAR(200),
            message TEXT NOT NULL,
            service_interest VARCHAR(100),
            urgency VARCHAR(50) DEFAULT 'medium',
            status VARCHAR(50) DEFAULT 'unread',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        print("Table contact_message created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")

    conn.close()

if __name__ == "__main__":
    run_migration()
