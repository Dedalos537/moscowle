# Sistema de Mensajería y Contacto - Guía de Implementación Completa

## 📋 Estado General del Proyecto

**Fecha:** 3 de diciembre de 2025  
**Estado:** ✅ **90% COMPLETADO** - Sistema listo para desplegar

### Componentes Implementados

✅ Backend Models (ContactInquiry, Message)  
✅ Backend Services (ContactService, MessageService)  
✅ Backend Routes (7 endpoints públicos y admin)  
✅ Backend Schemas (Validación Marshmallow)  
✅ Frontend Contact Form (Principal_Page)  
✅ Frontend Messages Module (Dashboard)  
✅ API Integration (Frontend ↔ Backend)  
✅ Database Migration (SQL completo)  
⏳ Database Setup (requiere ejecutar migración)  

---

## 🗂️ Estructura de Archivos

### Backend
```
backend/
├── app/
│   ├── models/
│   │   └── contact.py (124 líneas)
│   ├── services/
│   │   └── contact_service.py (225 líneas)
│   ├── schemas/
│   │   └── contact_schema.py (97 líneas)
│   ├── routes/
│   │   └── contact_routes.py (235 líneas)
│   └── __init__.py (actualizado)
└── migrations/
    └── add_contact_messages_tables.sql
```

### Frontend
```
Principal_Page/
├── src/
│   └── components/
│       └── organisms/
│           └── Contact.tsx (actualizado - envío de formulario)

Dashboard Administrativo Integral/
├── src/
│   └── components/
│       └── dashboard/
│           └── MessagesModule.tsx (607 líneas - completo)
```

---

## 🚀 Pasos de Implementación

### 1️⃣ Configurar Variables de Entorno

**Frontend (.env.local):**
```env
VITE_BACKEND_URL=http://localhost:8000
```

**Backend (.env):**
```env
FLASK_ENV=development
DATABASE_URL=mysql+pymysql://user:password@localhost/moscowle
JWT_SECRET_KEY=your-secret-key
```

---

### 2️⃣ Ejecutar Migración de Base de Datos

```bash
# Opción 1: Usando MySQL CLI
mysql -u root -p moscowle < backend/migrations/add_contact_messages_tables.sql

# Opción 2: Usando Python (si está configurado)
cd backend
python -c "from db import db; db.create_all()"
```

**Tablas Creadas:**
- `contact_inquiry` - Almacena consultas de contacto
- `message` - Almacena mensajes/respuestas

---

### 3️⃣ Verificar Dependencias Backend

```bash
cd backend
pip install -r requirements.txt
```

**Paquetes requeridos:**
- Flask 2.2+
- SQLAlchemy 3.0+
- Marshmallow 3.14+
- Flask-JWT-Extended 4.4+
- PyMySQL 1.0+

---

### 4️⃣ Iniciar Backend

```bash
cd backend
python app.py
# O con Gunicorn:
# gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

Backend escuchará en: `http://localhost:8000`

---

### 5️⃣ Iniciar Frontend

```bash
# Principal_Page (formulario de contacto)
cd Principal_Page
npm install
npm run dev

# Dashboard (mensajería)
cd "Dashboard Administrativo Integral"
npm install
npm run dev
```

---

## 📡 Endpoints API

### Públicos (Sin autenticación)

#### POST `/api/public/contact`
**Crear una nueva consulta de contacto**

```json
{
  "first_name": "Juan",
  "last_name": "Pérez",
  "email": "juan@email.com",
  "phone": "+51 900 000 000",
  "subject": "Información sobre terapia",
  "message": "Quisiera información sobre...",
  "service_interest": "Terapia de Lenguaje",
  "urgency": "high"
}
```

**Respuesta (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "inquiry_code": "INQ-A1B2C3D4",
    "first_name": "Juan",
    "email": "juan@email.com",
    "status": "new"
  }
}
```

---

### Admin (Requiere JWT)

#### GET `/api/admin/inquiries?status=pending&search=juan&per_page=10&page=1`
**Listar consultas con filtros**

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "inquiry_code": "INQ-A1B2C3D4",
        "first_name": "Juan",
        "status": "new",
        "urgency": "high",
        "created_at": "2025-12-03T10:30:00"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 10
  }
}
```

#### GET `/api/admin/inquiries/<id>`
**Obtener detalles de una consulta + mensajes**

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "inquiry": {
      "id": 1,
      "inquiry_code": "INQ-A1B2C3D4",
      "first_name": "Juan",
      "status": "new"
    },
    "messages": [
      {
        "id": 1,
        "sender_type": "user",
        "sender_name": "Juan Pérez",
        "message_text": "Mi mensaje...",
        "created_at": "2025-12-03T10:30:00"
      }
    ]
  }
}
```

#### PUT `/api/admin/inquiries/<id>`
**Actualizar estado de consulta**

```json
{
  "status": "in_progress"
}
```

#### POST `/api/admin/messages`
**Crear respuesta/mensaje**

```json
{
  "inquiry_id": 1,
  "message_text": "Hola Juan, gracias por tu consulta...",
  "sender_type": "admin",
  "is_internal": false
}
```

#### GET `/api/admin/messages/<inquiry_id>`
**Obtener conversación completa**

#### GET `/api/admin/stats`
**Obtener estadísticas del dashboard**

```json
{
  "success": true,
  "data": {
    "total_inquiries": 42,
    "new_inquiries_24h": 3,
    "pending_inquiries": 8,
    "unread_messages": 5
  }
}
```

---

## 🔐 Autenticación

Los endpoints admin requieren JWT en el header:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/admin/inquiries
```

