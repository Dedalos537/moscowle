import sqlite3
import os
from app import create_app, db
from sqlalchemy import text
import sys

# Configurar ruta para imports
sys.path.append(os.getcwd())

def migrate_data():
    app = create_app()
    
    sqlite_db_path = os.path.join(os.getcwd(), 'instance', 'moscowle_merged.db')
    if not os.path.exists(sqlite_db_path):
        print(f"ERROR: No se encuentra la base de datos origen: {sqlite_db_path}")
        return

    print(f"Origen (SQLite): {sqlite_db_path}")
    
    with app.app_context():
        print(f"Destino (MySQL): {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # 1. Probar conexión y crear tablas
        try:
            print("Conectando a MySQL y creando tablas si no existen...")
            db.create_all()
            print("Esquema verificado en MySQL.")
        except Exception as e:
            print(f"ERROR conectando a MySQL: {e}")
            print("Verifica que tu IP esté permitida en 'Remote Database Access' en cPanel.")
            return

        # 2. Conectar a SQLite
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Obtener lista de tablas
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        # Desactivar chequeo de claves foráneas para importar sin problemas de orden
        db.session.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        db.session.commit()
        
        try:
            for table in tables:
                if table in ['alembic_version']: continue
                
                print(f"Migrando tabla: {table}...", end=" ")
                
                # Leer datos de SQLite
                try:
                    sqlite_cursor.execute(f"SELECT * FROM {table}")
                    rows = sqlite_cursor.fetchall()
                    columns = [description[0] for description in sqlite_cursor.description]
                    
                    if not rows:
                        print("Vacía. Saltando.")
                        continue
                        
                    # Limpiar tabla destino (Opcional - usa TRUNCATE o DELETE)
                    # Precaución: Esto borra lo que haya en producción.
                    # db.session.execute(text(f"DELETE FROM {table}"))
                    
                    # Construir INSERT
                    placeholders = ', '.join([':' + col for col in columns])
                    sql = text(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})")
                    
                    # Convertir filas a lista de dicts para SQLAlchemy
                    data_to_insert = []
                    
                    # --- FILTRADO DE COLUMNAS (Fix Schema Mismatch) ---
                    # Obtener columnas reales de la tabla destino en MySQL
                    try:
                        # Hacemos una query vacía para ver las columnas
                        dest_cursor = db.session.execute(text(f"SELECT * FROM {table} LIMIT 0"))
                        dest_columns = set(dest_cursor.keys())
                    except Exception as e:
                        print(f"Warning: No se pudieron leer columnas destino de {table}, asumiendo iguales. {e}")
                        dest_columns = set(columns)

                    valid_columns = [col for col in columns if col in dest_columns]
                    
                    if len(valid_columns) != len(columns):
                        ignored = set(columns) - set(valid_columns)
                        print(f"  [Info] Ignorando columnas huérfanas en {table}: {ignored}")
                    
                    if not valid_columns:
                        print("  [Error] No hay columnas coincidentes. Saltando.")
                        continue
                        
                    # Reconstruir SQL solo con columnas válidas
                    placeholders = ', '.join([':' + col for col in valid_columns])
                    sql = text(f"INSERT INTO {table} ({', '.join(valid_columns)}) VALUES ({placeholders})")
                    # --------------------------------------------------

                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        # Filtrar el diccionario para tener solo keys válidas
                        valid_row_dict = {k: v for k, v in row_dict.items() if k in valid_columns}
                        data_to_insert.append(valid_row_dict)
                    
                    # Limpiar tabla destino (PRECAUCIÓN: Borra todo para reescribir)
                    print(f"  Limpiando destino {table}...")
                    db.session.execute(text(f"DELETE FROM {table}"))
                    
                    # Insertar en lotes
                    db.session.execute(sql, data_to_insert)
                    db.session.commit()
                    print(f"OK ({len(rows)} registros).")
                    
                except Exception as table_err:
                    print(f"\nERROR en tabla {table}: {table_err}")
                    db.session.rollback()
        
        finally:
            # Reactivar FK checks
            db.session.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
            db.session.commit()
            sqlite_conn.close()
            print("\n--- Migración Finalizada ---")

if __name__ == "__main__":
    migrate_data()
