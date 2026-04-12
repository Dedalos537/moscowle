import requests
import re

session = requests.Session()

# 1. Obtener CSRF token del login
print("🔐 Obteniendo CSRF token...")
login_page = session.get('http://127.0.0.1:5001/login')
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None
print(f"   ✅ Token: {csrf_token[:30] if csrf_token else 'ERROR'}...\n")

# 2. Loguear
print("🔑 Haciendo login...")
login_resp = session.post(
    'http://127.0.0.1:5001/login',
    data={
        'email': 'admin@centrojuanpabloii.com',
        'password': 'SecurePass123!',
        'csrf_token': csrf_token
    },
    allow_redirects=True
)
print(f"   Status: {login_resp.status_code}")
print(f"   Redirigido a: {login_resp.url}\n")

# 3. Obtener CSRF del dashboard
print("📊 Accediendo a dashboard...")
dashboard = session.get('http://127.0.0.1:5001/admin/dashboard')
print(f"   Status: {dashboard.status_code}")
print(f"   Autenticado: {'Administrador' in dashboard.text}\n")

csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', dashboard.text)
csrf_token = csrf_match.group(1) if csrf_match else None

# 4. Enviar mensaje a Copilot
print("🤖 Enviando mensaje a Copilot...")
result = session.post(
    'http://127.0.0.1:5001/llama/chat/send',
    json={'message': 'Hola Llama, ¿funcionas?', 'page': 'admin/dashboard'},
    headers={'X-CSRFToken': csrf_token}
)

print(f"   Status: {result.status_code}")
if result.status_code == 200:
    # Check if it's JSON
    try:
        data = result.json()
        if data.get('success'):
            print(f"   ✅ ÉXITO!")
            print(f"\n   Respuesta de Llama:")
            print(f"   {data.get('data', {}).get('response')}")
        else:
            print(f"   ❌ Error: {data.get('error', {}).get('message')}")
    except:
        print(f"   ❌ HTML recibido (no JSON)")
        if 'script' in result.text[:500]:
            print("      (El usuario no está autenticado)")
else:
    print(f"   ❌ Error HTTP {result.status_code}")
