#!/usr/bin/env python3
import sys
import os
import mysql.connector
from mysql.connector import Error
import bcrypt
from datetime import datetime

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'database': 'Moscowle_Complete',
    'user': 'root',
    'password': 'Rucula_530'
}

def create_admin_user():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Hash de la contraseña
        password = "admin123"
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Primero crear el usuario
        user_query = """
        INSERT INTO users (
            email, password_hash, role_id, status, email_verified, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        user_data = (
            'admin@terapias.com',
            hashed_password.decode('utf-8'),
            1,  # role_id para admin
            'active',
            True,
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(user_query, user_data)
        user_id = cursor.lastrowid
        
        # Luego crear el perfil del usuario
        profile_query = """
        INSERT INTO user_profiles (
            user_id, first_name, last_name, phone, birth_date, 
            specialty, hire_date, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        profile_data = (
            user_id,
            'Administrador',
            'Sistema',
            '+521234567890',
            '1980-01-01',
            'Administración',
            datetime.now().date(),
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(profile_query, profile_data)
        
        print(f"✅ Usuario administrador creado con ID: {user_id}")
        print(f"📧 Email: admin@terapias.com")
        print(f"🔑 Contraseña: admin123")
        print(f"👤 Nombre: Administrador Sistema")
        
        # Confirmar cambios
        connection.commit()
        
    except Error as e:
        print(f"❌ Error al crear usuario administrador: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n🔐 Conexión a la base de datos cerrada")

if __name__ == "__main__":
    print("🚀 Creando usuario administrador...")
    create_admin_user()