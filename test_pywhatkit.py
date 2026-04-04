#!/usr/bin/env python3
"""
Simple test script for pywhatkit WhatsApp automation
Run: python3 test_pywhatkit.py
"""
import pywhatkit
from datetime import datetime, timedelta
import sys

def test_pywhatkit():
    """Test pywhatkit by scheduling a test message"""
    
    # Test phone number (Peru format)
    test_phone = "+51921507470"
    
    # Calculate send time (2 minutes from now)
    now = datetime.now()
    future_time = now + timedelta(minutes=2)
    
    print("=" * 60)
    print("🧪 pywhatkit Test")
    print("=" * 60)
    print(f"✓ Librería version: {pywhatkit.__version__ if hasattr(pywhatkit, '__version__') else 'Latest'}")
    print(f"✓ Mensaje destinado a: {test_phone}")
    print(f"✓ Hora actual: {now.strftime('%H:%M:%S')}")
    print(f"✓ Hora de envío programada: {future_time.strftime('%H:%M:%S')}")
    print()
    print("📝 Mensaje a enviar:")
    print("-" * 60)
    
    test_message = """¡Hola! 👋

Este es un mensaje de prueba de pywhatkit desde moscowle_ia_mvp.

Si ves este mensaje, significa que:
✅ pywhatkit funciona correctamente
✅ La integración está configurada
✅ Puedes usar WhatsApp de forma GRATUITA

Muchas gracias por probar,
Centro de Terapias"""
    
    print(test_message)
    print("-" * 60)
    print()
    
    try:
        print("🚀 Programando envío in pywhatkit...")
        print("   (Se abrirá Chrome automáticamente en ~2 minutos)")
        print()
        
        pywhatkit.sendwhatmsg(
            phone_number=test_phone,
            message=test_message,
            time_hour=future_time.hour,
            time_min=future_time.minute,
            wait_time=15,  # Wait 15 seconds for message to send
            tab_close=True  # Close tab after sending
        )
        
        print("✅ ÉXITO: Mensaje programado correctamente")
        print()
        print("📋 Próximos pasos:")
        print("   1. Chrome se abrirá automáticamente en 2 minutos")
        print("   2. WhatsApp Web cargará y buscará el contacto")
        print("   3. El mensaje se escribirá automáticamente")
        print("   4. Se enviará sin intervención manual")
        print("   5. La pestaña se cerrará automáticamente")
        print()
        print("⏰ Por favor espera 2 minutos...")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("🔍 Posibles causas:")
        print("   1. Chrome/Chromium no está instalado")
        print("   2. El número no existe en WhatsApp")
        print("   3. No hay conexión a Internet")
        print("   4. WhatsApp Web está siendo bloqueado por firewall")
        print()
        return False

if __name__ == "__main__":
    success = test_pywhatkit()
    sys.exit(0 if success else 1)
