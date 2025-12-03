# Sistema Completo de Contacto y Mensajería - Documentación

## 📋 Resumen Ejecutivo

Se ha implementado un sistema completo de contacto y mensajería que conecta:
1. **Formulario de Contacto** (Principal_Page) → 2. **Backend API** (Flask) → 3. **Base de Datos** (MySQL) → 4. **Dashboard Admin** (MessagesModule)

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                  COMPONENTES DEL SISTEMA                      │
└─────────────────────────────────────────────────────────────┘

1. FORMULARIO DE CONTACTO (Frontend)
   └─ Principal_Page/src/components/ContactForm.tsx
   └─ POST /api/public/contact (sin autenticación)

2. BACKEND API (Flask)
   ├─ app/routes/contact_routes.py (7 endpoints)
   ├─ app/services/contact_service.py (lógica de negocio)
   ├─ app/models/contact.py (modelos de datos)
   └─ app/schemas/contact_schema.py (validación)

3. BASE DE DATOS (MySQL)
   ├─ contact_inquiry (consultas)
   └─ message (mensajes/respuestas)

4. DASHBOARD ADMINISTRATIVO (Frontend)
   └─ Dashboard/src/components/dashboard/MessagesModule.tsx
   └─ GET/POST endpoints con JWT auth
```

## 📁 Archivos Creados/Modificados

### Backend

#### 1. `backend/app/models/contact.py` (NEW - 124 líneas)
Define los modelos de datos SQLAlchemy:

```python
class ContactInquiry(db.Model):
    - inquiry_code: str (unique, formato INQ-XXXXXXXX)
    - first_name, last_name, email, phone: str
    - subject, message, service_interest: str
    - urgency: enum(low, medium, high)
    - status: enum(new, contacted, in_progress, resolved, closed)
    - timestamps: created_at, updated_at
    - messages: relación con Message

class Message(db.Model):
    - inquiry_id: FK a ContactInquiry
    - sender_type: enum(user, admin, anonymous, system)
    - sender_name, sender_email: str
    - message_text: str
    - message_type: enum(text, file, image, system)
    - is_read, is_internal: bool
    - timestamps: created_at, updated_at
```

#### 2. `backend/app/services/contact_service.py` (NEW - 225 líneas)
Lógica de negocio con dos clases de servicio:

```python
class ContactService:
    + generate_inquiry_code() → str
    + create_inquiry(data) → ContactInquiry
    + get_inquiry_by_id(id) → ContactInquiry
    + get_inquiry_by_code(code) → ContactInquiry
    + list_inquiries(status, search, per_page, page) → paginated list
    + update_inquiry_status(inquiry_id, status) → bool
    + get_stats() → {total, new_24h, pending}

class MessageService:
    + create_message(data) → Message
    + get_messages_by_inquiry(inquiry_id) → [Message]
    + mark_message_as_read(message_id) → bool
    + mark_inquiry_messages_as_read(inquiry_id) → int
    + get_unread_count() → int
```

#### 3. `backend/app/schemas/contact_schema.py` (NEW - 97 líneas)
Esquemas Marshmallow para validación:

- **ContactInquirySchema**: Validación de envíos (first_name, last_name, email, message, etc)
- **ContactInquiryUpdateSchema**: Validación de cambios de estado
- **MessageSchema**: Esquema de salida de mensajes
- **MessageCreateSchema**: Validación de creación de mensajes

#### 4. `backend/app/routes/contact_routes.py` (NEW - 235 líneas)
Endpoints HTTP:

**Públicos (sin autenticación):**
- `POST /api/public/contact` - Crear nueva consulta

**Administrativos (requieren JWT):**
- `GET /api/admin/inquiries` - Listar consultas (filtrado, búsqueda, paginación)
- `GET /api/admin/inquiries/<id>` - Detalle de consulta + mensajes
- `PUT /api/admin/inquiries/<id>` - Actualizar estado
- `POST /api/admin/messages` - Crear respuesta
- `GET /api/admin/messages/<inquiry_id>` - Obtener conversación
- `GET /api/admin/stats` - Estadísticas

#### 5. `backend/app/__init__.py` (UPDATED)
Cambios:
```python
# Agregar import de modelos
from .models import contact as _contact

# Agregar import de blueprint
from .routes.contact_routes import contact_bp

