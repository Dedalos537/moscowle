"""
Configuración de la base de datos
Centro de Terapias Juan Pablo II
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de conexión
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Rucula_530'),
    'database': os.getenv('DB_NAME', 'Moscowle_Complete'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

class DatabaseConnection:
    """Manejador de conexiones a la base de datos"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establecer conexión con la base de datos"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except Error as e:
            print(f"Error de conexión a MySQL: {e}")
            return False
    
    def disconnect(self):
        """Cerrar conexión con la base de datos"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def execute_query(self, query, params=None):
        """Ejecutar una consulta SELECT"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except Error as e:
            print(f"Error ejecutando consulta: {e}")
            return None
    
    def execute_update(self, query, params=None):
        """Ejecutar una consulta INSERT/UPDATE/DELETE"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return self.cursor.rowcount
        except Error as e:
            print(f"Error ejecutando actualización: {e}")
            self.connection.rollback()
            return None
    
    def get_last_insert_id(self):
        """Obtener el último ID insertado"""
        return self.cursor.lastrowid

def get_db_connection():
    """Factory function para obtener una nueva conexión"""
    db = DatabaseConnection()
    if db.connect():
        return db
    return None

# Test de conexión
def test_connection():
    """Probar la conexión a la base de datos"""
    db = get_db_connection()
    if db:
        result = db.execute_query("SELECT 'Conexión exitosa' as message")
        db.disconnect()
        return result is not None
    return False

if __name__ == "__main__":
    if test_connection():
        print("✅ Conexión a la base de datos exitosa")
    else:
        print("❌ Error de conexión a la base de datos")