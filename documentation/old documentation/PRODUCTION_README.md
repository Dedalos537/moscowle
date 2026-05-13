# 🚀 MOSCOWLE IA MVP - PRODUCTION DEPLOYMENT (cPanel v134.0.12)

**Build Date:** 11 de Abril de 2026  
**Version:** 1.0 (Production Ready)  
**Compatibility:** cPanel v134.0.12 +

---

## 📦 DEPLOYMENT QUICK START

### ⚡ 5 MINUTOS - COMPILAR PAQUETE

```bash
# 1. Verificar integridad del proyecto
bash verify_project.sh

# 2. Compilar paquete de producción
bash build_production.sh

# La salida será:
# ✅ moscowle_production_v1.zip (creado en build_output/)
```

### ⚙️ INSTALACIÓN EN cPANEL (20-30 MINUTOS)

1. **Subir** `moscowle_production_v1.zip` a tu servidor cPanel (vía SFTP)
2. **Extraer** en el directorio deseado
3. **Ejecutar** `SETUP.sh` para configurar ambiente
4. **Configurar** `.env` con credenciales de BD y secretos
5. **Crear app** en cPanel => "Setup Python App"
6. **Verificar** acceso a https://tudominio.com

📖 **Ver:** `DEPLOY_PRODUCTION_CPANEL.md` para pasos completos

---

## 📋 CONTENIDO DEL PAQUETE

```
moscowle_production_v1/
├── app/                          # Aplicación Flask completa
│   ├── routes/                  # Endpoints (admin, api, auth, etc)
│   ├── services/                # Lógica de negocio y IA (v5 + OCR)
│   ├── models.py                # Base de datos (SQLAlchemy)
│   ├── templates/               # HTML (Bootstrap + Tailwind)
│   ├── static/                  # CSS, JS, assets
│   └── __init__.py              # Inicialización Flask
│
├── config.py                     # Configuración de Flask
├── run.py                        # Script de inicio local
├── passenger_wsgi.py            # Entrada WSGI para cPanel/Passenger
├── requirements.txt             # Dependencias Python (42 paquetes)
├── migrations/                  # DB migrations (Flask-Migrate)
│
├── .env.example                 # Template de variables de entorno
├── .htaccess                    # Redirects HTTP→HTTPS + Security headers
├── SETUP.sh                     # Script de instalación automática
│
├── DEPLOY_PRODUCTION_CPANEL.md # Guía de despliegue paso a paso
├── V5_GUIA_COMPLETA.md         # Documentación de IA v5
├── README.md                    # General project info
│
├── logs/                        # Runtime logs (creado en instalación)
├── uploads/                     # User uploads (crédo, vouchers, etc)
└── tmp/                         # Archivos temporales

SIZE: ~150 MB (incluye dependencias en reqs)
```

---

## 🎯 CARACTERISTICAS INCLUIDAS

### ✅ Backend Flask
- **Autenticación:** Login seguro con bcrypt, Flask-Login
- **Base de datos:** MySQL/MariaDB con ORM SQLAlchemy
- **API REST:** 50+ endpoints administrativos documentados
- **Seguridad:** CORS, CSRF protection, rate limiting, HSTS

### ✅ IA Avanzada (Ollama/Llama)
- **NLP Engine v5:** Detección de 20+ intents del admin
- **Semantic Search:** Extracción inteligente de parámetros
- **Clarification System:** Preguntas contextuales automáticas
- **Business Analytics:** Cálculos de revenue, breakeven, deudores

### ✅ Pagos y Finanzas
- **Registro de Pagos:** Manual o automático con voucher OCR
- **OCR Intelligent:** Extrae montos, nombres, referencias de imágenes
- **Gestión de Deudores:** Seguimiento y recordatorios automáticos
- **Gastos:** Categorización y reportes financieros

### ✅ Administración
- **Panel Completo:** Dashboard con estadísticas en tiempo real
- **Gestión de Usuarios:** Pacientes, Terapeutas, Admins
- **Sesiones:** Programación automática, conflictos, recordatorios
- **Reportes:** Exportar a Excel, análisis de tendencias

### ✅ Experiencia de Usuario
- **Responsive Design:** Funciona en desktop, tablet, móvil
- **Dark Mode:** Tema claro/oscuro configurable
- **Real-time Updates:** WebSockets para notificaciones
- **Accesibilidad:** ARIA labels, navegación por teclado

---

## 🔐 SEGURIDAD PRE-CONFIGURADA

```
✓ HTTPS enforced (HTTP→HTTPS redirect)
✓ Secure cookies (HTTPOnly, SameSite, Secure flags)
✓ HSTS header (31536000 segundos / 1 año)
✓ CSP headers (Content-Security-Policy)
✓ Rate limiting (60 req/min por IP)
✓ SQL Injection prevention (parameterized queries)
✓ XSS protection (template escaping)
✓ CSRF tokens (Flask-WTF)
✓ Password hashing (bcrypt, 12 rounds)
✓ JWT tokens opcional para API
```

---

## 🛠️ BEFORE YOU START

### Requirements on cPanel server:

