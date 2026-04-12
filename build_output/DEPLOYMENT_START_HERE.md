# ✅ MOSCOWLE IA MVP - DEPLOYMENT PACKAGE READY

**Build Date:** April 11, 2026  
**Package:** `moscowle_production_v1.zip`  
**Size:** 1.6 MB (applicación + config)  
**Files:** 300+ (app, services, migrations, docs)

---

## 🎯 YOU HAVE EVERYTHING YOU NEED

Your production package is ready in:
```
/Users/apple/Documents/moscowle_ia_mvp/build_output/moscowle_production_v1.zip
```

**Contains:**
- ✅ Complete Flask application
- ✅ IA services (Ollama integration)
- ✅ Database migrations
- ✅ Security configurations
- ✅ Installation scripts
- ✅ Complete documentation

---

## 📋 QUICK ACTION STEPS

### STEP 1️⃣: COPY ZIP TO YOUR SERVER

#### Option A: Using SFTP (Recommended)

```bash
# From your macOS terminal:
scp -P 22 \
  /Users/apple/Documents/moscowle_ia_mvp/build_output/moscowle_production_v1.zip \
  username@yourdomain.com:/home/username/public_html/

# Or with full path to cPanel:
scp -P 2222 \
  /Users/apple/Documents/moscowle_ia_mvp/build_output/moscowle_production_v1.zip \
  username@yourdomain.com:/home/username/
```

#### Option B: Using cPanel File Manager

1. Log in to cPanel
2. Go to **File Manager**
3. Navigate to `public_html/`
4. Upload `moscowle_production_v1.zip`

---

### STEP 2️⃣: SSH INTO YOUR SERVER

```bash
# Connect
ssh username@yourdomain.com
# or if using non-standard SSH port:
ssh -p 2222 username@yourdomain.com

# Check you're in the right place
pwd
# Output should be: /home/username
ls -la
# Should show: public_html, mail, etc.
```

---

### STEP 3️⃣: EXTRACT ZIP IN cPanel

```bash
# Navigate to upload location
cd /home/username/public_html
# or if you uploaded to home:
cd /home/username

# Extract
unzip -q moscowle_production_v1.zip

# Verify extraction
ls -la moscowle_production_v1/
# Should show: app/ config.py SETUP.sh etc.

# Enter directory
cd moscowle_production_v1

# Clean up zip
rm ../moscowle_production_v1.zip
```

---

### STEP 4️⃣: RUN SETUP SCRIPT

```bash
# Inside the app directory
bash SETUP.sh

# This will:
# 1. Create Python virtual environment (venv/)
# 2. Install all dependencies from requirements.txt
# 3. Create logs/ and uploads/ directories
#
# ⏱️ Takes 5-10 minutes depending on connection
```

---

### STEP 5️⃣: CONFIGURE ENVIRONMENT

```bash
# Copy template to .env
cp .env.example .env

# Edit with your values
nano .env
# Or use vi if nano not available
vi .env
```

**CRITICAL VALUES TO UPDATE:**

```bash
# 1. Generate SECRET_KEY (random string, 32+ chars)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output to .env SECRET_KEY=xxxxx

# 2. Set Database Connection
# Get credentials from cPanel > MySQL Databases
SQLALCHEMY_DATABASE_URI=mysql+pymysql://username_dbuser:PASSWORD@localhost:3306/username_dbname

# 3. Set Email (Gmail or your SMTP)
MAIL_USERNAME=youremail@gmail.com
MAIL_PASSWORD=YOUR_APP_PASSWORD  # For Gmail: generate at myaccount.google.com/security
```

---

### STEP 6️⃣: CREATE PYTHON APP IN cPanel

1. **Log in to cPanel**
2. Search for **"Setup Python App"** (may be under "Software")
3. Click **"Create Application"** (or "NEW APPLICATION")

**Fill in:**

| Field | Value |
|-------|-------|
| **Python Version** | 3.9+ (or latest available) |
| **Application root** | `/home/username/public_html/moscowle_production_v1` |
| **Application URL** | `yourdomain.com` or `subdomain.yourdomain.com` |
| **Application startup file** | `passenger_wsgi.py` |
| **Application Entry Point** | `application` |
| **Passenger log file** | `/home/username/public_html/moscowle_production_v1/logs/passenger.log` |

**Click "Create" and wait 30-60 seconds for compilation**

---

### STEP 7️⃣: INITIALIZE DATABASE

```bash
# SSH into server (if not already connected)
ssh username@yourdomain.com
cd /home/username/public_html/moscowle_production_v1

# Activate virtual environment
source venv/bin/activate

# Set variables
export PYTHONPATH=/home/username/public_html/moscowle_production_v1:$PYTHONPATH
export FLASK_APP=run.py

# Apply database migrations
flask db upgrade

# If first time, run:
# flask db init
# flask db migrate -m "Initial migration"
# flask db upgrade
```

---

### STEP 8️⃣: VERIFY APPLICATION

```bash
# Check Passenger is running
ps aux | grep passenger
# Should show: passenger_watchdog, passenger_spawner

# Check for errors
tail -20 logs/passenger.log
# Should NOT show "500 Internal Server Error"

# Optional: Check MySQL connection
python -c "from app import db; db.create_all()" 2>&1 | grep -i error
```

---

### STEP 9️⃣: OPEN IN BROWSER

Go to: **`https://yourdomain.com`**

✅ **Expected:**
- Page loads without 500 error
- Redirects to HTTPS automatically
- Login form appears
- Browser shows padlock 🔒 (secure)

