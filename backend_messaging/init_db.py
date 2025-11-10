#!/usr/bin/env python3
"""
Script para inicializar la base de datos MySQL
Centro de Terapias Juan Pablo II - Sistema de Mensajería
"""

import mysql.connector
from mysql.connector import Error
import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

import os

# Configuración de conexión (leer desde variables de entorno para docker)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'database': os.getenv('DB_NAME', 'Moscowle_Complete'),
    'password': os.getenv('DB_PASSWORD', 'Rucula_530'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def create_database_and_tables():
    """Crear la base de datos y todas las tablas necesarias"""
    
    connection = None
    cursor = None
    
    try:
        # Conectar a MySQL sin especificar base de datos
        print("🔌 Conectando a MySQL...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Crear la base de datos
        print("📁 Creando base de datos 'Moscowle_Complete'...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS Moscowle_Complete CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE Moscowle_Complete")
        
        # Leer y ejecutar el script SQL
        script_path = os.path.join(os.path.dirname(__file__), 'init_database.sql')
        
        if not os.path.exists(script_path):
            print(f"❌ Error: No se encontró el archivo {script_path}")
            return False
            
        print("📄 Leyendo script SQL...")
        with open(script_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # Dividir en comandos individuales y ejecutar
        print("⚙️ Ejecutando comandos SQL...")
        
        # Filtrar comandos vacíos y comentarios
        commands = [cmd.strip() for cmd in sql_script.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
        
        success_count = 0
        
        for i, command in enumerate(commands, 1):
            if command.strip():
                try:
                    # Manejar delimitadores especiales para triggers
                    if 'DELIMITER' in command:
                        continue
                    
                    cursor.execute(command)
                    success_count += 1
                    print(f"✅ Comando {i}/{len(commands)} ejecutado")
                    
                except Error as e:
                    if "already exists" in str(e) or "Duplicate entry" in str(e):
                        print(f"⚠️ Comando {i}: Ya existe (ignorado)")
                        success_count += 1
                    else:
                        print(f"❌ Error en comando {i}: {e}")
        
        # Confirmar cambios
        connection.commit()
        
        print(f"\n🎉 Base de datos inicializada exitosamente!")
        print(f"📊 Comandos ejecutados: {success_count}/{len(commands)}")
        
        # Verificar tablas creadas
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\n📋 Tablas creadas ({len(tables)}):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"   - {table[0]}: {count} registros")
        
        return True
        
    except Error as e:
        print(f"❌ Error de MySQL: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("\n🔌 Conexión cerrada")

def test_connection():
    """Probar la conexión a la base de datos"""
    
    try:
        print("🧪 Probando conexión a Moscowle_Complete...")
        
        config = DB_CONFIG.copy()
        config['database'] = 'Moscowle_Complete'
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Probar una consulta simple
        cursor.execute("SELECT COUNT(*) as total FROM roles")
        result = cursor.fetchone()
        
        print(f"✅ Conexión exitosa! Roles en BD: {result[0]}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Error as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🏥 SISTEMA DE MENSAJERÍA - JUAN PABLO II")
    print("🔧 Inicialización de Base de Datos")
    print("=" * 60)
    
    # Crear base de datos y tablas
    if create_database_and_tables():
        print("\n" + "=" * 60)
        
        # Probar conexión
        if test_connection():
            print("\n🚀 ¡Sistema listo para usar!")
            print("\n📝 Próximos pasos:")
            print("   1. Instalar dependencias: pip install -r requirements.txt")
            print("   2. Ejecutar API: python main.py")
            print("   3. Documentación API: http://localhost:8000/docs")
        else:
            print("\n⚠️ Base de datos creada pero hay problemas de conexión")
            sys.exit(1)
    else:
        print("\n❌ Error al inicializar la base de datos")
        sys.exit(1)
    
    print("=" * 60)