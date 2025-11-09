#!/usr/bin/env python3
import mysql.connector
from mysql.connector import Error

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'database': 'Moscowle_Complete',
    'user': 'root',
    'password': 'Rucula_530'
}

def check_users_table():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Describir tabla users
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        
        print("📋 Estructura de la tabla 'users':")
        print("-" * 50)
        for column in columns:
            print(f"Campo: {column[0]}, Tipo: {column[1]}, Null: {column[2]}, Key: {column[3]}, Default: {column[4]}")
        
        # Mostrar también las tablas disponibles
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\n📊 Tablas disponibles en la base de datos:")
        print("-" * 50)
        for table in tables:
            print(f"- {table[0]}")
        
    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    check_users_table()