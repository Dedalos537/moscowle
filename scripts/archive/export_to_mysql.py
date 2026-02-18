import sqlite3

def dump_to_mysql(db_path, output_file):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- MySQL dump generated from SQLite database\n")
        f.write("SET FOREIGN_KEY_CHECKS=0;\n")
        f.write("SET SQL_MODE = \"NO_AUTO_VALUE_ON_ZERO\";\n")
        f.write("START TRANSACTION;\n\n")

        for table in tables:
            if table == 'sqlite_sequence': continue
            
            f.write(f"-- Data for table `{table}` --\n")
            
            # Get table data
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if not rows:
                continue

            # Get column names for insert statement
            # Note: We assume the table schema already exists in MySQL (from SQLAlchemy create_all)
            # If not, we'd need CREATE TABLE statements too, which are harder to translate perfectly.
            # Assuming the user will let SQLAlchemy create tables first or they already exist.
            
            # To be safe, we'll just generate INSERTS.
            # If we need CREATE TABLE, we rely on Flask-Migrate or db.create_all() running first.
            
            query = f"INSERT INTO `{table}` VALUES "
            
            values_list = []
            for row in rows:
                # Format values for MySQL
                formatted_values = []
                for val in row:
                    if val is None:
                        formatted_values.append("NULL")
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''").replace("\\", "\\\\")
                        formatted_values.append(f"'{escaped}'")
                    elif isinstance(val, (int, float)):
                        formatted_values.append(str(val))
                    else:
                        # Fallback for blobs or other types
                        formatted_values.append(f"'{str(val)}'")
                
                values_list.append("(" + ", ".join(formatted_values) + ")")
            
            f.write(f"INSERT INTO `{table}` VALUES \n")
            f.write(",\n".join(values_list))
            f.write(";\n\n")

        f.write("COMMIT;\n")
        f.write("SET FOREIGN_KEY_CHECKS=1;\n")

    conn.close()
    print(f"Dump saved to {output_file}")

if __name__ == "__main__":
    dump_to_mysql('instance/moscowle_merged.db', 'migration_dump.sql')
