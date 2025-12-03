# 🎯 GUÍA RÁPIDA DE EJECUCIÓN

## ¿Qué pasará en cada paso?

### PASO 1: Migración de Base de Datos

```bash
mysql -u root -p moscowle < backend/migrations/add_contact_messages_tables.sql
```

**Qué sucede:**
- Se crean 2 tablas: `contact_inquiry` y `message`
- Se crean índices optimizados para búsquedas rápidas
- Se crean triggers para actualizar timestamps automáticamente
- Se establece relación de clave foránea entre tablas
- Status: ✅ BD lista para recibir datos

**Verificar:**
```sql
-- Ejecutar en MySQL
SHOW TABLES;  -- Debe mostrar contact_inquiry y message
DESCRIBE contact_inquiry;
DESCRIBE message;
```

---

### PASO 2: Backend (Flask)

```bash
cd backend
source venv/bin/activate  # macOS/Linux
# O: venv\Scripts\activate (Windows)
python app.py
```

**Qué sucede:**
1. Flask inicia en `http://localhost:8000`
2. Importa los modelos de `app/models/contact.py`
3. Registra el blueprint de `contact_routes.py`
4. Se accesibilita:
   - POST `/api/public/contact` (público)
   - GET/PUT `/api/admin/inquiries*` (JWT)
   - POST `/api/admin/messages` (JWT)
   - GET `/api/admin/stats` (JWT)
5. Status: ✅ Backend listo recibir consultas

**Verificar:**
```bash
# En otra terminal
curl http://localhost:8000/api/admin/stats -H "Authorization: Bearer TEST_TOKEN"
# Debería retornar JSON (puede fallar auth pero no 404)
```

---

### PASO 3: Principal Page (Formulario de Contacto)

```bash
cd Principal_Page
npm install  # Si es la primera vez
npm run dev
```

**Qué sucede:**
1. Vite compila React/TypeScript
2. Abre en `http://localhost:5173`
3. Se carga la página web pública
4. Contact.tsx está configurado con:
   - VITE_BACKEND_URL = `http://localhost:8000`
   - Formulario listo para enviar a `/api/public/contact`
5. Status: ✅ Frontend público listo

**Verificar:**
- Abre http://localhost:5173
- Scroll hasta "Contáctanos"
- Deberías ver el formulario con todos los campos

---

### PASO 4: Dashboard (Administración)

```bash
cd "Dashboard Administrativo Integral"
npm install  # Si es la primera vez
npm run dev
```

**Qué sucede:**
1. Vite compila React/TypeScript
2. Abre en `http://localhost:5174`
3. Se carga el panel administrativo
4. MessagesModule.tsx está configurado con:
   - VITE_BACKEND_URL = `http://localhost:8000`
   - Conecta a GET `/api/admin/inquiries` con JWT
5. Status: ✅ Dashboard admin listo (requiere login)

**Verificar:**
- Abre http://localhost:5174
- Si hay login, ingresa credenciales
- Deberías ver sección "Mensajería"
- Debe mostrar 4 estadísticas (aunque estén en 0)

---

## 🧪 PRUEBA COMPLETA (5 MINUTOS)

### Test 1: Enviar Consulta

```
1. Abre http://localhost:5173
2. Scroll a "Contáctanos"
3. Llena el formulario:
   - Nombre: "Javier"
   - Apellido: "García"
   - Email: "javier@example.com"
   - Teléfono: "+51 900 000 000"
   - Asunto: "Información sobre terapia"
   - Mensaje: "Hola, me gustaría información sobre los servicios disponibles"
   - Servicio: "Terapia de Lenguaje"
   - Prioridad: "Alta"
4. Click "Enviar Mensaje"
5. Debería ver: ✅ "¡Mensaje enviado exitosamente!"
```

**Verificación en terminal:**
```bash
# Ver en BD
mysql -u root -p
USE moscowle;
SELECT * FROM contact_inquiry;  -- Debe mostrar 1 fila
```

**Verificación en backend (logs):**
```
[INFO] POST /api/public/contact - 200 OK
[INFO] ContactInquiry creado: INQ-XXXXXXXX
```

---

### Test 2: Ver en Dashboard

```
1. Abre http://localhost:5174
2. Login si es necesario
3. Ve a sección "Mensajería"
4. Debería ver:
   - Estadísticas actualizadas (1 total, 1 nueva 24h)
   - "Javier García" en lista de consultas
   - Estado "Nuevo" en badge azul
   - Prioridad "Alta" en badge rojo
```

**Verificación en terminal:**
```bash
# Ver datos de API
curl http://localhost:8000/api/admin/inquiries \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
# Debe retornar JSON con la consulta
```

---

### Test 3: Responder como Admin

```
1. En Dashboard, click en "Javier García"
2. Debería ver:
   - Datos de contacto completos
   - Mensaje original en gris
   - Área "Responder" abajo
3. Escribe en "Escriba su respuesta...":
   "Hola Javier, gracias por tu consulta. Nos complace poder ayudarte..."
4. Click "Enviar Respuesta"
5. Debería ver:
   - ✅ Confirmación de envío
   - Mensaje aparece en conversación (fondo azul, "Admin" badge)
   - Estado automático cambia a "Contactado"
```

**Verificación en BD:**
```sql
SELECT * FROM message WHERE inquiry_id = 1;  -- Debe mostrar 2 mensajes
SELECT status FROM contact_inquiry WHERE id = 1;  -- Debe ser "contacted"
```

