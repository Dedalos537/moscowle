import requests
import re

session = requests.Session()

# 1. Login
print("1. Login...")
login_page = session.get('http://127.0.0.1:5001/auth/login')
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None
print(f"   CSRF Token: {csrf_token[:30] if csrf_token else 'NOT FOUND'}...")

login_resp = session.post(
    'http://127.0.0.1:5001/auth/login',
    data={'email': 'admin@centrojuanpabloii.com', 'password': 'SecurePass123!', 'csrf_token': csrf_token}
)
print(f"   Login Status: {login_resp.status_code}")
print(f"   Login URL: {login_resp.url}")

# Check first message response
dashboard = session.get('http://127.0.0.1:5001/admin/dashboard')
print(f"\n2. Dashboard access: {dashboard.status_code}")
print(f"   Has 'Administrador': {'Administrador' in dashboard.text}")

# Get CSRF for message
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', dashboard.text)
csrf_token = csrf_match.group(1) if csrf_match else None

result = session.post(
    'http://127.0.0.1:5001/llama/chat/send',
    json={'message': 'Hola!', 'page': 'admin/dashboard'},
    headers={'X-CSRFToken': csrf_token}
)

print(f"\n3. Copilot endpoint:")
print(f"   Status: {result.status_code}")
print(f"   Content-Type: {result.headers.get('Content-Type')}")
print(f"   Response (first 300 chars):")
print(f"   {result.text[:300]}")
