#!/bin/bash

################################################################################
# SCRIPT DE DEPLOYMENT PARA MOSCOWLE IA MVP
# ============================================================================== #
# Propósito: Preparar proyecto para pase a producción en cPanel/Hostinger
# 
# Funciones:
# 1. Validar ambiente
# 2. Limpiar directorios (node_modules, .git, cache, uploads locales)
# 3. Excluir archivos sensibles (.env, .vscode, etc.)
# 4. Minificar/Compilar assets si aplica
# 5. Generar ZIP optimizado
# 6. Crear instrucciones de despliegue
#
# Uso:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
#
# Salida:
#   deploy_moscowle_v2.zip (archivo comprimido optimizado)
#   DEPLOYMENT_GUIDE.md (instrucciones de despliegue)
#
# Consideraciones:
# - No incluir .env, bases de datos físicas, uploads > 1MB
# - Usar rutas relativas para máxima compatibilidad cPanel
# - Verificar permisos (755 para scripts, 644 para archivos)
################################################################################

set -e  # Exit on error

# Colors para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build_deploy"
DEPLOY_ZIP="deploy_moscowle_v2.zip"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ZIP="deploy_moscowle_v2_backup_${TIMESTAMP}.zip"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          MOSCOWLE IA - DEPLOYMENT SCRIPT FOR cPanel          ║"
echo "║                    Versión 2.0 - 2026-03-19                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# PASO 1: VALIDACIONES INICIALES
# =============================================================================

echo -e "${BLUE}[1/6] Validando ambiente...${NC}"

