#!/usr/bin/env python3
"""
Script para probar la conexión con la base de datos MySQL
"""

import pymysql
import sys
from dotenv import load_dotenv
import os

def test_database_connection():
    """
    Prueba la conexión con la base de datos y muestra información detallada
    """
    print("🔧 Probando conexión con la base de datos...")
    
    try:
        # Cargar variables de entorno
        load_dotenv(dotenv_path='.env')
        
        # Obtener configuración de la base de datos
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'centroju_moscowle'),
            'password': os.getenv('DB_PASSWORD', 'SUrs8gfNk4sY3jw85mUR'),
            'database': os.getenv('DB_NAME', 'centroju_moscowle'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        print(f"📋 Configuración de conexión:")
        print(f"   Host: {db_config['host']}")
        print(f"   Usuario: {db_config['user']}")
        print(f"   Base de datos: {db_config['database']}")
        print(f"   Charset: {db_config['charset']}")
        print()
        
        # Intentar conectar
        print("🔌 Estableciendo conexión...")
        connection = pymysql.connect(**db_config)
        
        print("✅ ¡Conexión establecida exitosamente!")
        
        # Probar consulta básica
        with connection.cursor() as cursor:
            # Información del servidor
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            print(f"📊 Versión de MySQL: {result['version']}")
            
            # Mostrar tablas disponibles
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print(f"📚 Tablas encontradas ({len(tables)}):")
                for table in tables:
                    table_name = list(table.values())[0]
                    print(f"   - {table_name}")
            else:
                print("⚠️  No se encontraron tablas en la base de datos")
            
            # Información de la base de datos
            cursor.execute("SELECT DATABASE() as current_db")
            current_db = cursor.fetchone()
            print(f"🎯 Base de datos actual: {current_db['current_db']}")
            
        connection.close()
        print("🔐 Conexión cerrada correctamente")
        return True
        
    except pymysql.Error as e:
        print(f"❌ Error de MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def test_specific_connection():
    """
    Prueba con configuración hardcodeada como fallback
    """
    print("\n🔄 Probando con configuración directa...")
    
    try:
        connection = pymysql.connect(
            host='localhost',
            user='centroju_moscowle',
            password='SUrs8gfNk4sY3jw85mUR',
            database='centroju_moscowle',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("✅ ¡Conexión directa exitosa!")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            print(f"🧪 Prueba básica: {result}")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en conexión directa: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Script de prueba de conexión a la base de datos")
    print("=" * 50)
    
    # Probar con variables de entorno
    success1 = test_database_connection()
    
    # Si falla, probar conexión directa
    if not success1:
        success2 = test_specific_connection()
        if not success2:
            print("\n💡 Posibles soluciones:")
            print("   1. Verificar que MySQL esté ejecutándose")
            print("   2. Verificar credenciales de acceso")
            print("   3. Verificar que la base de datos existe")
            print("   4. Verificar permisos del usuario")
            sys.exit(1)
    
    print("\n🎉 ¡Todo funciona correctamente!")