❌ **If error:**
```bash
# Check app logs
tail -50 logs/passenger.log

# Check .env
cat .env | grep SQLALCHEMY_DATABASE_URI

# Restart app
touch tmp/restart.txt

# Wait 30 seconds, refresh browser
```

---

## 🤖 OPTIONAL: SETUP IA (OLLAMA)

### If running AI on the same server:

```bash
# Download Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Download model (~4GB)
ollama pull llama3.1:8b

# Start service
ollama serve &

# Check it's running
curl http://127.0.0.1:11434/api/tags
```

### If running AI on remote server:

```bash
# Edit .env
nano .env

# Change:
OLLAMA_HOST=http://REMOTE_IP_ADDRESS:11434

# Verify connectivity
curl http://REMOTE_IP_ADDRESS:11434/api/tags
```

---

## 📊 POST-DEPLOYMENT CHECKLIST

```
Installation Verification:
☐ https://yourdomain.com opens without error
☐ Login page loads
☐ Can login with ADMIN account
☐ Dashboard displays data
☐ No 500 errors in logs/passenger.log

Features Test:
☐ Create new user (Paciente)
☐ Register payment
☐ Chat/IA responds
☐ View reports
☐ Export to Excel

Security Check:
☐ HTTPS working (padlock in browser)
☐ HTTP redirects to HTTPS
☐ .env file exists and has SECRET_KEY
☐ Database connected
☐ Logs don't show connection errors

Ollama (if enabled):
☐ ollama pull llama3.1:8b completed
☐ ollama serve running
☐ IA responds to chat messages
```

---

## 🆘 COMMON ISSUES & FIXES

### ❌ "502 Bad Gateway"

```bash
# Check if app crashed
tail logs/passenger.log

# Restart
touch tmp/restart.txt
sleep 30
# Refresh browser
```

### ❌ "Database connection refused"

```bash
# Verify credentials in cPanel > MySQL Databases
# Make sure .env has correct:
cat .env | grep SQLALCHEMY_DATABASE_URI

# If wrong, update:
nano .env  # Fix the line

# Restart app
touch tmp/restart.txt
```

### ❌ "Module not found: flask"

```bash
# Virtual environment not activated or corrupted
cd /home/username/public_html/moscowle_production_v1
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ "IA not responding"

```bash
# Check Ollama if local
ps aux | grep ollama

# If not running:
ollama serve &

# If remote, verify connectivity:
curl http://REMOTE_IP:11434/api/tags
```

---

## 📁 DIRECTORY STRUCTURE (After Setup)

```
moscowle_production_v1/
├── app/                      ✅ Flask application
│   ├── routes/              (50+ API endpoints)
│   ├── services/            (Business logic + IA)
│   ├── models.py            (Database schema)
│   ├── templates/           (HTML pages)
│   └── static/              (CSS, JS, images)
│
├── venv/                     ✅ Python environment (created by SETUP.sh)
│
├── migrations/              ✅ Database migrations
│
├── logs/                    ✅ Runtime logs
│   ├── app.log
│   └── passenger.log
│
├── uploads/                 ✅ User files (vouchers, etc)
│
├── tmp/                     ✅ Temporary files
│
├── config.py               ✅ Flask config
├── run.py                  ✅ Local development
├── passenger_wsgi.py       ✅ Production WSGI entry
├── requirements.txt        ✅ Dependencies
├── .env                    ✅ Environment (YOU CREATE THIS)
├── .htaccess              ✅ Apache config
│
├── DEPLOY_PRODUCTION_CPANEL.md   (Full deployment guide)
├── PRODUCTION_README.md           (This file)
└── SETUP.sh                      (Initialization script)
```

---

## 💡 MAINTENANCE TIPS

### Weekly:
```bash
# Check logs for errors
tail logs/app.log | grep ERROR

# Monitor disk usage
du -sh /home/username/public_html/moscowle_production_v1
```

### Monthly:
```bash
# Backup database
mysqldump -u db_user -p db_name > backup_$(date +%Y%m%d).sql

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Quarterly:
```bash
# Clean old logs
find logs -name "*.log" -mtime +90 -delete

# Verify backups exist
ls -lh backup_*.sql | tail -5
```

---

## 📞 TROUBLESHOOTING GUIDE

See **`DEPLOY_PRODUCTION_CPANEL.md`** for comprehensive troubleshooting (70% of questions answer there)

Quick links:
- Error 500? → Log diagnostics
- Python not found? → Check Python version
- MySQL error? → Verify credentials
- IA not working? → Check Ollama
- Still stuck? → Review `passenger.log`

---

## 🎉 SUCCESS!

If you can:
1. Access https://yourdomain.com
2. Login with admin account
3. See dashboard data
4. Create/update users
5. Register payments
6. Chat with IA

**Your application is production-ready! 🚀**

---

## 📚 FULL DOCUMENTATION

Located in the package:

| File | Purpose |
|------|---------|
| `DEPLOY_PRODUCTION_CPANEL.md` | **Step-by-step deployment** ⭐ |
| `V5_GUIA_COMPLETA.md` | IA features & examples |
| `PRODUCTION_README.md` | This file (overview) |
| `README.md` | General project info |
| `config.py` | Flask configuration |
| `app/models.py` | Database schema |
| `app/routes/` | API endpoints |
| `app/services/` | Business logic + IA |

---

**Version:** 1.0  
**Status:** ✅ Production Ready  
**Compatible:** cPanel v134.0.12+  
**Last Updated:** April 11, 2026

🚀 **Ready to deploy?** Start with **STEP 1** above!