# Registrar blueprint
app.register_blueprint(contact_bp, url_prefix="/api")
```

### Base de Datos

#### `backend/migrations/add_contact_inquiry_tables.sql` (NEW)
Schema SQL con:
- Tabla `contact_inquiry` (20 columnas, 4 índices, búsqueda full-text)
- Tabla `message` (12 columnas, 4 índices)
- Triggers automáticos para timestamps
- Relación FK con cascada DELETE

### Frontend

#### `Dashboard/MessagesModule.tsx` (UPDATED - 600 líneas)
React component completo con:

**Funcionalidades:**
- Cargar y mostrar estadísticas en tiempo real
- Listar consultas con búsqueda y filtrado
- Ver detalles de consulta individual
- Mostrar conversación completa de mensajes
- Responder a consultas
- Cambiar estado de consulta
- Interfaz completamente responsiva y dark mode

**Estados manejados:**
- stats (total, nuevas 24h, pendientes, sin leer)
- inquiries (lista de consultas)
- selectedInquiry (consulta seleccionada)
- messages (mensajes de conversación)
- Loading states

**API Integration:**
- `GET /api/admin/stats` - Cargar estadísticas
- `GET /api/admin/inquiries` - Listar consultas
- `GET /api/admin/messages/<id>` - Cargar mensajes
- `PUT /api/admin/inquiries/<id>` - Cambiar estado
- `POST /api/admin/messages` - Enviar respuesta

## 🔄 Flujo de Datos

### 1. Envío de Contacto (Usuario)
```
Formulario ContactForm (Principal_Page)
    ↓
POST /api/public/contact
    ↓
ContactService.create_inquiry()
    ↓
contact_inquiry tabla (sin auth requerida)
    ↓
Status: "new" • inquiry_code: INQ-XXXXXXXX
```

### 2. Visualización en Dashboard (Admin)
```
MessagesModule carga al abrir
    ↓
GET /api/admin/stats
GET /api/admin/inquiries (filtrado)
    ↓
Mostrar lista con avatares, estado, urgencia
    ↓
Admin selecciona consulta
    ↓
GET /api/admin/messages/<inquiry_id>
    ↓
Mostrar conversación completa
```

### 3. Respuesta del Admin
```
Admin escribe respuesta en textarea
    ↓
POST /api/admin/messages
{
  inquiry_id: 1,
  message_text: "Respuesta aquí",
  sender_type: "admin",
  is_internal: false
}
    ↓
MessageService.create_message()
    ↓
ContactService.update_inquiry_status("contacted")
    ↓
message tabla + contact_inquiry.status actualizado
    ↓
GET /api/admin/messages/<inquiry_id> (reload)
    ↓
Mostrar nueva respuesta en conversación
```

## 🚀 Instalación y Ejecución

### 1. Aplicar Migración de Base de Datos

```bash
# Conectar a MySQL
mysql -u root -p

# Ejecutar script de migración
source backend/migrations/add_contact_inquiry_tables.sql;

# Verificar tablas creadas
SHOW TABLES LIKE 'contact%';
SHOW TABLES LIKE 'message';
```

### 2. Verificar Backend

```bash
# Activar venv
cd backend
source env/bin/activate

# Instalar/verificar dependencias
pip install -r requirements.txt

# Correr servidor
python wsgi.py  # Escucha en localhost:8000
```

### 3. Verificar Frontend

```bash
# Navegar a Dashboard
cd "Dashboard Administrativo Integral"

# Configurar variable de entorno (opcional, por defecto localhost:8000)
export VITE_BACKEND_URL=http://localhost:8000

# Correr desarrollo
npm run dev  # Puerto 5173
```

### 4. Verificar Principal_Page (Contacto)

```bash
cd Principal_Page
npm run dev
```

## 📊 Ejemplos de Uso

### Crear Consulta (Público)

```bash
curl -X POST http://localhost:8000/api/public/contact \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "phone": "+34123456789",
    "subject": "Consulta sobre servicios",
    "message": "Quisiera saber más sobre vuestros servicios de IA",
    "service_interest": "Machine Learning",
    "urgency": "high"
  }'
```

Respuesta:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "inquiry_code": "INQ-ABC12345",
    "status": "new",
    "created_at": "2024-12-03T15:30:00"
  }
}
```