- [ ] **Python 3.9+** (ask hosting provider)
- [ ] **MySQL 5.7+** or MariaDB 10.2+
- [ ] **RAM:** 4GB+ (8GB+ recomendado, 6GB mínimo)
- [ ] **Disk:** 5GB+ (2GB app + 3GB para modelos IA si local)
- [ ] **SSH Access** habilitado
- [ ] **mod_rewrite**, **mod_headers** enabled

### On your machine:

```bash
# Asegurar que tienes todo para compilar
bash verify_project.sh

# Compilar
bash build_production.sh
```

---

## 📝 QUICK REFERENCE - CRITICAL CONFIGURATION

### 1. Crear archivo `.env` en cPanel

```bash
# Copiar template
cp .env.example .env

# Editar y reemplazar:
nano .env
```

**VALORES CRÍTICOS A CAMBIAR:**

```env
# Generar clave aleatoria (32+ caracteres)
SECRET_KEY=xxxxx-super-larga-aqui-xxxxx

# Credenciales MySQL (ej: user123:pass456@localhost/db_name)
SQLALCHEMY_DATABASE_URI=mysql+pymysql://...

# Email SMTP (Gmail App Password)
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password-16chars

# IA Ollama (local o remoto)
OLLAMA_HOST=http://127.0.0.1:11434
```

### 2. Crear Python App en cPanel

**Panel > Setup Python App:**
- Python: 3.9+
- Root: `/home/user/public_html/app_moscowle`
- WSGI: `passenger_wsgi.py`
- Domain: `tudominio.com`

### 3. Inicializar Base de Datos

```bash
source venv/bin/activate
export PYTHONPATH=/home/user/public_html/app_moscowle:$PYTHONPATH
flask db upgrade
```

### 4. Verificar Ollama (opcional)

```bash
# Si está en el mismo servidor:
ollama pull llama3.1:8b
ollama serve

# Verificar
curl http://127.0.0.1:11434/api/tags
```

---

## 📞 TROUBLESHOOTING RÁPIDO

### Aplicación no inicia
```bash
# Ver logs
tail -50 logs/passenger.log

# Verificar .env
cat .env | grep SQLALCHEMY_DATABASE_URI

# Reiniciar
touch tmp/restart.txt
```

### DB Connection Error
```bash
# Verificar credenciales en cPanel > MySQL Databases
# Editar .env
nano .env  # Cambiar SQLALCHEMY_DATABASE_URI

# Aplicar cambios
touch tmp/restart.txt
```

### IA Ollama no responde
```bash
# Si está off-server: cambiar OLLAMA_HOST
# Si es local: iniciar servicio
ollama serve &

# Probar
python -c "import ollama; print(ollama.Client().list_running())"
```

---

## 📈 PERFORMANCE TIPS

1. **MySQL Indexing:** Verificar índices en tablas principales
2. **Cache:** Flask-Caching activado por defecto (1 hora TTL)
3. **Compresión:** GZIP activada en Apache
4. **Ollama:** Usar quantized models (7B mejor que 13B si RAM < 8GB)
5. **Logs:** Rotar logs semanalmente

---

## 📚 DOCUMENTATION

| Documento | Propósito |
|-----------|-----------|
| `DEPLOY_PRODUCTION_CPANEL.md` | **Guía paso a paso** (70% de tus preguntas) |
| `V5_GUIA_COMPLETA.md` | Características IA y ejemplos de uso |
| `app/routes/llama_routes.py` | Endpoints de IA (ver docstrings) |
| `app/services/enhanced_llm_service_v5.py` | Motor NLP, intents, parámetros |
| `app/services/ocr_service.py` | OCR de vouchers de pago |
| `app/services/admin_service.py` | Lógica de creación/actualización de usuarios |

---

## ✅ POST-DEPLOYMENT CHECKLIST

- [ ] Aplicación abre en HTTPS
- [ ] Login funciona
- [ ] Dashboard carga sin errores 500
- [ ] Crear usuario funcioná
- [ ] Registrar pago funciona
- [ ] IA responde a mensajes
- [ ] No hay errores en logs/passenger.log
- [ ] Ollama activo (si es local)
- [ ] Backups de BD configurados

---

## 🎉 YOU'RE DONE!

Una vez deployado:

1. **Compartir enlace:** `https://tudominio.com`
2. **Admin login:** usa `ADMIN_EMAIL` y contraseña temporal
3. **Cambiar pwd:** Ir a Profile > Cambiar contraseña
4. **Crear usuarios:** Panel > Admin Usuarios
5. **Monitorear:** Ver logs semanalmente

---

## 📞 NEED HELP?

1. **Check Logs:**
   ```bash
   tail -f logs/app.log
   tail -f logs/passenger.log
   ```

2. **Verify Setup:**
   ```bash
   python run.py  # Pruebas locales (si tienes acceso SSH)
   ```

3. **Review:**
   - `DEPLOY_PRODUCTION_CPANEL.md` (troubleshooting section)
   - `app/services/` (where business logic lives)
   - `app/models.py` (database schema)

---

**Version:** 1.0  
**Last Updated:** April 11, 2026  
**Maintained By:** Dev Team  
**Status:** ✅ Production Ready
