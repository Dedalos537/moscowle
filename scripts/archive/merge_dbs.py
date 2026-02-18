import sqlite3
import shutil
import os
from datetime import datetime

# Paths
DEPLOY_DB = 'uploads/moscowle.db'
LOCAL_DB = 'instance/moscowle.db'
MERGED_DB = 'instance/moscowle_merged.db'

def get_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def merge_databases():
    if not os.path.exists(DEPLOY_DB):
        print(f"Error: {DEPLOY_DB} not found.")
        return

    if not os.path.exists(LOCAL_DB):
        print(f"Error: {LOCAL_DB} not found.")
        return

    # Create a copy of Local DB as Merged DB
    print(f"Creating merged database at {MERGED_DB}...")
    shutil.copy2(LOCAL_DB, MERGED_DB)

    # Dictionary to track primary keys for conflict resolution
    # Table Name -> Primary Key Column
    # Assuming 'id' is prevalent, but need to check schema if possible. 
    # For simplicity in this script, we'll try to insert and ignore duplicates based on primary key.
    
    conn_deploy = sqlite3.connect(DEPLOY_DB)
    conn_merged = sqlite3.connect(MERGED_DB)
    
    tables = get_tables(conn_deploy)
    
    for table in tables:
        if table == 'sqlite_sequence': continue # Skip internal SQLite table
        
        print(f"Merging table: {table}")
        
        # Get all rows from deploy DB
        cursor_deploy = conn_deploy.cursor()
        try:
            cursor_deploy.execute(f"SELECT * FROM {table}")
            rows = cursor_deploy.fetchall()
            
            # Get column names
            col_names = [description[0] for description in cursor_deploy.description]
            placeholders = ', '.join(['?'] * len(col_names))
            cols = ', '.join(col_names)
            
            cursor_merged = conn_merged.cursor()
            
            # Attempt to insert rows. detailed conflict resolution is hard without explicit schema knowledge.
            # We will use INSERT OR IGNORE to avoid primary key collisions.
            # If the user wants to prioritize deploy data over local for conflicts, we'd use REPLACE.
            # Let's assume we want to KEEP local data if conflict, adds new from deploy.
            query = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"
            
            cursor_merged.executemany(query, rows)
            conn_merged.commit()
            print(f"  Processed {len(rows)} rows for {table}.")
            
        except Exception as e:
            print(f"  Error merging table {table}: {e}")

    conn_deploy.close()
    conn_merged.close()
    print(f"Merge completed. Merged database is at {MERGED_DB}")

if __name__ == "__main__":
    merge_databases()
