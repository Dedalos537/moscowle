# Docker Setup - Moscowle Sistema de Mensajería

**Fecha:** 3 de diciembre de 2025  
**Versión:** 2.0 (Con sistema de mensajería completo)

## 📋 Contenedores Incluidos

| Servicio | Puerto | URL | Descripción |
|----------|--------|-----|-------------|
| MySQL Database | 3306 | - | Base de datos principal (moscowle) |
| Backend (Flask) | 8000 (desde 5000) | `http://localhost:8000` | API REST + Mensajería |
| Frontend (Principal Page) | 3002 | `http://localhost:3002` | Página de contacto |
| Dashboard Admin | 3001 | `http://localhost:3001` | Panel de administración |

---

## 🚀 Inicio Rápido

### Opción 1: Docker Compose (RECOMENDADO)

```bash
# 1. Construir imágenes
docker-compose build

# 2. Iniciar todos los servicios
docker-compose up -d

# 3. Esperar a que se ejecuten las migraciones (~30 segundos)
docker-compose logs -f backend

# 4. Acceder a los servicios
# Frontend: http://localhost:3002
# Dashboard: http://localhost:3001 (requiere login)
# Backend API: http://localhost:8000/api/admin/stats
```

---

## 📝 Contenedor Backend

El backend está configurado para:
1. ✅ Esperar a que MySQL esté listo
2. ✅ Ejecutar automáticamente las migraciones de mensajería
3. ✅ Iniciar Flask en puerto 5000 (mapeado a 8000 en host)

### Volúmenes y Migraciones

```yaml
backend:
  volumes:
    - ./backend:/app  # Código en tiempo real
  command: 
    - Ejecuta migraciones
    - Inicia Flask
```

---

## 🗄️ Base de Datos

### Credenciales

- **Host:** moscowle_db (o 127.0.0.1:3306 desde host)
- **Usuario:** root
- **Password:** Rucula_530
- **Database:** moscowle

### Conectar desde host

```bash
mysql -h 127.0.0.1 -u root -pRucula_530 -P 3306 moscowle
```

### Tablas del Sistema de Mensajería

```sql
-- Ver tablas
SHOW TABLES;

-- Ver estructura
DESC contact_inquiry;
DESC message;

-- Ver datos
SELECT * FROM contact_inquiry;
SELECT * FROM message;
```

---

## 🧪 Pruebas API

### Enviar Contacto (Público, sin auth)

```bash
curl -X POST http://localhost:8000/api/public/contact \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "phone": "+51 900000000",
    "subject": "Información",
    "message": "Quiero más información sobre servicios",
    "service_interest": "Terapia de Lenguaje",
    "urgency": "high"
  }'
```

### Ver Estadísticas

```bash
curl http://localhost:8000/api/admin/stats
```

---

## 🔧 Comandos Docker

### Estado de servicios

```bash
docker-compose ps
```

### Ver logs en tiempo real

```bash
# Todos
docker-compose logs -f

# Solo backend
docker-compose logs -f backend

# Solo BD
docker-compose logs -f db
```

### Detener

```bash
# Mantener volúmenes
docker-compose down

# Eliminar todo (CUIDADO: borra BD)
docker-compose down -v
```

### Reconstruir

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Ejecutar comandos en contenedores

```bash
# Bash en backend
docker-compose exec backend bash

# Python en backend
docker-compose exec backend python

# MySQL en BD
docker-compose exec db mysql -u root -pRucula_530 moscowle
```

---

## 🔄 Desarrollo Local con Docker

```bash
# 1. Iniciar stack
docker-compose up -d

# 2. Ver que está corriendo
docker-compose ps

# 3. Ver logs de backend
docker-compose logs -f backend

# 4. Hacer cambios en código (se recargan en tiempo real)
# Los volúmenes permiten editar y ver cambios sin reconstruir

# 5. Si cambias requirements.txt, reconstruir:
docker-compose build backend
docker-compose up -d

# 6. Cuando termines
docker-compose down
```

---

## 📊 Flujo Completo en Docker

```
1. Usuario en localhost:3002
   ↓
2. Llena formulario de contacto
   ↓
3. POST http://localhost:8000/api/public/contact
   ↓
4. Backend (Flask en Docker) procesa
   ↓
5. Guarda en MySQL (Docker)
   ↓
6. Admin logea en localhost:3001
   ↓
7. Ve consulta en Dashboard
   ↓
8. Responde vía POST /api/admin/messages
   ↓
9. Actualiza en conversación
```

---

## 🚨 Troubleshooting

### Puerto ya en uso

```bash
# Cambiar puerto en docker-compose.yml
ports:
  - "3307:3306"  # Cambiar primer número
```

### Backend no inicia

```bash
docker-compose logs backend
# Ver error específico
```

### BD no se inicializa

```bash
docker-compose down -v
docker-compose up db
# Esperar health check
```

### Migraciones no ejecutan

```bash
docker-compose exec backend \
  mysql -h moscowle_db -u root -pRucula_530 moscowle < \
  /app/migrations/add_contact_messages_tables.sql
```

### Frontend no conecta

```bash
# Verificar VITE_BACKEND_URL en frontend
# Debe ser: http://localhost:8000
```

---

## 📚 Archivos Relacionados

- `docker-compose.yml` - Configuración principal
- `docker-compose.override.yml` - Overrides para desarrollo
- `backend/Dockerfile` - Imagen backend
- `QUICK_START_GUIDE.md` - Guía sin Docker
- `SISTEMA_MENSAJERIA_COMPLETO.md` - API endpoints

---

**Generado:** 3 de diciembre de 2025  
**Status:** ✅ ACTUALIZADO CON SISTEMA DE MENSAJERÍA
