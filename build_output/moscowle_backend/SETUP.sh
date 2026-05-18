#!/bin/bash
# ============================================================
# SETUP - Despliegue en PythonAnywhere
# ============================================================
# 1. Crear cuenta en pythonanywhere.com
# 2. Web tab → Add new web app → Manual configuration → Python 3.11
# 3. Subir los archivos directo a /home/moscowle/:
#    - Subir moscowle_backend.zip por Files → Upload
#    - En Bash: unzip -o moscowle_backend.zip && rm moscowle_backend.zip
# 4. Crear virtualenv:
#    mkvirtualenv --python=python3.11 moscowle_backend
#    pip install -r requirements.txt
# 5. Web tab → Code:
#    - Working directory: /home/moscowle
#    - WSGI configuration file: pegar contenido de wsgi.py
#    - Virtualenv: /home/moscowle/.virtualenvs/moscowle_backend
# 6. En Web tab → Environment variables (agregar todas):
#    FLASK_ENV = production
#    SECRET_KEY = <clave_segura>
#    SQLALCHEMY_DATABASE_URI = mysql+pymysql://centroju_diego:Rucula_530@201.148.104.226:3306/centroju_moscowle_prod
#    SESSION_COOKIE_SECURE = True
#    GEMINI_API_KEY = <tu_key>
#    GROQ_API_KEY = <tu_key>
#    MAIL_SERVER = smtp.gmail.com
#    MAIL_PORT = 587
#    MAIL_USE_TLS = True
#    MAIL_USERNAME = <tu_email>
#    MAIL_PASSWORD = <tu_password>
#    MAIL_DEFAULT_SENDER = noreply@centrojuanpabloii.com
#    CORS_ORIGINS = https://moscowle.centrojuanpabloii.com http://localhost:4200
# 7. Reload web app (botón verde)
# 8. Verificar: https://moscowle.pythonanywhere.com/api/time
#
# ============================================================
# FRONTEND - Subir a cPanel
# ============================================================
# 1. Subir moscowle_frontend/ a public_html/moscowle.centrojuanpabloii.com/
# 2. Verificar: https://moscowle.centrojuanpabloii.com
# ============================================================
# MySQL - Remote access desde cPanel
# ============================================================
# cPanel → MySQL → Remote MySQL → Allow: %.pythonanywhere.com
# ============================================================

echo "=== INSTRUCCIONES ==="
echo "Backend:  PythonAnywhere (https://moscowle.pythonanywhere.com)"
echo "Frontend: cPanel (https://moscowle.centrojuanpabloii.com)"
echo "MySQL:    cPanel (remote access para PythonAnywhere)"
echo ""
echo "Pasos:"
echo "  1. cPanel → MySQL → Remote MySQL → agregar %.pythonanywhere.com"
echo "  2. PythonAnywhere → crear web app manual (Python 3.11)"
echo "  3. Subir archivos directo a /home/moscowle/ (sin subcarpeta)"
echo "  4. Crear venv + pip install -r requirements.txt"
echo "  5. Web → Code: WSGI = wsgi.py, Working dir = /home/moscowle, venv = moscowle_backend"
echo "  6. Setear environment variables"
echo "  7. Reload"
echo "  8. Subir frontend a public_html/moscowle.centrojuanpabloii.com/"
