#!/bin/bash

set -e

echo "=================================================="
echo " MOSCOWLE IA MVP - PRODUCTION BUILD"
echo "=================================================="
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT=$(pwd)
BUILD_DIR="${PROJECT_ROOT}/build_output"
FLASK_PACKAGE="moscowle_flask_v1"
ANGULAR_PACKAGE="moscowle_angular_v1"

echo -e "${BLUE}[1/11] Creating build directories...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/${FLASK_PACKAGE}"
mkdir -p "$BUILD_DIR/${ANGULAR_PACKAGE}"

echo -e "${BLUE}[2/11] Copying Flask application files...${NC}"
cp -r "${PROJECT_ROOT}/app" "$BUILD_DIR/${FLASK_PACKAGE}/"
cp "${PROJECT_ROOT}/config.py" "$BUILD_DIR/${FLASK_PACKAGE}/"
cp "${PROJECT_ROOT}/passenger_wsgi.py" "$BUILD_DIR/${FLASK_PACKAGE}/"
cp "${PROJECT_ROOT}/requirements.txt" "$BUILD_DIR/${FLASK_PACKAGE}/"
cp "${PROJECT_ROOT}/create_admin.py" "$BUILD_DIR/${FLASK_PACKAGE}/" 2>/dev/null || true

echo -e "${BLUE}[3/11] Copying migrations...${NC}"
if [ -d "${PROJECT_ROOT}/migrations" ]; then
    cp -r "${PROJECT_ROOT}/migrations" "$BUILD_DIR/${FLASK_PACKAGE}/"
fi

echo -e "${BLUE}[4/11] Building Angular frontend...${NC}"
ANGULAR_DIST=""
if [ -d "${PROJECT_ROOT}/edysync" ]; then
    cd "${PROJECT_ROOT}/edysync"
    npm install --silent 2>/dev/null
    npx ng build --configuration production 2>&1 | tail -5
    cd "${PROJECT_ROOT}"
    cp -r "${PROJECT_ROOT}/edysync/dist/edysync/browser/"* "$BUILD_DIR/${ANGULAR_PACKAGE}/"
    echo " Angular build copied to ${ANGULAR_PACKAGE}/"
fi

echo -e "${BLUE}[5/11] Creating Angular .htaccess for subdomain...${NC}"
cat > "$BUILD_DIR/${ANGULAR_PACKAGE}/.htaccess" << 'HTANGULAR'
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTPS} !=on
  RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
  RewriteBase /
  RewriteRule ^index\.html$ - [L]
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule . /index.html [L]
</IfModule>
<IfModule mod_headers.c>
  Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
HTANGULAR

echo -e "${BLUE}[6/11] Copying documentation...${NC}"
cp "${PROJECT_ROOT}/README.md" "$BUILD_DIR/${FLASK_PACKAGE}/" 2>/dev/null || true

echo -e "${BLUE}[7/11] Creating .env.example...${NC}"
cat > "$BUILD_DIR/${FLASK_PACKAGE}/.env.example" << 'ENVEOF'
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=CAMBIAR_A_CLAVE_ALEATORIA_LARGA_32_CARACTERES
SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:contraseña@localhost:3306/nombre_bd
SQLALCHEMY_TRACK_MODIFICATIONS=False
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password
MAIL_DEFAULT_SENDER=noreply@centrojuanpabloii.com
OLLAMA_HOST=http://127.0.0.1:11434
LLM_MODEL=llama3.1:8b
LLM_ENABLED=True
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_TEMP=TempPass123!
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
ENABLE_VISION_ANALYSIS=True
ENABLE_PAYMENT_VOUCHER_OCR=True
ENABLE_PYWHATKIT=False
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
ENVEOF

echo -e "${BLUE}[8/11] Creating Flask initialization script...${NC}"
cat > "$BUILD_DIR/${FLASK_PACKAGE}/SETUP.sh" << 'SETUPEOF'
#!/bin/bash
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
echo "3. In cPanel > Setup Python App:"
echo "   - Application root: /moscowle"
echo "   - Entry point: passenger_wsgi.py"
echo "   - Environment: production"
echo "4. Upload angular/ content to moscowle.centrojuanpabloii.com"
echo ""
SETUPEOF
chmod +x "$BUILD_DIR/${FLASK_PACKAGE}/SETUP.sh"

echo -e "${BLUE}[9/11] Creating runtime directories...${NC}"
mkdir -p "$BUILD_DIR/${FLASK_PACKAGE}/logs"
mkdir -p "$BUILD_DIR/${FLASK_PACKAGE}/uploads"
mkdir -p "$BUILD_DIR/${FLASK_PACKAGE}/tmp"
chmod 777 "$BUILD_DIR/${FLASK_PACKAGE}/logs"
chmod 777 "$BUILD_DIR/${FLASK_PACKAGE}/uploads"
chmod 777 "$BUILD_DIR/${FLASK_PACKAGE}/tmp"

echo -e "${BLUE}[10/11] Creating .htaccess for Flask (centrojuanpabloii.com/moscowle)...${NC}"
cat > "$BUILD_DIR/${FLASK_PACKAGE}/.htaccess" << 'HTEOF'
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
HTEOF

echo -e "${BLUE}[11/11] Creating compressed packages...${NC}"
cd "$BUILD_DIR"
zip -r -q "${FLASK_PACKAGE}.zip" "$FLASK_PACKAGE/"
zip -r -q "${ANGULAR_PACKAGE}.zip" "$ANGULAR_PACKAGE/"
cd "$PROJECT_ROOT"

echo ""
echo -e "${GREEN}=================================================="
echo "BUILD SUCCESSFUL"
echo "==================================================${NC}"
echo ""
echo -e "${GREEN} Packages in:${NC} $BUILD_DIR"
echo ""
echo "--- FLASK BACKEND ---"
echo -e " ${BLUE}File:${NC} ${FLASK_PACKAGE}.zip"
echo -e " ${BLUE}Size:${NC} $(du -h "$BUILD_DIR/${FLASK_PACKAGE}.zip" | cut -f1)"
echo ""
echo " Deploy to centrojuanpabloii.com/moscowle:"
echo "  1. Upload ${FLASK_PACKAGE}.zip to your server"
echo "  2. Extract in the moscowle directory"
echo "  3. Copy .env.example to .env and configure"
echo "  4. Run: bash SETUP.sh"
echo "  5. In cPanel > Setup Python App:"
echo "     - Python version: 3.11+"
echo "     - Application root: moscowle"
echo "     - Entry point: passenger_wsgi.py"
echo "     - Environment: production"
echo ""
echo "--- ANGULAR FRONTEND ---"
echo -e " ${BLUE}File:${NC} ${ANGULAR_PACKAGE}.zip"
echo -e " ${BLUE}Size:${NC} $(du -h "$BUILD_DIR/${ANGULAR_PACKAGE}.zip" | cut -f1)"
echo ""
echo " Deploy to moscowle.centrojuanpabloii.com:"
echo "  1. In cPanel > Subdomains, ensure moscowle points to a directory"
echo "  2. Upload ${ANGULAR_PACKAGE}.zip and extract in that directory"
echo "  3. The .htaccess will handle SPA routing"
echo ""
