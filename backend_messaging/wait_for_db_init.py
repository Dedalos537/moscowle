#!/usr/bin/env python3
"""wait_for_db_init.py
Python-based waiter that polls MySQL until the expected database and table exist.
Uses mysql-connector-python (already in requirements.txt).
"""
import os
import sys
import time
from mysql.connector import connect, Error


DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Rucula_530')
DB_NAME = os.getenv('DB_NAME', 'Moscowle_Complete')
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '60'))
SLEEP_SECONDS = float(os.getenv('SLEEP_SECONDS', '2'))


def check_mysql():
    try:
        # connect without specifying database first
        with connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, connection_timeout=5) as conn:
            with conn.cursor() as cur:
                # ensure DB exists
                cur.execute("SHOW DATABASES LIKE %s", (DB_NAME,))
                db_exists = cur.fetchone() is not None
                if not db_exists:
                    print(f"  - Database {DB_NAME} not found yet")
                    return False

                # check for roles table existence
                cur.execute(f"USE `{DB_NAME}`")
                cur.execute("SHOW TABLES LIKE 'roles'")
                has_roles = cur.fetchone() is not None
                if has_roles:
                    print(f"✔ Database and 'roles' table present in {DB_NAME}")
                    return True
                else:
                    print(f"  - '{DB_NAME}.roles' not present yet")
                    return False
    except Error as e:
        print(f"  - MySQL connection error: {e}")
        return False


def main():
    print(f"⏳ Waiting for MySQL at {DB_HOST} and for db_init to finish (DB: {DB_NAME})")
    attempts = 0
    while attempts < MAX_RETRIES:
        ok = check_mysql()
        if ok:
            print("✅ db_init appears complete — continuing")
            sys.exit(0)
        attempts += 1
        time.sleep(SLEEP_SECONDS)

    print(f"❌ Timeout waiting for db_init after {MAX_RETRIES} attempts", file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main()
