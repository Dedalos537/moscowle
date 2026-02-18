import sqlite3
import os

def check_field_exists(cursor, table_name, field_name):
    # Returns True if field exists, False otherwise
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    return field_name in columns

def update_schema_plan_type():
    db_path = os.path.join("instance", "moscowle.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        table = "user"
        new_fields = [
            ("plan_type", "VARCHAR(20) DEFAULT 'individual'"), # 'individual' or 'group'
            ("plan_type_2", "VARCHAR(20) DEFAULT 'individual'")
        ]
        
        print(f"Checking {table} table for plan_type fields...")
        
        for field, type_def in new_fields:
            if not check_field_exists(cursor, table, field):
                print(f"Adding {field} to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {field} {type_def}")
            else:
                print(f"Field {field} already exists.")

        conn.commit()
        print("Schema updated for Plan Type.")

    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema_plan_type()
