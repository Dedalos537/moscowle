#!/usr/bin/env python3
"""
Script para insertar datos básicos en la base de datos
"""

import mysql.connector
from mysql.connector import Error
import bcrypt

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Rucula_530',
    'database': 'Moscowle_Complete',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def insert_basic_data():
    """Insertar datos básicos necesarios"""
    
    try:
        print("🔌 Conectando a la base de datos...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Insertar roles básicos
        print("👥 Insertando roles básicos...")
        roles_data = [
            ('admin', 'Administrador del sistema', '{"all": true}'),
            ('therapist', 'Terapeuta profesional', '{"patients": ["read", "write"], "appointments": ["read", "write"], "messages": ["read", "write"]}'),
            ('assistant', 'Asistente administrativo', '{"inquiries": ["read", "write"], "messages": ["read", "write"], "appointments": ["read"]}')
        ]
        
        for role_name, description, permissions in roles_data:
            cursor.execute("""
                INSERT IGNORE INTO roles (name, description, permissions) 
                VALUES (%s, %s, %s)
            """, (role_name, description, permissions))
        
        # Crear hash de contraseña para admin (password: admin123)
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insertar usuario administrador
        print("🔐 Creando usuario administrador...")
        cursor.execute("""
            INSERT IGNORE INTO users (email, password_hash, role_id, status, email_verified) 
            VALUES (%s, %s, %s, %s, %s)
        """, ('admin@juanpablo2.com', password_hash, 1, 'active', True))
        
        # Obtener el ID del usuario admin
        cursor.execute("SELECT id FROM users WHERE email = %s", ('admin@juanpablo2.com',))
        admin_user = cursor.fetchone()
        
        if admin_user:
            admin_id = admin_user[0]
            
            # Insertar perfil del administrador
            print("👤 Creando perfil del administrador...")
            cursor.execute("""
                INSERT IGNORE INTO user_profiles (user_id, first_name, last_name, phone) 
                VALUES (%s, %s, %s, %s)
            """, (admin_id, 'Administrador', 'Principal', '+52 555 0000 0000'))
        
        # Confirmar cambios
        connection.commit()
        
        print("✅ Datos básicos insertados exitosamente!")
        
        # Mostrar resumen
        cursor.execute("SELECT COUNT(*) FROM roles")
        roles_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        profiles_count = cursor.fetchone()[0]
        
        print(f"📊 Resumen:")
        print(f"   - Roles: {roles_count}")
        print(f"   - Usuarios: {users_count}")
        print(f"   - Perfiles: {profiles_count}")
        
        print(f"\n🔑 Credenciales de administrador:")
        print(f"   Email: admin@juanpablo2.com")
        print(f"   Password: admin123")
        
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
    print("🔧 INSERCIÓN DE DATOS BÁSICOS")
    print("=" * 50)
    
    if insert_basic_data():
        print("\n🚀 ¡Datos básicos listos!")
    else:
        print("\n❌ Error al insertar datos básicos")
    
    print("=" * 50)