### Listar Consultas (Admin)

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/admin/inquiries?status=new&search=juan&per_page=10&page=1
```

### Responder Consulta (Admin)

```bash
curl -X POST http://localhost:8000/api/admin/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "inquiry_id": 1,
    "message_text": "Gracias por tu consulta. Nos complace ayudarte.",
    "sender_type": "admin",
    "is_internal": false
  }'
```

## 🔐 Seguridad

### Autenticación
- Endpoint público de contacto: **sin autenticación** (cualquiera puede enviar)
- Endpoints admin: **JWT requerido** (solo administradores)
- Token obtenido en login: `localStorage.auth_token`

### Validación
- Esquemas Marshmallow en entrada
- Validación de email, longitudes
- SQL injection prevención (ORM SQLAlchemy)
- Enumerables tipados para status/urgency

### Privacidad
- Campo `is_internal` para notas privadas no mostradas al usuario
- Queries filtrables por status
- Mensajes no leídos rastreados

## 📈 Escalabilidad Futura

### Mejoras Posibles
1. **Notificaciones en tiempo real** - WebSocket para chat en vivo
2. **Attachments** - Subida de archivos con tipo MIME validation
3. **Plantillas** - Respuestas rápidas predefinidas
4. **Asignación de agentes** - Asignar consulta a admin específico
5. **SLA tracking** - Tiempos de respuesta prometidos
6. **Analytics** - Dashboard de métricas de soporte
7. **Email notifications** - Notificar al usuario de respuestas
8. **Chatbot AI** - Respuestas automáticas iniciales

## 🧪 Testing

### Backend Tests
```python
# test_contact_routes.py
def test_create_inquiry():
    response = client.post('/api/public/contact', json={...})
    assert response.status_code == 201
    
def test_admin_requires_jwt():
    response = client.get('/api/admin/inquiries')
    assert response.status_code == 401
```

### Frontend Tests
```typescript
// Mock API responses
describe('MessagesModule', () => {
  it('should load inquiries on mount', () => {
    // Mock apiCall
    // Render component
    // Assert inquiries loaded
  });
});
```

## 📚 Referencia Rápida de Endpoints

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/api/public/contact` | ❌ | Crear consulta |
| GET | `/api/admin/inquiries` | ✅ | Listar consultas |
| GET | `/api/admin/inquiries/<id>` | ✅ | Detalle + mensajes |
| PUT | `/api/admin/inquiries/<id>` | ✅ | Cambiar estado |
| POST | `/api/admin/messages` | ✅ | Crear mensaje |
| GET | `/api/admin/messages/<id>` | ✅ | Obtener conversación |
| GET | `/api/admin/stats` | ✅ | Estadísticas |

## 💡 Tips de Desarrollo

### Debug en Backend
```python
# app/routes/contact_routes.py
app.logger.debug(f"Creating inquiry: {data}")

# Activar debug mode
app.run(debug=True)
```

### Debug en Frontend
```typescript
// MessagesModule.tsx
console.log('API Response:', result);
console.error('API Error:', error);

// Ver requests en DevTools
Network tab → XHR/Fetch
```

### Base de Datos
```sql
-- Ver todas las consultas
SELECT * FROM contact_inquiry ORDER BY created_at DESC;

-- Ver mensajes de una consulta
SELECT * FROM message WHERE inquiry_id = 1 ORDER BY created_at ASC;

-- Estadísticas
SELECT 
  status, 
  COUNT(*) as count 
FROM contact_inquiry 
GROUP BY status;
```

## ✅ Checklist de Completitud

- [x] Modelos de datos creados
- [x] Servicios de lógica de negocio
- [x] Esquemas de validación
- [x] Endpoints API (7 total)
- [x] Integración en app/__init__.py
- [x] Frontend MessagesModule completo
- [x] Base de datos migration
- [x] Manejo de errores
- [x] Autenticación JWT
- [x] Interfaz responsiva
- [x] Dark mode support
- [x] Estadísticas en tiempo real

## 📞 Soporte

Para preguntas o issues:
1. Ver logs en backend: `app.logger`
2. Ver Network tab en DevTools
3. Verificar JWT token válido en localStorage
4. Comprobar tablas de BD creadas
5. Revisar permisos MySQL

---

**Última actualización**: Diciembre 2024
**Versión**: 1.0 (Producción lista)
**Mantenedor**: Sistema de Contacto Integral