---

### Test 4: Cambiar Estado

```
1. En el detalle de la consulta
2. Click en dropdown de estado (azul)
3. Selecciona "En progreso"
4. Debería actualizar inmediatamente
5. La consulta ahora muestra status "En progreso" (naranja)
```

---

## 📊 DIAGRAMA DE FLUJO DE DATOS

```
┌─────────────────────────────────────────────────────────────────┐
│ USUARIO EN PRINCIPAL_PAGE (http://localhost:5173)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Formulario lleno → Validación frontend (Contact.tsx)       │
│  ↓                                                              │
│  2. POST http://localhost:8000/api/public/contact              │
│  ↓                                                              │
└─────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND (http://localhost:8000)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  3. contact_routes.py recibe POST                              │
│  ↓                                                              │
│  4. ContactSchema.load() valida datos                          │
│  ↓                                                              │
│  5. ContactService.create_inquiry() procesa                    │
│  ↓                                                              │
│  6. ContactInquiry guardado en BD                              │
│  ↓                                                              │
│  7. Retorna 200 OK + inquiry_code                              │
│  ↓                                                              │
└─────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────┐
│ BASE DE DATOS (MySQL moscowle)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  contact_inquiry: 1 fila agregada (estado: new)                │
│  └─ id: 1                                                      │
│  └─ inquiry_code: INQ-XXXXXXXX                                 │
│  └─ first_name: Javier                                         │
│  └─ status: new                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────┐
│ ADMIN EN DASHBOARD (http://localhost:5174)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  8. GET http://localhost:8000/api/admin/inquiries (con JWT)    │
│  ↓                                                              │
│  9. Backend retorna [ContactInquiry]                           │
│  ↓                                                              │
│  10. MessagesModule.tsx renderiza lista                        │
│  └─ "Javier García" aparece en tabla                           │
│                                                                 │
│  11. Admin click en "Javier García"                            │
│  ↓                                                              │
│  12. GET /api/admin/inquiries/1                                │
│  ↓                                                              │
│  13. Backend retorna inquiry + messages                        │
│  ↓                                                              │
│  14. MessagesModule muestra conversación                       │
│  └─ Mensaje original del usuario en gris                       │
│                                                                 │
│  15. Admin escribe respuesta + click "Enviar"                  │
│  ↓                                                              │
│  16. POST /api/admin/messages                                  │
│  ↓                                                              │
└─────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND PROCESA RESPUESTA                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  17. MessageService.create_message() procesa                   │
│  ↓                                                              │
│  18. Message guardado en BD                                    │
│  ↓                                                              │
│  19. ContactInquiry.status actualizado a "contacted"           │
│  ↓                                                              │
└─────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────┐
│ BD - ESTADO FINAL                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  contact_inquiry:                                              │
│  └─ status: contacted (actualizado)                            │
│                                                                 │
│  message: [2 registros]                                        │
│  ├─ sender_type: user, message_text: "Hola, me gustaría..."   │
│  └─ sender_type: admin, message_text: "Hola Javier..."        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────┐
│ DASHBOARD ACTUALIZA                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  20. GET /api/admin/inquiries/1 nuevamente                     │
│  ↓                                                              │
│  21. Conversación actualizada con ambos mensajes               │
│  └─ Usuario (gris) + Admin (azul)                              │
│  ↓                                                              │
│  22. Status muestra "Contactado"                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ❌ TROUBLESHOOTING

### Error: "Cannot POST /api/public/contact"
- **Causa:** Backend no está corriendo en puerto 8000
- **Solución:** `cd backend && python app.py`

### Error: "CORS error"
- **Causa:** CORS no configurado
- **Solución:** Asegurar que `from flask_cors import CORS; CORS(app)` en backend/__init__.py

### Error: "Cannot connect to database"
- **Causa:** MySQL no corriendo o BD no existe
- **Solución:** 
  ```bash
  CREATE DATABASE moscowle;
  mysql -u root -p moscowle < backend/migrations/add_contact_messages_tables.sql
  ```

### Error: "401 Unauthorized" en endpoints admin
- **Causa:** JWT inválido o expirado
- **Solución:** Login nuevamente en dashboard

### Contacto no aparece en dashboard
- **Causa:** Frontend no refresca automáticamente
- **Solución:** Click botón "Actualizar" en dashboard

---

## ✅ CHECKLIST FINAL

- [ ] MySQL corriendo y BD `moscowle` existe
- [ ] Migración ejecutada (tablas creadas)
- [ ] Backend corriendo en `http://localhost:8000`
- [ ] Principal_Page corriendo en `http://localhost:5173`
- [ ] Dashboard corriendo en `http://localhost:5174`
- [ ] Formulario de contacto visible y funcional
- [ ] Admin puede ver consultas en dashboard
- [ ] Admin puede responder consultas
- [ ] Conversación actualiza en tiempo real
- [ ] Estadísticas en dashboard se actualizan
- [ ] Todos los badges de colores muestren correctamente

---

## 🎬 ¡LISTO PARA EMPEZAR!

Todo el sistema está implementado y documentado. Solo necesitas seguir los 4 pasos de PASO 1 a PASO 4 para tener un sistema funcional de mensajería integrado.

**Tiempo estimado:** 10 minutos para tener todo corriendo.

---

**Fecha:** 3 de diciembre de 2025  
**Versión:** 1.0  
**Status:** ✅ LISTO PARA PRODUCCIÓN
