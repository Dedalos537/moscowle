#!/usr/bin/env python3
"""
Script para crear un usuario ADMIN en la aplicación
Úsalo cuando necesites recuperar acceso admin

CÓMO USARLO EN cPANEL:
1. Abre File Manager
2. Ve a /home/centroju/moscowle_production_v1/
3. Crea un archivo nuevo: create_admin.py
4. Pega este contenido
5. Abre Terminal (o ejecuta por cPanel)
6. cd /home/centroju/moscowle_production_v1
7. source venv/bin/activate
8. python create_admin.py

Luego sigue las indicaciones.
"""

import sys
import os
from getpass import getpass

# Agregar el directorio de la app al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def create_admin_user():
    """Crea un usuario admin interactivo"""
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔐 CREAR USUARIO ADMIN")
        print("="*60 + "\n")
        
        # Validar inputs
        while True:
            email = input("📧 Email del admin: ").strip()
            if '@' in email and '.' in email:
                break
            print("❌ Email inválido, intenta de nuevo\n")
        
        while True:
            password = getpass("🔑 Contraseña (min 8 caracteres): ")
            if len(password) >= 8:
                break
            print("❌ Contraseña muy corta, intenta de nuevo\n")
        
        username = input("👤 Nombre de usuario (opcional): ").strip() or email.split('@')[0]
        
        # Verificar si existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"\n⚠️  El email {email} ya existe")
            update = input("¿Actualizar a ADMIN? (s/n): ").strip().lower()
            if update == 's':
                existing_user.role = 'admin'
                existing_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
                existing_user.username = username
                db.session.commit()
                print(f"✅ Usuario actualizado a ADMIN\n")
                print(f"📧 Email: {email}")
                print(f"🔑 Contraseña: ******* \n")
                return True
            else:
                print("❌ Operación cancelada\n")
                return False
        
        # Crear nuevo admin
        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_admin = User(
                email=email,
                username=username,
                password=hashed_password,
                role='admin',
                is_active=True,
                account_status='active'
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            print(f"\n✅ ADMIN CREADO EXITOSAMENTE\n")
            print(f"📧 Email: {email}")
            print(f"👤 Usuario: {username}")
            print(f"🔑 Contraseña: ******* \n")
            print("🎉 Ya puedes loguearte en: https://centrojuanpabloii.com\n")
            return True
            
        except Exception as e:
            print(f"\n❌ Error al crear admin: {str(e)}\n")
            return False

def list_admins():
    """Lista todos los admins actuales"""
    
    app = create_app()
    
    with app.app_context():
        admins = User.query.filter_by(role='admin').all()
        
        if not admins:
            print("\n❌ No hay admins creados aún\n")
            return
        
        print("\n" + "="*60)
        print("👑 ADMINS ACTUALES")
        print("="*60 + "\n")
        
        for i, admin in enumerate(admins, 1):
            print(f"{i}. {admin.email} ({admin.username})")
        
        print()

def main():
    print("\n🎯 HERRAMIENTA DE ADMINISTRACIÓN\n")
    print("1. Crear nuevo ADMIN")
    print("2. Actualizar usuario a ADMIN")
    print("3. Listar ADMINs")
    print("4. Salir\n")
    
    choice = input("Selecciona opción (1-4): ").strip()
    
    if choice == '1' or choice == '2':
        create_admin_user()
    elif choice == '3':
        list_admins()
    elif choice == '4':
        print("👋 Saliendo...\n")
    else:
        print("❌ Opción inválida\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelado por el usuario\n")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
