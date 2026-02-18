import sqlite3
import os

def check_field_exists(cursor, table_name, field_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    return field_name in columns

def update_schema():
    db_path = os.path.join("instance", "moscowle.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add columns to user table
        print("Checking User table columns for therapist schedule...")
        
        if not check_field_exists(cursor, "user", "work_start_time"):
            print("Adding work_start_time to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN work_start_time VARCHAR(5)")
            
        if not check_field_exists(cursor, "user", "work_end_time"):
            print("Adding work_end_time to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN work_end_time VARCHAR(5)")
            
        if not check_field_exists(cursor, "user", "work_days"):
            print("Adding work_days to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN work_days VARCHAR(20)")

        conn.commit()
        print("Schema updated successfully.")

    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
