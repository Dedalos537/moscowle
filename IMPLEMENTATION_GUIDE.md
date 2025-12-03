# 🚀 Guía de Implementación - Sistema de Contacto y Mensajería

## ✅ Estado Actual: COMPLETO Y FUNCIONAL

Todos los componentes han sido implementados exitosamente. Este documento explica cómo poner en funcionamiento el sistema.

---

## 📊 Resumen de Archivos

### Backend (681 líneas de código nuevo)

| Archivo | Líneas | Estado | Descripción |
|---------|--------|--------|-------------|
| `backend/app/models/contact.py` | 124 | ✅ NEW | Modelos de datos |
| `backend/app/services/contact_service.py` | 225 | ✅ NEW | Lógica de negocio |
| `backend/app/schemas/contact_schema.py` | 97 | ✅ NEW | Validación |
| `backend/app/routes/contact_routes.py` | 235 | ✅ NEW | 7 Endpoints API |
| `backend/app/__init__.py` | - | ✅ UPDATED | +3 líneas (imports) |
| `backend/migrations/add_contact_inquiry_tables.sql` | 70 | ✅ NEW | Schema BD |

### Frontend (606 líneas, completamente funcional)

| Archivo | Líneas | Estado | Descripción |
|---------|--------|--------|-------------|
| `Dashboard/MessagesModule.tsx` | 606 | ✅ UPDATED | React component completo |

### Documentación

| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `backend/CONTACT_MESSAGING_COMPLETE.md` | ✅ NEW | Documentación técnica completa |
| `CONTACT_SYSTEM_STATUS.md` | ✅ NEW | Estado y verificación |

---

## 🔧 Paso 1: Configurar Base de Datos

### Opción A: Ejecutar migración SQL

```bash
# Abrir MySQL
mysql -u root -p

# Ejecutar el archivo de migración
source backend/migrations/add_contact_inquiry_tables.sql;

# Verificar que se crearon las tablas
SHOW TABLES LIKE 'contact%';
SHOW TABLES LIKE 'message';

# Verificar estructura
DESCRIBE contact_inquiry;
DESCRIBE message;
```

### Opción B: Usar Flask-Migrate (si está configurado)

```bash
cd backend
source env/bin/activate

# Crear migración
flask db migrate -m "Add contact and message tables"

# Aplicar migración
flask db upgrade
```

---

## ⚙️ Paso 2: Backend - Verificar Integración

### Verificar que los archivos están en el lugar correcto

```bash
# Desde raíz del proyecto
ls -la backend/app/models/contact.py
ls -la backend/app/services/contact_service.py
ls -la backend/app/schemas/contact_schema.py
ls -la backend/app/routes/contact_routes.py

# Verificar imports en __init__.py
grep "contact" backend/app/__init__.py
```

### Ejecutar Backend

```bash
cd backend
source env/bin/activate

# Si es necesario, instalar dependencias nuevas
pip install -r requirements.txt

# Iniciar servidor Flask
python wsgi.py

# Debe mostrar:
# Running on http://127.0.0.1:8000
# WARNING in app.runserver: This is a development server...
```

### Verificar que los endpoints están disponibles

En otra terminal:

```bash
# Probar endpoint público (sin auth)
curl -X POST http://localhost:8000/api/public/contact \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "message": "Este es un mensaje de prueba"
  }'

# Respuesta esperada (201 Created):
# {
#   "success": true,
#   "data": {
#     "id": 1,
#     "inquiry_code": "INQ-xxxxxxxxx",
#     "status": "new"
#   }
# }
```

---

## 🎨 Paso 3: Frontend - Verificar Integración

### Dashboard Administrativo

```bash
cd "Dashboard Administrativo Integral"

# Instalar dependencias si es necesario
npm install

# Configurar URL del backend (opcional, por defecto usa localhost:8000)
export VITE_BACKEND_URL=http://localhost:8000

# Iniciar desarrollo
npm run dev

# Debe mostrar:
# Local: http://localhost:5173
```

### Verificar que MessagesModule está actualizado

```bash
# Ver las nuevas líneas
head -50 "Dashboard Administrativo Integral/src/components/dashboard/MessagesModule.tsx"

# Debe mostrar imports de React 18, interfaces, y funciones de API
```

### Acceder a MessagesModule

