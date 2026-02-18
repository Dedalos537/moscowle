#!/usr/bin/env python3
"""
Script para probar la configuración de email antes de crear pacientes.
Ejecuta: python test_email.py
"""

from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create minimal Flask app
app = Flask(__name__)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize Mail
mail = Mail(app)

def test_email_config():
    """Test email configuration"""
    print("=" * 60)
    print("PROBANDO CONFIGURACIÓN DE EMAIL")
    print("=" * 60)
    
    # Show current configuration
    print("\n📧 Configuración actual:")
    print(f"  Servidor: {app.config['MAIL_SERVER']}")
    print(f"  Puerto: {app.config['MAIL_PORT']}")
    print(f"  TLS: {app.config['MAIL_USE_TLS']}")
    print(f"  Usuario: {app.config['MAIL_USERNAME']}")
    print(f"  Remitente: {app.config['MAIL_DEFAULT_SENDER']}")
    print(f"  Contraseña: {'*' * len(app.config['MAIL_PASSWORD']) if app.config['MAIL_PASSWORD'] else 'NO CONFIGURADA'}")
    
    # Check if all required fields are set
    if not all([app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']]):
        print("\n❌ ERROR: MAIL_USERNAME o MAIL_PASSWORD no están configurados en .env")
        print("\n📝 Por favor configura tu .env con una de estas opciones:")
        print("\n  Opción 1 - Mailtrap (recomendado para testing):")
        print("    1. Regístrate gratis en https://mailtrap.io")
        print("    2. Copia las credenciales SMTP de 'My Inbox'")
        print("    3. Actualiza tu .env:")
        print("       MAIL_SERVER=sandbox.smtp.mailtrap.io")
        print("       MAIL_PORT=2525")
        print("       MAIL_USERNAME=tu_username_mailtrap")
        print("       MAIL_PASSWORD=tu_password_mailtrap")
        print("\n  Opción 2 - Gmail (para enviar emails reales):")
        print("    1. Habilita verificación en 2 pasos: https://myaccount.google.com/security")
        print("    2. Genera App Password: Busca 'Contraseñas de aplicaciones'")
        print("    3. Actualiza tu .env:")
        print("       MAIL_SERVER=smtp.gmail.com")
        print("       MAIL_PORT=587")
        print("       MAIL_USERNAME=tu_email@gmail.com")
        print("       MAIL_PASSWORD=tu_app_password_16_caracteres")
        return False
    
    # Try to send a test email
    print("\n📤 Intentando enviar email de prueba...")
    
    try:
        with app.app_context():
            # Destination email
            test_recipient = input("\n✉️  Ingresa el email destino para la prueba: ").strip()
            if not test_recipient:
                test_recipient = app.config['MAIL_USERNAME']
            
            # Create test message
            msg = Message(
                subject="Prueba de Email - Moscowle",
                recipients=[test_recipient],
                body="""
¡Hola!

Este es un email de prueba del sistema Moscowle.

Si recibiste este mensaje, la configuración de email está funcionando correctamente. ✅

Credenciales de ejemplo:
Email: paciente@ejemplo.com
Contraseña temporal: Test123456!

Saludos,
Sistema Moscowle
                """.strip()
            )
            
            # Send
            mail.send(msg)
            
            print("\n✅ ¡EMAIL ENVIADO EXITOSAMENTE!")
            print(f"   Destinatario: {test_recipient}")
            
            if 'mailtrap' in app.config['MAIL_SERVER']:
                print("\n📬 Como estás usando Mailtrap:")
                print("   1. Ve a https://mailtrap.io")
                print("   2. Entra a 'My Inbox'")
                print("   3. Verás el email de prueba ahí")
            else:
                print(f"\n📬 Revisa la bandeja de entrada de {test_recipient}")
            
            print("\n🎉 La configuración de email está lista para usar en Moscowle.")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR al enviar email: {str(e)}")
        print("\n🔍 Posibles causas:")
        print("   • Credenciales incorrectas en .env")
        print("   • Si usas Gmail: necesitas App Password, no contraseña normal")
        print("   • Si usas Mailtrap: verifica username y password")
        print("   • Firewall bloqueando puerto 587/2525")
        print("\n💡 Solución:")
        print("   1. Verifica las credenciales en tu archivo .env")
        print("   2. Si usas Gmail, genera una App Password")
        print("   3. Reinicia el servidor después de cambiar .env")
        return False

if __name__ == '__main__':
    print("\n")
    success = test_email_config()
    print("\n" + "=" * 60)
    if success:
        print("✅ TODO LISTO - Puedes crear pacientes en Moscowle")
    else:
        print("⚠️  CONFIGURA EL EMAIL antes de continuar")
    print("=" * 60 + "\n")
