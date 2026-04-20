# 📦 MOSCOWLE IA MVP - DEPLOYMENT GUIDE FOR cPANEL (v134.0.12)

**Última actualización:** 11 de Abril de 2026

---

## 📋 TABLA DE CONTENIDOS

1. [Requisitos Previos](#requisitos-previos)
2. [Paso 1: Preparar el Servidor](#paso-1-preparar-el-servidor)
3. [Paso 2: Subir y Extraer el Paquete](#paso-2-subir-y-extraer-el-paquete)
4. [Paso 3: Configurar Python y Virtualenv](#paso-3-configurar-python-y-virtualenv)
5. [Paso 4: Instalar Dependencias](#paso-4-instalar-dependencias)
6. [Paso 5: Configurar Variables de Entorno](#paso-5-configurar-variables-de-entorno)
7. [Paso 6: Configurar Base de Datos](#paso-6-configurar-base-de-datos)
8. [Paso 7: Iniciar la Aplicación](#paso-7-iniciar-la-aplicación)
9. [Paso 8: Configurar IA (Ollama/Llama)](#paso-8-configurar-ia-ollama)
10. [Verificación y Testing](#verificación-y-testing)
11. [Troubleshooting](#troubleshooting)

---

## 🔧 REQUISITOS PREVIOS

### En cPanel:
- ✅ **Python 3.9+** disponible (solicitar al proveedor si es necesario)
- ✅ **Acceso SSH** habilitado
- ✅ **MySQL 5.7+** o MariaDB 10.2+
- ✅ **Espacio en disco:** Mínimo 5GB (2GB app + 3GB modelos IA)
- ✅ **Memoria RAM:** Mínimo 4GB (recomendado 8GB para Ollama)
- ✅ **mod_rewrite** y **mod_headers** habilitados en Apache

### En tu máquina local (dev):
- Archivo ZIP del deployment: `moscowle_production_v1.zip`
- Cliente SFTP o acceso SSH

---

## 🚀 PASO 1: PREPARAR EL SERVIDOR

### 1.1 Acceder por SSH a cPanel

```bash
ssh username@tudominio.com
# o si usas puerto diferente
ssh -p 2222 username@tudominio.com
```

### 1.2 Navegar al directorio home

```bash
cd ~
# Listar directorios disponibles
ls -la
```

Típicamente verás:
```
public_html/      # Documentos web públicos
public_ftp/       # FTP root
mail/             # Datos de correo
```

### 1.3 Crear carpeta para la aplicación

```bash
# Opción A: Dentro de public_html (recomendado para Flask)
cd public_html
mkdir -p app_moscowle
cd app_moscowle

# Opción B: En el home (alternativa)
cd ~
mkdir -p moscowle_app
cd moscowle_app
```

**Nota:** Guarda la ruta completa, ej: `/home/username/public_html/app_moscowle`

---

## 📥 PASO 2: SUBIR Y EXTRAER EL PAQUETE

### 2.1 Subir el ZIP por SFTP (desde tu máquina)

```bash
# Desde tu máquina local
scp -P 22 moscowle_production_v1.zip username@tudominio.com:/home/username/public_html/app_moscowle/

# O usando rsync (más eficiente)
rsync -avz --progress moscowle_production_v1.zip username@tudominio.com:/home/username/public_html/app_moscowle/
```

### 2.2 Extraer el ZIP en el servidor

```bash
cd /home/username/public_html/app_moscowle

# Extraer
unzip -q moscowle_production_v1.zip

# Verificar contenido
ls -la
# Debe mostrar: app/ config.py migrations/ requirements.txt passenger_wsgi.py etc.

# Limpiar
rm moscowle_production_v1.zip
```

---

## 🐍 PASO 3: CONFIGURAR PYTHON Y VIRTUALENV

### 3.1 Verificar versión de Python

```bash
python3 --version
# Esperado: Python 3.9.x o mayor

# Si no funciona, probar
python --version
/usr/bin/python3.11 --version  # o similar versión disponible
```

### 3.2 Crear Virtual Environment

```bash
cd /home/username/public_html/app_moscowle

# Crear venv
python3 -m venv venv

# Activar
source venv/bin/activate

# Verificar
which python
# Debe mostrar: /home/username/public_html/app_moscowle/venv/bin/python
```

---

## 📦 PASO 4: INSTALAR DEPENDENCIAS

### 4.1 Actualizar pip

```bash
# Asegurar que pip está actualizado
pip install --upgrade pip setuptools wheel
```

### 4.2 Instalar requirements

```bash
cd /home/username/public_html/app_moscowle

# Instalar desde archivo
pip install -r requirements.txt

# Esto puede tomar 5-10 minutos. Esperar pacientemente.
# Si hay errores, ver sección Troubleshooting.
```

### 4.3 Verificar instalación

```bash
python -c "import flask; print(flask.__version__)"
# Esperado: 2.3.x o mayor

python -c "import sqlalchemy; print(sqlalchemy.__version__)"
# Esperado: 1.4.x o 2.x
```

---

## 🔑 PASO 5: CONFIGURAR VARIABLES DE ENTORNO

### 5.1 Crear archivo .env

```bash
cd /home/username/public_html/app_moscowle

# Crear archivo
cat > .env << 'EOF'
# === APLICACIÓN ===
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=tu-clave-secreta-super-larga-aqui-minimo-32-caracteres-aleatorios
APP_PORT=5000

# === DATABASE ===
SQLALCHEMY_DATABASE_URI=mysql+pymysql://db_user:db_password@localhost:3306/db_name
SQLALCHEMY_TRACK_MODIFICATIONS=False

# === SEGURIDAD ===
USE_PROXYFIX=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=True
HSTS_SECONDS=31536000
HSTS_INCLUDE_SUBDOMAINS=True

# === EMAIL ===
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password-aqui
MAIL_DEFAULT_SENDER=noreply@tudominio.com

# === ADMIN ===
ADMIN_EMAIL=admin@centrojuanpabloii.com
ADMIN_PASSWORD_TEMP=TempPass123!

# === IA/OLLAMA ===
OLLAMA_HOST=http://127.0.0.1:11434
LLM_MODEL=llama3.1:8b
LLM_ENABLED=True

# === LOGGING ===
LOG_LEVEL=INFO
LOG_FILE=/home/username/public_html/app_moscowle/logs/app.log

# === CARACTERÍSTICAS ===
ENABLE_VISION_ANALYSIS=True
ENABLE_PAYMENT_VOUCHER_OCR=True
ENABLE_PYWHATKIT=False  # Solo si necesitas WhatsApp
EOF

# Ver contenido
cat .env
```

### 5.2 ACTUALIZAR VALORES CRÍTICOS

**⚠️ IMPORTANTE:** Reemplaza los siguientes valores:

1. **SECRET_KEY:** Generar clave aleatoria
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Copiar salida hacia .env

2. **Database Credentials:**
   ```bash
   # Ver en tu cPanel > MySQL Databases
   SQLALCHEMY_DATABASE_URI=mysql+pymysql://user123:pass456@localhost:3306/dbname_mw
   ```

3. **Email Credentials:**
   - Usar tu email de Gmail o SMTP
   - Para Gmail: Generar "App Password" en Seguridad de cuenta

4. **Ollama Host:** Dejar como está si está en el mismo servidor

### 5.3 Proteger el archivo .env

```bash
# Cambiar permisos (solo lectura para el usuario)
chmod 600 .env

# Verificar
ls -la .env
# Esperado: -rw------- (600)
```

---

## 🗄️ PASO 6: CONFIGURAR BASE DE DATOS

### 6.1 Acceder a cPanel > MySQL Databases

- Ir a **cPanel Dashboard**
- Buscar **MySQL Databases**
- Crear nueva base de datos (ej: `username_moscowle`)
- Crear usuario MySQL (ej: `username_mw_user`)
- Asignar todos los permisos
- **Guardar credenciales**

### 6.2 Crear tablas desde Migrations

```bash
cd /home/username/public_html/app_moscowle
source venv/bin/activate

# Aplicar migraciones
flask db upgrade

# O si es la primera vez
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

Si hay error de módulo "flask":

```bash
# Exportar PYTHONPATH
export PYTHONPATH=/home/username/public_html/app_moscowle:$PYTHONPATH
export FLASK_APP=run.py
flask db upgrade
```

### 6.3 Verificar Tablas en phpMyAdmin

- Acceder a cPanel > phpMyAdmin
- Seleccionar base de datos
- Buscar tablas: `user`, `appointment`, `payment`, `expense`, etc.
- ✅ Si existen, DB está lista

---

## 🎯 PASO 7: INICIAR LA APLICACIÓN

### 7.1 Configurar en cPanel > Setup Python App

1. **Acceder a cPanel**
2. Buscar **"Setup Python App"** (o "Application Manager" / "Python Releases")
3. Click **"Create Application"**

Llenar:
- **Python Version:** 3.9+ (seleccionar disponible)
- **Application root:** `/home/username/public_html/app_moscowle`
- **Application startup script:** `passenger_wsgi.py`
- **Application domain:** `tudominio.com` o `subdomain.tudominio.com`
- **Passenger log file:** `/home/username/public_html/app_moscowle/logs/passenger.log`

Guardar y esperar a que se compile (30-60 segundos).

### 7.2 Verificar estado en cPanel

```bash
# Desde SSH
ps aux | grep passenger
# Debe mostrar procesos de Passenger activos

# Revisar logs
tail -f /home/username/public_html/app_moscowle/logs/passenger.log
```

### 7.3 Probar acceso web

Abrir navegador:
```
https://tudominio.com
```

Esperado:
- ✅ Redirige a HTTPS
- ✅ Página de login carga
- ✅ Sin errores 500

---

## 🤖 PASO 8: CONFIGURAR IA (OLLAMA)

### 8.1 ¿En el mismo servidor o remoto?

**OPCIÓN A: En el mismo servidor cPanel** (recomendado si tienes espacio/RAM)

```bash
# Descargar Ollama (si no está instalado)
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo (∼ 4GB)
ollama pull llama3.1:8b

# Verificar
ollama list
# Debe mostrar: llama3.1:8b   4.7GB

# Servicio siempre activo
sudo systemctl enable ollama
sudo systemctl start ollama

# Verificar que escucha en :11434
curl http://127.0.0.1:11434/api/tags
```

**OPCIÓN B: Servidor Ollama remoto** (externamente alojado)

```bash
# Modificar .env
# OLLAMA_HOST=http://ip-del-servidor-remoto:11434

# Asegurar que es accesible
curl http://ip-del-servidor-remoto:11434/api/tags
```

### 8.2 Probar conexión desde la app

```bash
cd /home/username/public_html/app_moscowle
source venv/bin/activate

python -c "
import ollama
client = ollama.Client(host='http://127.0.0.1:11434')
resp = client.chat(model='llama3.1:8b', messages=[{'role': 'user', 'content': 'Hola'}])
print('✅ Ollama funciona:', resp['message']['content'][:50])
"
```

---

## ✅ VERIFICACIÓN Y TESTING

### 8.1 Verificar endpoints principales

```bash
# Login
curl -k https://tudominio.com/login

# API de texto
curl -X POST https://tudominio.com/llama/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message":"Hola"}'

# API de usuarios (requiere auth)
curl -k https://tudominio.com/api/admin/list-users \
  -H "Authorization: Bearer token..."
```

### 8.2 Revisar logs

```bash
# App logs
tail -f /home/username/public_html/app_moscowle/logs/app.log

# Passenger logs
tail -f /home/username/public_html/app_moscowle/logs/passenger.log

# System logs
tail -f /var/log/cPanel/error_log
```

### 8.3 Checklist final

- [ ] Aplicación accesible en HTTPS
- [ ] Login funciona
- [ ] Dashboard carga
- [ ] Usuarios pueden crearse
- [ ] Pagos pueden registrarse
- [ ] IA responde a consultas
- [ ] Logs no muestran errores críticos
- [ ] Base de datos actualizada

---

## 🔧 TROUBLESHOOTING

### Error: "ModuleNotFoundError: No module named 'flask'"

```bash
# Activar venv
source /home/username/public_html/app_moscowle/venv/bin/activate

# Reinstalar
pip install -r requirements.txt --force-reinstall
```

### Error: "SQLALCHEMY_DATABASE_URI not set"

```bash
# Verificar .env
cat /home/username/public_html/app_moscowle/.env | grep SQLALCHEMY

# Debe estar presente. Si no, agregar:
echo 'SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:pass@localhost/db' >> .env
```

### Error 500: Internal Server Error

```bash
# Revisar logs
tail -50 /home/username/public_html/app_moscowle/logs/passenger.log

# Reiniciar Passenger
touch /home/username/public_html/app_moscowle/tmp/restart.txt
```

### Error: "Ollama connection refused"

```bash
# Verificar que Ollama corre
ps aux | grep ollama
# Si no, iniciar:
ollama serve

# Probar conectividad
curl http://127.0.0.1:11434/api/tags

# Si error, revisar firewall
sudo ufw allow 11434
```

### Error: "Permission denied" en logs

```bash
# Cambiar permisos recursivamente
chmod -R 755 /home/username/public_html/app_moscowle
chmod -R 660 /home/username/public_html/app_moscowle/logs
```

### Mostrar versiones instaladas

```bash
source venv/bin/activate
pip list
python -c "import sys; print(sys.version)"
```

---

## 📞 CONTACTO Y SOPORTE

Si tienes problemas:

1. Revisar logs (ver sección anterior)
2. Verificar `.env` tiene todas las variables
3. Confirmar MySQL conecta correctamente
4. Probar manualmente en SSH:
   ```bash
   cd /home/username/public_html/app_moscowle
   source venv/bin/activate
   python run.py
   ```

---

## 🎉 ¡LISTO!

Si llegaste aquí sin errores, **¡tu aplicación está en producción!**

Acceder a: `https://tudominio.com`

**Tips para mantenimiento:**
- Revisar logs semanalmente
- Hacer backup de la base de datos
- Monitorear uso de CPU/RAM en cPanel
- Actualizar dependencias mensualmente: `pip install -r requirements.txt --upgrade`

---

**Versión:** 1.0  
**Última actualización:** 11 de Abril de 2026  
**Compatibilidad:** cPanel v134.0.12 +