1. Ir a `http://localhost:5173` en el navegador
2. Iniciar sesión (si es requerido)
3. Navegar a la sección de Mensajes/Consultas
4. Deberías ver:
   - Tarjetas de estadísticas (Total, Nuevas 24h, Pendientes, Sin Leer)
   - Lista de consultas a la izquierda
   - Panel de detalles a la derecha
   - Área de respuesta abajo

---

## 📱 Paso 4: Principal_Page - Formulario de Contacto

```bash
cd Principal_Page

npm install
npm run dev

# Ir a http://localhost:5174 (o puerto que asigne)
```

### Probar el flujo completo

1. **En Principal_Page**:
   - Encontrar y rellenar el formulario de contacto
   - Enviar el formulario
   - Deberías recibir confirmación

2. **Verificar en Base de Datos**:
   ```bash
   mysql -u root -p
   USE tu_database;
   SELECT * FROM contact_inquiry;
   ```
   - Debería mostrar el registro creado

3. **Verificar en Dashboard**:
   - Actualizar MessagesModule
   - La nueva consulta debería aparecer en la lista
   - Estado: "new", Urgencia: según lo ingresado

---

## 🔐 Paso 5: Autenticación

### Para endpoints administrativos

Los siguientes endpoints requieren JWT token en header `Authorization`:

```bash
# Obtener token en login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password"
  }'

# Respuesta: {"token": "eyJ0eXAiOiJKV1QiLCJhbGc..."}

# Usar token en requests
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  http://localhost:8000/api/admin/inquiries
```

### Token se guarda automáticamente en frontend

En `MessagesModule.tsx`:
```typescript
const getAuthToken = () => localStorage.getItem('auth_token');
```

---

## 🧪 Pruebas Completas del Sistema

### Test 1: Crear Consulta (Público)

```bash
curl -X POST http://localhost:8000/api/public/contact \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "phone": "+34123456789",
    "subject": "Consulta sobre servicios de IA",
    "message": "Quisiera saber más sobre vuestras soluciones de machine learning",
    "service_interest": "Machine Learning",
    "urgency": "high"
  }'

# Respuesta esperada:
# {
#   "success": true,
#   "data": {
#     "id": 1,
#     "inquiry_code": "INQ-ABC12345",
#     "status": "new",
#     "created_at": "2024-12-03T..."
#   }
# }
```

### Test 2: Listar Consultas (Admin)

```bash
# Asumir que tienes token JWT válido
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/admin/inquiries?status=new&per_page=10&page=1'

# Respuesta esperada:
# {
#   "success": true,
#   "data": {
#     "items": [
#       {
#         "id": 1,
#         "inquiry_code": "INQ-ABC12345",
#         "first_name": "Juan",
#         ...
#       }
#     ],
#     "total": 1,
#     "page": 1,
#     "pages": 1
#   }
# }
```

### Test 3: Ver Detalles + Mensajes (Admin)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/admin/inquiries/1'

# Respuesta esperada:
# {
#   "success": true,
#   "data": {
#     "inquiry": {...},
#     "messages": []  # Vacío si es primera vez
#   }
# }
```

### Test 4: Enviar Respuesta (Admin)

```bash
curl -X POST http://localhost:8000/api/admin/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inquiry_id": 1,
    "message_text": "Gracias por tu consulta. Nos complace informarte sobre nuestras soluciones...",
    "sender_type": "admin",
    "is_internal": false
  }'

# Respuesta esperada:
# {
#   "success": true,
#   "data": {
#     "id": 1,
#     "inquiry_id": 1,
#     "message_text": "...",
#     "sender_type": "admin",
#     ...
#   }
# }
```

### Test 5: Ver Estadísticas (Admin)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/admin/stats'

# Respuesta esperada:
# {
#   "success": true,
#   "data": {
#     "total_inquiries": 1,
#     "new_inquiries_24h": 1,
#     "pending_inquiries": 0,
#     "unread_messages": 0
#   }
# }
```

---

## 🐛 Solución de Problemas

### Problema: "Module not found" error

**Solución:**
```bash
# Verificar que los archivos existen
ls -la backend/app/models/contact.py
ls -la backend/app/services/contact_service.py

# Si no existen, volver a crear
# Si existen, verificar imports en app/__init__.py
grep "from .models import contact" backend/app/__init__.py
grep "from .routes.contact_routes import contact_bp" backend/app/__init__.py
```

### Problema: "401 Unauthorized" en endpoints admin

