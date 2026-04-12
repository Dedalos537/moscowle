import requests
import re

session = requests.Session()

# 1. Login
login_page = session.get('http://127.0.0.1:5001/auth/login')
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None

login_resp = session.post(
    'http://127.0.0.1:5001/auth/login',
    data={'email': 'admin@centrojuanpabloii.com', 'password': 'SecurePass123!', 'csrf_token': csrf_token}
)

# 2. Get new CSRF
dashboard = session.get('http://127.0.0.1:5001/admin/dashboard')
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', dashboard.text)
csrf_token = csrf_match.group(1) if csrf_match else None

# 3. Send message
result = session.post(
    'http://127.0.0.1:5001/llama/chat/send',
    json={'message': 'Hola!', 'page': 'admin/dashboard'},
    headers={'X-CSRFToken': csrf_token}
)

print(f"Status: {result.status_code}")
if result.status_code == 200:
    data = result.json()
    print(f"Success: {data.get('success')}")
    if data.get('success'):
        print(f"Response: {data.get('data', {}).get('response')}")
else:
    print(f"Error: {result.text[:200]}")
