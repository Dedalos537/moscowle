#!/usr/bin/env python3
"""
Script simple para probar conexión rápida a la base de datos
"""

from db.db import get_db_connection

def quick_test():
    try:
        print("Probando conexión...")
        connection = get_db_connection()
        print("✅ Conexión exitosa!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"Resultado de prueba: {result}")
        
        connection.close()
        print("Conexión cerrada")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_test()