if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${RED}❌ Directorio de proyecto no encontrado${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt no encontrado${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/run.py" ]; then
    echo -e "${RED}❌ run.py no encontrado${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ambiente validado${NC}"

# =============================================================================
# PASO 2: CREAR DIRECTORIO TEMPORAL DE BUILD
# =============================================================================

echo -e "${BLUE}[2/6] Preparando directorios...${NC}"

# Limpiar build anterior
if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
    echo -e "${YELLOW}⚠️  Directorio de build anterior removido${NC}"
fi

mkdir -p "$BUILD_DIR"
echo -e "${GREEN}✅ Directorio de build creado: $BUILD_DIR${NC}"

# =============================================================================
# PASO 3: COPIAR ARCHIVOS Y EXCLUIR DIRECTORIOS PESADOS
# =============================================================================

echo -e "${BLUE}[3/6] Copiando archivos del proyecto...${NC}"

# Copiar todo EXCEPTO directorios pesados/sensibles
rsync -a \
    --exclude='.git' \
    --exclude='.gitignore' \
    --exclude='.vscode' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.DS_Store' \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='env' \
    --exclude='.idea' \
    --exclude='*.log' \
    --exclude='uploads/*' \
    --exclude='instance/uploads/*' \
    --exclude='instance/*.db' \
    --exclude='instance/*.db.backup*' \
    --exclude='build_deploy' \
    --exclude='dist' \
    --exclude='*.egg-info' \
    --exclude='deploy_moscowle*.zip' \
    "$PROJECT_ROOT/" "$BUILD_DIR/moscowle_ia_mvp/"

echo -e "${GREEN}✅ Archivos copiados exitosamente${NC}"

# =============================================================================
# PASO 4: CREAR DIRECTORIOS NECESARIOS EN DEPLOY
# =============================================================================

echo -e "${BLUE}[4/6] Creando estructura de directorios para producción...${NC}"

mkdir -p "$BUILD_DIR/moscowle_ia_mvp/instance/uploads"
mkdir -p "$BUILD_DIR/moscowle_ia_mvp/instance/uploads/receipts"
mkdir -p "$BUILD_DIR/moscowle_ia_mvp/instance/uploads/yape_receipts"
mkdir -p "$BUILD_DIR/moscowle_ia_mvp/logs"

# Crear .env.example si no existe
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cat > "$BUILD_DIR/moscowle_ia_mvp/.env.production" << 'ENVEOF'
# ===================================
# PRODUCCIÓN - CONFIGURACIÓN CRÍTICA
# ===================================

# Flask
FLASK_ENV=production
FLASK_APP=run.py
SECRET_KEY=CAMBIAR_EN_PRODUCCION_GENERAR_SECRETO_FUERTE
DEBUG=False

# Base de Datos (MySQL/MariaDB en cPanel)
# Conexión formato: mysql+pymysql://usuario:contraseña@hostname/database
DATABASE_URL=mysql+pymysql://usuario:contraseña@localhost/moscowle_db

# Configuración de Puerto
PORT=5001

# Email (SMTP)
MAIL_SERVER=mail.tudominio.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=noreply@tudominio.com
MAIL_PASSWORD=contraseña_segura

# Twilio (Opcional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Google Drive (Opcional)
GOOGLE_DRIVE_KEY=

# Security
CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com
ENVEOF
    echo -e "${YELLOW}⚠️  .env.production creado - EDITAR ANTES DE DESPLEGAR${NC}"
fi

# Copiar .env.example si existe
if [ -f "$PROJECT_ROOT/.env.example" ]; then
    cp "$PROJECT_ROOT/.env.example" "$BUILD_DIR/moscowle_ia_mvp/.env.example"
fi

echo -e "${GREEN}✅ Estructura de directorios creada${NC}"

# =============================================================================
# PASO 5: GENERAR INSTRUCCIONES DE DESPLIEGUE
# =============================================================================

echo -e "${BLUE}[5/6] Generando guía de despliegue...${NC}"

cat > "$BUILD_DIR/DEPLOYMENT_GUIDE.md" << 'MDEOF'
# 📋 GUÍA DE DESPLIEGUE - MOSCOWLE IA MVP v2.0

## Requisitos Previos
- No acceso a SSH/Terminal requerido - se usa FTP/cPanel File Manager
- cPanel con Python 3.9+ instalado
- MySQL/MariaDB disponible
- Mínimo 500 MB de espacio disponible

## PASO 1: Descargar y Extraer ZIP

1. **Descarga** el archivo `deploy_moscowle_v2.zip`
2. **En cPanel → File Manager:**
   ```
   Ir a: public_html/ o directorio de tu aplicación
   Click derecho → Extract (o usar Upload → Extract)
   Seleccionar: deploy_moscowle_v2.zip
   ```
   Resultado: Se crea carpeta `moscowle_ia_mvp/`

## PASO 2: Configurar .env

1. **Editar archivo** `.env.production` (renombrarlo a `.env`):
   ```
   Ir a: moscowle_ia_mvp/
   Click en .env.production → Edit
   ```

2. **Reemplazar valores CRÍTICOS:**
   ```
   DATABASE_URL = mysql+pymysql://cpanel_user:PASSWORD@localhost/cpanel_database
   SECRET_KEY   = (Generar con: python3 -c "import secrets; print(secrets.token_hex(32))")
   MAIL_SERVER  = Solicitar a hosting provider
   ```

3. **Guardar cambios**

## PASO 3: Crear Base de Datos

1. **En cPanel → MySQL Databases:**
   - Click: "Create New Database"
   - Database Name: `moscowle_db` (o tu preferencia)
   - Click: "Create Database"

2. **En cPanel → MySQL Users:**
   - Create New User: `moscowle_user`
   - Password: (generar fuerte)
   - Click: "Create User"

3. **Asignar Privilegios:**
   - Select: `moscowle_user` y `moscowle_db`
   - Grant ALL PRIVILEGES
   - Click: "Make Changes"

4. **Copiar datos de conexión a .env:**
   ```
   DATABASE_URL=mysql+pymysql://moscowle_user:PASSWORD@localhost/moscowle_db
   ```

## PASO 4: Configurar Python & Virtual Environment

1. **En cPanel → Setup Python App:**
   - Click: "Setup Python App"
   - Python Version: Seleccionar 3.9 o superior
   - App Mode: "Web application"
   - App URL: (tu dominio o subdomain)
   - Application Root: `/home/username/public_html/moscowle_ia_mvp`
   - Application Startup File: `run.py`
   - Application Entry Point: `app`
   - Interpreter: (seleccionar Python 3.9+)

2. **Copia el ENVPATH que genera** (lo necesitas en el siguiente paso)

## PASO 5: Modificar Archivo de Entrada

1. **En File Manager → public_html/moscowle_ia_mvp:**
   - Buscar archivo: `passenger_wsgi.py`
   - Click derecho → Edit

2. **Editar para usar la app:**
   ```python
   import sys
   sys.path.insert(0, '/home/username/public_html/moscowle_ia_mvp')
   
   from app import create_app
   app = create_app()
   
   # Passenger/Gunicorn entry point
   application = app
   ```

3. **Guardar**

## PASO 6: Instalar Dependencias Python

1. **En cPanel → Terminal (o SSH si disponible):**
   ```bash
   cd /home/username/public_html/moscowle_ia_mvp
   source /opt/passenger/py39/bin/activate  # O la versión que uses
   pip install -r requirements.txt
   ```

   Si NO tienes acceso a Terminal:
   - **Usar Python App creado en Paso 4**
   - cPanel ejecutará automáticamente el setup

## PASO 7: Configurar Permisos

1. **En File Manager:**
   ```
   moscowle_ia_mvp/ → Click derecho → Change Permissions (Chmod)
   Permisos:
   - Directorios: 755 (rwxr-xr-x)
   - Archivos: 644 (rw-r--r--)
   - instance/ → 755
   - instance/uploads/ → 755
   - logs/ → 755
   ```

## PASO 8: Inicializar Base de Datos

1. **Ejecutar migrations:**
   ```
   source /opt/passenger/py39/bin/activate
   cd /home/username/public_html/moscowle_ia_mvp
   python migrations/add_yape_transaction.py
   ```

2. **Crear usuario admin (si primera vez):**
   ```python
   python3 << 'EOF'
   from app import create_app
   from app.models import User
   from app.extensions import db
   
   app = create_app()
   with app.app_context():
       admin = User(
           username='admin',
           email='admin@moscowle.com',
           role='admin',
           is_active=True
       )
       admin.set_password('CAMBIAR_CONTRASEÑA')
       db.session.add(admin)
       db.session.commit()
       print("✅ Admin creado")
   EOF
   ```

## PASO 9: Probar Aplicación

1. **Acceder a:** `https://tudominio.com/`
2. **Esperar 30 segundos** al primer acceso (Python app se inicia)
3. **Login con usuario admin** creado en Paso 8
4. **Verificar:**
   - [ ] Dashboard carga
   - [ ] Puedes navegar a /admin/deudores
   - [ ] Puedes ver /admin/yape (módulo Yape)

## PASO 10: Configurar SSL/HTTPS

1. **cPanel → AutoSSL:**
   - Click: "Enable AutoSSL for this account"
   - Se instala certificado automáticamente

2. **Forzar HTTPS:**
   - File Manager: public_html/ → .htaccess
   - Añadir:
   ```apache
   <IfModule mod_rewrite.c>
       RewriteEngine On
       RewriteCond %{HTTPS} off
       RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
   </IfModule>
   ```

## PASO 11: Configurar Cronjobs (Tareas Automáticas)

Si usas la app para:
- Enviar recordatorios de pago
- Actualizar pagos automáticos
- Reportes semanales

**En cPanel → Cron Jobs:**

```bash
# Ejecutar cada hora
0 * * * * /opt/passenger/py39/bin/python /home/username/public_html/moscowle_ia_mvp/app/tasks/payment_reminders.py

# Ejecutar cada lunes a las 9 AM
0 9 * * 1 /opt/passenger/py39/bin/python /home/username/public_html/moscowle_ia_mvp/app/tasks/weekly_reports.py
```

## SOLUCIÓN DE PROBLEMAS

### Error: "ModuleNotFoundError: No module named 'openpyxl'"
```bash
source /opt/passenger/py39/bin/activate
pip install openpyxl
```

### Error: "SQLAlchemy connection refused"
- Verificar DATABASE_URL en .env
- Asegurarse MySQL user tiene privilegios en DB
- Testear con: `python3 -c "import MySQLdb; MySQLdb.connect(...)"`

### Error: "Static files not loading"
- Verificar archivo `app/routes/uploads.py` línea de STATIC_FOLDER
- Asegurarse carpeta `static/` tiene permisos 755

### Port 5000 ya está en uso
- cPanel asigna puertos automáticamente
- NO intentes cambiar puerto en run.py
- El servidor usa Passenger automaticamente

## BACKUP Y MANTENIMIENTO

### Backup Automático (Importante)
```bash
# Crear backup semanal (añadir a Cron)
0 2 * * 0 cd /home/username && zip -r backups/moscowle_$(date +%Y%m%d).zip public_html/moscowle_ia_mvp/instance/
```

### Logs
Ubicación: `instance/logs/`
- Revisar regularmente para errores
- Limpiar mensualmente si > 100 MB

### Actualizar Código
1. Descargar nuevo `deploy_moscowle_v2.zip`
2. Extraer en directorio temporal
3. Copiar SOLO carpetas `app/` y `static/`
4. NO reemplazar `.env` ni `instance/`
5. Reiniciar app en cPanel

## SOPORTE
- Documentación: `/documentation/INSTRUCCIONES_DESPLIEGUE_CPANEL.md`
- Email: support@moscowle.com

---
**Última actualización:** 2026-03-19
**Versión:** 2.0
MDEOF

echo -e "${GREEN}✅ Guía de despliegue generada: $BUILD_DIR/DEPLOYMENT_GUIDE.md${NC}"

# =============================================================================
# PASO 6: CREAR ZIP OPTIMIZADO
# =============================================================================

echo -e "${BLUE}[6/6] Generando archivo ZIP optimizado...${NC}"

cd "$BUILD_DIR"

# Crear ZIP excluyendo archivos innecesarios
zip -r \
    -x "*/.*" \
    "*.pyc" \
    "*__pycache__*" \
    "*/.pytest_cache/*" \
    "*.egg-info" \
    "${DEPLOY_ZIP}" \
    moscowle_ia_mvp/ \
    DEPLOYMENT_GUIDE.md \
    > /dev/null 2>&1

# Mover ZIP al directorio raíz del proyecto
mv "${BUILD_DIR}/${DEPLOY_ZIP}" "${PROJECT_ROOT}/${DEPLOY_ZIP}"
ZIP_SIZE=$(du -h "${PROJECT_ROOT}/${DEPLOY_ZIP}" | cut -f1)

echo -e "${GREEN}✅ ZIP creado: ${DEPLOY_ZIP} (${ZIP_SIZE})${NC}"

# =============================================================================
# RESUMEN Y INSTRUCCIONES FINALES
# =============================================================================

cat > "${PROJECT_ROOT}/DEPLOYMENT_SUMMARY.txt" << 'SUMMEOF'
================================================================================
                    DEPLOYMNET SUMMARY - MOSCOWLE IA MVP v2.0
================================================================================

📦 ARCHIVOS GENERADOS:
   ✅ deploy_moscowle_v2.zip        (Aplicación lista para cPanel)
   ✅ DEPLOYMENT_GUIDE.md           (Guía paso a paso)
   ✅ DEPLOYMENT_SUMMARY.txt        (Este archivo)

📋 CONTENIDO DEL ZIP:
   - app/                           (Modelos, rutas, servicios)
   - migrations/                    (Scripts de migración BD)
   - static/                        (CSS, JS, imágenes)
   - templates/                     (HTML Jinja2)
   - requirements.txt               (Dependencias Python)
   - run.py                          (Punto de entrada)
   - passenger_wsgi.py              (Configuración cPanel)
   - config.py                      (Configuración general)
   - .env.production                (Template de variables de entorno)

🚀 PASOS RÁPIDOS PARA DESPLEGAR:

1. Descargar deploy_moscowle_v2.zip
2. En cPanel → Extract en public_html/
3. Editar .env.production (renombrar a .env)
4. cPanel → Setup Python App
5. Crear Base de Datos MySQL
6. Ejecutar: pip install -r requirements.txt
7. Ejecutar migrations: python migrations/add_yape_transaction.py
8. Acceder a: https://tudominio.com

⚠️  CONFIGURACIONES CRÍTICAS:
   - DATABASE_URL: Cambiar host/usuario/contraseña
   - SECRET_KEY: Generar con: python3 -c "import secrets; print(secrets.token_hex(32))"
   - MAIL_SERVER: Solicitar a hosting provider
   - CORS_ORIGINS: Añadir tu dominio

📊 CHECKLIST PRE-DEPLOYMENT:
   [ ] .env configurado con credenciales reales
   [ ] Base de Datos MySQL creada
   [ ] Python 3.9+ disponible en cPanel
   [ ] Permisos de directorios: 755 dirs, 644 files
   [ ] SSL/HTTPS configurado
   [ ] Backup de base de datos local realizado

🔒 CONSIDERACIONES DE SEGURIDAD:
   - Archivo .env: NO incluido en ZIP (crear manualmente)
   - Directorios excluidos: .git, .vscode, venv, node_modules
   - Uploads: Inicialmente vacío (se crea en runtime)
   - Logs: Directorio vacío pero con estructura

📈 ESCALABILIDAD:
   - App usa WSGI (compatible con cPanel Passenger)
   - Yape Service: Streams para archivos grandes
   - DB: Preparada para MySQL con índices para performance
   - Static files: Servidos vía cPanel automáticamente

💬 SOPORTE:
   - Leer: documentation/INSTRUCCIONES_DESPLIEGUE_CPANEL.md
   - Foro: https://moscowle.com/soporte
   - Email: admin@moscowle.com

================================================================================
Generated: 2026-03-19
Version: 2.0
================================================================================
SUMMEOF

echo -e "${GREEN}✅ Resumen de deployment creado${NC}"

# =============================================================================
# LIMPIEZA Y FINALIZACIÓN
# =============================================================================

echo -e "${BLUE}[✓] Finalizando...${NC}"

# Borrar directorio temporal
rm -rf "$BUILD_DIR"

# Mostrar resumen final
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ DEPLOYMENT PREPARADO EXITOSAMENTE            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📦 ARCHIVOS LISTOS EN:${NC} ${PROJECT_ROOT}"
echo "   • ${DEPLOY_ZIP}"
echo "   • DEPLOYMENT_SUMMARY.txt"
echo ""
echo -e "${YELLOW}🚀 PRÓXIMO PASO:${NC}"
echo "   1. Descargra: ${DEPLOY_ZIP}"
echo "   2. Sube en cPanel File Manager"
echo "   3. Extrae en public_html/"
echo "   4. Lee: DEPLOYMENT_GUIDE.md"
echo ""
echo -e "${BLUE}📖 DOCUMENTACIÓN:${NC}"
echo "   • Full Guide: documentation/INSTRUCCIONES_DESPLIEGUE_CPANEL.md"
echo "   • Technical: documentation/CPANEL_DEPLOY.md"
echo ""
echo -e "${GREEN}✅ Listo para cPanel/Hostinger${NC}"
echo ""