**Solución:**
```bash
# 1. Verificar que tienes token válido
echo $TOKEN

# 2. Verificar que el header está correcto
curl -H "Authorization: Bearer $TOKEN" ...

# 3. Si el token expiró, obtener uno nuevo
curl -X POST http://localhost:8000/api/login ...
```

### Problema: "CORS error" en frontend

**Solución:**
```bash
# 1. Verificar que backend está corriendo
curl http://localhost:8000/

# 2. Verificar que VITE_BACKEND_URL es correcto
echo $VITE_BACKEND_URL

# 3. Si sigue fallando, revisar app.config en Flask
# y CORS policy en backend/app/__init__.py
```

### Problema: Database connection error

**Solución:**
```bash
# 1. Verificar que MySQL está corriendo
mysql -u root -p -e "SELECT 1;"

# 2. Verificar credenciales en app/config.py
# 3. Verificar que la base de datos existe
# 4. Verificar que las tablas existen
mysql -u root -p -e "SHOW TABLES;" tu_database
```

### Problema: Migraciones no aplicadas

**Solución:**
```bash
# 1. Ejecutar script SQL directamente
mysql -u root -p < backend/migrations/add_contact_inquiry_tables.sql

# 2. Verificar tablas
mysql -u root -p -e "SHOW TABLES LIKE 'contact%';"

# 3. Si aún no funciona, revisar errores en MySQL
mysql -u root -p -e "SHOW ERRORS;"
```

---

## 📋 Checklist de Implementación

- [ ] Base de datos migrada (`contact_inquiry` y `message` tablas existen)
- [ ] Backend corriendo en `http://localhost:8000`
- [ ] Endpoint `/api/public/contact` responde 201 Created
- [ ] Endpoint `/api/admin/stats` responde con JWT
- [ ] MessagesModule.tsx actualizado (606 líneas)
- [ ] Dashboard corriendo en `http://localhost:5173`
- [ ] Principal_Page corriendo
- [ ] Formulario de contacto envía datos
- [ ] Consulta aparece en MessagesModule
- [ ] Admin puede responder
- [ ] Mensaje aparece en conversación
- [ ] Estadísticas se actualizan

---

## 🎯 Próximos Pasos Opcionales

1. **Email Notifications** - Notificar al usuario de respuestas
2. **Real-time Updates** - WebSocket para chat en vivo
3. **File Attachments** - Permitir subida de archivos
4. **Canned Responses** - Plantillas de respuesta rápida
5. **Agent Assignment** - Asignar consultas a agentes específicos
6. **SLA Tracking** - Monitorear tiempos de respuesta
7. **Analytics Dashboard** - Métricas de soporte

---

## 📞 Soporte y Debugging

### Logs útiles

```bash
# Backend logs
tail -f backend/logs/app.log

# Frontend DevTools
Open http://localhost:5173 → F12 → Console tab

# Database logs
tail -f /var/log/mysql/error.log
```

### Comandos útiles

```bash
# Limpiar base de datos
mysql -u root -p << EOF
DELETE FROM message;
DELETE FROM contact_inquiry;
ALTER TABLE contact_inquiry AUTO_INCREMENT = 1;
ALTER TABLE message AUTO_INCREMENT = 1;
EOF

# Ver todas las consultas
mysql -u root -p -e "SELECT * FROM contact_inquiry;"

# Ver todos los mensajes
mysql -u root -p -e "SELECT * FROM message;"

# Ver estadísticas
mysql -u root -p << EOF
SELECT 
  status, 
  COUNT(*) as count 
FROM contact_inquiry 
GROUP BY status;
EOF
```

---

## ✨ Características Implementadas

✅ Sistema bidireccional completo
✅ 7 endpoints API (1 público, 6 admin)
✅ Base de datos relacional con FK
✅ Autenticación JWT en endpoints admin
✅ Búsqueda y filtrado de consultas
✅ Paginación automática
✅ Estadísticas en tiempo real
✅ Validación de entrada (Marshmallow)
✅ Manejo completo de errores
✅ Interfaz responsiva + dark mode
✅ Full-text search en BD
✅ Timestamps automáticos

---

**¡Listo para comenzar!**

Para empezar, sigue estos pasos en orden:
1. Ejecutar migración de BD
2. Iniciar backend
3. Iniciar Dashboard
4. Iniciar Principal_Page
5. Llenar formulario y verificar que aparece en Dashboard
6. Responder desde Dashboard y verificar que funciona

Para preguntas, revisar `backend/CONTACT_MESSAGING_COMPLETE.md` o este documento.
