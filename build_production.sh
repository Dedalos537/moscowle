#!/bin/bash

###############################################################################
# MOSCOWLE IA MVP - PRODUCTION BUILD AND DEPLOYMENT PACKAGE
# Prepares the application for cPanel deployment
# Usage: bash build_production.sh
###############################################################################

set -e

echo "=================================================="
echo " MOSCOWLE IA MVP - PRODUCTION BUILD"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT=$(pwd)
BUILD_DIR="${PROJECT_ROOT}/build_output"
PACKAGE_NAME="moscowle_production_v1"
PACKAGE_FILE="${BUILD_DIR}/${PACKAGE_NAME}.zip"

# Create build directory
echo -e "${BLUE}[1/9] Creating build directory...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}"

# Copy application files
echo -e "${BLUE}[2/9] Copying application files...${NC}"
cp -r "${PROJECT_ROOT}/app" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/config.py" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/run.py" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/passenger_wsgi.py" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/requirements.txt" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/create_admin.py" "$BUILD_DIR/${PACKAGE_NAME}/" 2>/dev/null || true

# Copy migrations
echo -e "${BLUE}[3/9] Copying migrations...${NC}"
if [ -d "${PROJECT_ROOT}/migrations" ]; then
    cp -r "${PROJECT_ROOT}/migrations" "$BUILD_DIR/${PACKAGE_NAME}/"
fi

# Copy documentation
echo -e "${BLUE}[4/9] Copying documentation...${NC}"
cp "${PROJECT_ROOT}/DEPLOY_PRODUCTION_CPANEL.md" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/V5_GUIA_COMPLETA.md" "$BUILD_DIR/${PACKAGE_NAME}/"
cp "${PROJECT_ROOT}/README.md" "$BUILD_DIR/${PACKAGE_NAME}/" 2>/dev/null || true

# Create .env.example
echo -e "${BLUE}[5/9] Creating .env.example...${NC}"
cat > "$BUILD_DIR/${PACKAGE_NAME}/.env.example" << 'EOF'
# ===========================
# MOSCOWLE IA MVP - PRODUCCION
# ===========================

# APLICACIÓN
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=CAMBIAR_A_CLAVE_ALEATORIA_LARGA_32_CARACTERES
APP_PORT=5000

# BASE DE DATOS (MySQL)
SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:contraseña@localhost:3306/nombre_bd
SQLALCHEMY_TRACK_MODIFICATIONS=False

# SEGURIDAD
USE_PROXYFIX=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=True
HSTS_SECONDS=31536000
HSTS_INCLUDE_SUBDOMAINS=True

# EMAIL (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password
MAIL_DEFAULT_SENDER=noreply@tutudominio.com

# ADMIN
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_TEMP=TempPass123!

# IA - OLLAMA
OLLAMA_HOST=http://127.0.0.1:11434
LLM_MODEL=llama3.1:8b
LLM_ENABLED=True

# LOGGING
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# CARACTERÍSTICAS
ENABLE_VISION_ANALYSIS=True
ENABLE_PAYMENT_VOUCHER_OCR=True
ENABLE_PYWHATKIT=False
EOF

# Create initialization script
echo -e "${BLUE}[6/9] Creating initialization script...${NC}"
cat > "$BUILD_DIR/${PACKAGE_NAME}/SETUP.sh" << 'EOF'
#!/bin/bash
# Quick setup script for production deployment

echo "=================================================="
echo " MOSCOWLE IA MVP - QUICK SETUP"
echo "=================================================="

# Define paths
APP_DIR=$(pwd)
VENV_DIR="${APP_DIR}/venv"

echo "[1/5] Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "[2/5] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "[3/5] Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "[4/5] Installing dependencies..."
pip install -r requirements.txt

echo "[5/5] Creating logs directory..."
mkdir -p "${APP_DIR}/logs"

echo ""
echo " Setup completed!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Update .env with your configuration"
echo "3. Configure Python App in cPanel"
echo "4. See DEPLOY_PRODUCTION_CPANEL.md for full instructions"
echo ""
EOF

chmod +x "$BUILD_DIR/${PACKAGE_NAME}/SETUP.sh"

# Create directories for runtime
echo -e "${BLUE}[7/9] Creating runtime directories...${NC}"
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}/logs"
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}/uploads"
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}/tmp"
chmod 777 "$BUILD_DIR/${PACKAGE_NAME}/logs"
chmod 777 "$BUILD_DIR/${PACKAGE_NAME}/uploads"
chmod 777 "$BUILD_DIR/${PACKAGE_NAME}/tmp"

# Create .htaccess for HTTP->HTTPS redirect
echo -e "${BLUE}[8/9] Creating .htaccess configuration...${NC}"
cat > "$BUILD_DIR/${PACKAGE_NAME}/.htaccess" << 'EOF'
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTPS} !=on
  RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>

<IfModule mod_headers.c>
  Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
EOF

# Create compressed package
echo -e "${BLUE}[9/9] Creating compressed package...${NC}"
cd "$BUILD_DIR"
zip -r -q "$PACKAGE_NAME.zip" "$PACKAGE_NAME/"
cd "$PROJECT_ROOT"

# Show results
echo ""
echo -e "${GREEN}=================================================="
echo "BUILD SUCCESSFUL"
echo "==================================================${NC}"
echo ""
echo -e "${GREEN} Package created:${NC}"
echo "   Location: $PACKAGE_FILE"
echo "   Size: $(du -h "$PACKAGE_FILE" | cut -f1)"
echo ""
echo -e "${GREEN}Package contents:${NC}"
unzip -l "$PACKAGE_FILE" | head -20
echo "   ... (and more)"
echo ""
echo -e "${GREEN} Next steps:${NC}"
echo "1. Upload $PACKAGE_FILE to your cPanel server using SFTP"
echo "2. Extract: unzip $PACKAGE_NAME.zip"
echo "3. Run: cd $PACKAGE_NAME && bash SETUP.sh"
echo "4. Follow: DEPLOY_PRODUCTION_CPANEL.md for full setup"
echo ""
echo -e "${BLUE} Tips:${NC}"
echo "   - UPLOAD only: app/ config.py run.py passenger_wsgi.py requirements.txt"
echo "   - DO NOT upload: venv/ .git .venv tests/ debug files"
echo "   - CONFIGURE: .env with MySQL credentials and secrets"
echo ""