El token se obtiene del login y se guarda en `localStorage` con clave `auth_token`.

---

## 🧪 Pruebas del Flujo Completo

### Test 1: Enviar Contacto desde Principal_Page

```bash
# 1. Ir a http://localhost:5173 (Principal_Page)
# 2. Scroll a sección "Contáctanos"
# 3. Llenar formulario:
#    - Nombre: Javier
#    - Apellido: García
#    - Email: javier@example.com
#    - Mensaje: Quiero más información...
#    - Prioridad: Alta
# 4. Click "Enviar Mensaje"
# 5. Ver confirmación "¡Mensaje enviado exitosamente!"
```

### Test 2: Ver en Dashboard

```bash
# 1. Ir a http://localhost:5174 (Dashboard)
# 2. Login con credenciales admin
# 3. Ir a sección "Mensajería"
# 4. Ver nueva consulta en lista
# 5. Click en la consulta para ver detalles
```

### Test 3: Responder en Dashboard

```bash
# 1. Seleccionar una consulta
# 2. Escribir respuesta en área de texto
# 3. Click "Enviar Respuesta"
# 4. Ver mensaje aparece en conversación
# 5. Cambiar estado a "en_progress" o "resuelto"
```

---

## 📊 Modelos de Datos

### ContactInquiry
```python
{
  id: int,                    # PK
  inquiry_code: str,          # Único: INQ-XXXXXXXX
  first_name: str,            # Requerido
  last_name: str,             # Requerido
  email: str,                 # Requerido
  phone: str,                 # Opcional
  subject: str,               # Opcional
  message: str,               # Requerido, mín 10 caracteres
  service_interest: str,      # Opcional
  urgency: enum,              # low | medium | high
  status: enum,               # new | contacted | in_progress | resolved | closed
  created_at: datetime,       # Auto-timestamp
  updated_at: datetime        # Auto-timestamp
}
```

### Message
```python
{
  id: int,                    # PK
  inquiry_id: int,            # FK → ContactInquiry
  sender_type: enum,          # user | anonymous | system | admin
  sender_name: str,           # Opcional
  sender_email: str,          # Opcional
  message_text: str,          # Requerido
  message_type: enum,         # text | file | image | system
  is_read: bool,              # Default: false
  is_internal: bool,          # Default: false
  created_at: datetime,       # Auto-timestamp
  updated_at: datetime        # Auto-timestamp
}
```

---

## 🎨 UI Components Utilizados

### Frontend (React + TypeScript)
- `Card`, `CardContent`, `CardHeader` - Contenedores
- `Button` - Botones de acción
- `Input`, `Textarea` - Inputs de formulario
- `Select`, `SelectContent`, `SelectItem` - Dropdowns
- `Badge` - Etiquetas de estado/urgencia
- `ScrollArea` - Área scrollable para conversaciones
- `Avatar`, `AvatarFallback` - Avatares de usuarios
- `Alert`, `AlertDescription` - Alertas de estado

### Backend (Flask + SQLAlchemy)
- `Blueprint` - Rutas modulares
- `SQLAlchemy ORM` - Modelos y relaciones
- `Marshmallow` - Esquemas de validación
- `Flask-JWT-Extended` - Autenticación
- Decoradores: `@jwt_required()`, `@contact_bp.route()`

---

## 🔧 Troubleshooting

### Error 404 en Contact.tsx
**Problema:** `POST /api/public/contact` retorna 404  
**Solución:** Verificar que backend está corriendo en `http://localhost:8000` y que la ruta está registrada en `app/__init__.py`

### CORS Error
**Problema:** `Cross-Origin Request Blocked`  
**Solución:** Agregar en `app/__init__.py`:
```python
from flask_cors import CORS
CORS(app)
```

### Token JWT Expirado
**Problema:** `401 Unauthorized` en endpoints admin  
**Solución:** Re-login en Dashboard o extender tiempo de expiración en config

### Base de datos no existe
**Problema:** `Error: Database moscowle doesn't exist`  
**Solución:** 
```sql
CREATE DATABASE moscowle CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## 📈 Próximos Pasos (Opcionales)

1. **Notificaciones en Tiempo Real**
   - Usar WebSocket con Socket.IO
   - Notificar a admin cuando llega nuevo mensaje

2. **Email Notifications**
   - Enviar email cuando se recibe consulta
   - Resumen diario de consultas pendientes

3. **File Attachments**
   - Permitir adjuntos en respuestas
   - Almacenamiento en S3 o servidor local

4. **Advanced Analytics**
   - Gráficas de consultas por servicio
   - Tiempo promedio de respuesta
   - Satisfacción del cliente

5. **Integration with CRM**
   - Sincronizar con sistema CRM existente
   - Historial completo de cliente

---

## 📞 Contacto y Soporte

Para cambios o mejoras:
- Backend: `backend/app/routes/contact_routes.py`
- Frontend: `Dashboard Administrativo Integral/src/components/dashboard/MessagesModule.tsx`
- Database: `backend/migrations/add_contact_messages_tables.sql`

---

**Última actualización:** 3 de diciembre de 2025  
**Versión:** 1.0 (Completo)
