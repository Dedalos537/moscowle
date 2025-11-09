#!/usr/bin/env python3
"""
Script para migrar la tabla contact_inquiries
"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Rucula_530',
    'database': 'Moscowle_Complete',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def migrate_contact_inquiries():
    """Migrar la tabla contact_inquiries"""
    
    try:
        print("🔧 Migrando tabla contact_inquiries...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Agregar columnas faltantes
        migrations = [
            "ALTER TABLE contact_inquiries ADD COLUMN inquiry_code VARCHAR(20) UNIQUE AFTER id",
            "ALTER TABLE contact_inquiries ADD COLUMN subject VARCHAR(200) AFTER phone",
            "ALTER TABLE contact_inquiries ADD COLUMN urgency ENUM('low', 'medium', 'high') DEFAULT 'medium' AFTER service_interest",
            "ALTER TABLE contact_inquiries ADD COLUMN ip_address VARCHAR(45) AFTER source",
            "ALTER TABLE contact_inquiries ADD COLUMN user_agent TEXT AFTER ip_address",
            "ALTER TABLE contact_inquiries MODIFY COLUMN status ENUM('new', 'contacted', 'in_progress', 'resolved', 'closed') DEFAULT 'new'"
        ]
        
        for i, migration in enumerate(migrations, 1):
            try:
                cursor.execute(migration)
                print(f"✅ Migración {i}/{len(migrations)} completada")
            except Error as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print(f"⚠️ Migración {i}: Columna ya existe (ignorado)")
                else:
                    print(f"❌ Error en migración {i}: {e}")
        
        # Generar códigos únicos para registros existentes
        print("🔄 Generando códigos únicos para registros existentes...")
        cursor.execute("SELECT id FROM contact_inquiries WHERE inquiry_code IS NULL")
        records = cursor.fetchall()
        
        for record in records:
            record_id = record[0]
            inquiry_code = f"INQ{record_id:06d}"
            cursor.execute(
                "UPDATE contact_inquiries SET inquiry_code = %s WHERE id = %s",
                (inquiry_code, record_id)
            )
        
        connection.commit()
        
        print("✅ Migración completada exitosamente!")
        
        # Verificar estructura final
        cursor.execute("DESCRIBE contact_inquiries")
        columns = cursor.fetchall()
        
        print(f"\n📋 Estructura final de contact_inquiries ({len(columns)} columnas):")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
        
        return True
        
    except Error as e:
        print(f"❌ Error de MySQL: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    print("=" * 50)
    print("🔧 MIGRACIÓN DE BASE DE DATOS")
    print("=" * 50)
    
    if migrate_contact_inquiries():
        print("\n🚀 ¡Migración completada!")
    else:
        print("\n❌ Error en la migración")
    
    print("=" * 50)