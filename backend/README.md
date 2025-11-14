# Backend Unificado - Centro de Terapias Juan Pablo II

Sistema backend modular y escalable para la gestión de consultas, mensajería y analytics.

## 🏗️ Estructura del Proyecto

```
backend/
├── app/
│   ├── core/           # Configuración, logging, seguridad
│   ├── models/         # Modelos de datos Pydantic
│   ├── services/       # Lógica de negocio
│   ├── api/           # Endpoints REST
│   ├── database/      # Capa de acceso a datos
│   └── analytics/     # Módulos de analytics
├── migrations/        # Scripts de base de datos
├── logs/             # Archivos de log
├── main.py           # Aplicación principal
├── requirements.txt  # Dependencias Python
├── .env             # Variables de entorno
└── setup.sh         # Script de configuración
```

## 🚀 Instalación Rápida

1. **Configurar el entorno:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Activar entorno virtual:**
   ```bash
   source venv/bin/activate
   ```

3. **Ejecutar el servidor:**
   ```bash
   python main.py
   ```

## 📡 Endpoints Principales

### Autenticación
- `POST /auth/login` - Iniciar sesión
- `GET /auth/me` - Información del usuario actual

### Mensajería
- `POST /messaging/inquiries` - Crear consulta (público)
- `GET /messaging/inquiries/by-code/{code}` - Obtener por código (público)
- `GET /messaging/inquiries/{id}` - Obtener por ID (autenticado)
- `POST /messaging/messages` - Crear mensaje (autenticado)

### Analytics
- `GET /analytics/stats` - Estadísticas básicas

## 🔧 Configuración

### Variables de Entorno (.env)

```env
# Base de datos
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=tu_password
DB_NAME=Moscowle_Complete

# JWT
SECRET_KEY=tu_clave_secreta_super_segura
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Servidor
HOST=127.0.0.1
PORT=8001
DEBUG=True

# CORS
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

### Base de Datos

La base de datos se inicializa automáticamente con el script `migrations/init_db.py`. Incluye:

- **Usuarios y perfiles** - Sistema de autenticación
- **Consultas de contacto** - Formularios web con códigos únicos
- **Conversaciones y mensajes** - Sistema de mensajería
- **NPS responses** - Encuestas de satisfacción
- **Heat map interactions** - Analytics de UX

## 🔐 Autenticación

El sistema usa JWT tokens para autenticación:

1. **Login** con username/password
2. **Token JWT** con expiración configurable
3. **Roles** de usuario (admin, therapist)
4. **Middleware** de autenticación en rutas protegidas

## 📊 Características

### ✅ Implementado
- Sistema de autenticación JWT
- Gestión de consultas de contacto
- Mensajería básica
- Configuración modular
- Logging estructurado
- Base de datos con migrations
- Documentación automática (FastAPI)

### 🔄 En Desarrollo
- Analytics completos (NPS, heat maps)
- Notificaciones en tiempo real
- Sistema de archivos adjuntos
- Dashboard administrativo
- API de estadísticas avanzadas

## 🧪 Testing

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio httpx

# Ejecutar tests
pytest
```

## 📝 Logging

Los logs se guardan en `logs/app.log` con rotación automática:

- **INFO**: Operaciones normales
- **ERROR**: Errores y excepciones
- **DEBUG**: Información detallada (solo en desarrollo)

## 🔄 Desarrollo

### Agregar Nuevo Endpoint

1. **Definir modelo** en `app/models/`
2. **Crear servicio** en `app/services/`
3. **Agregar ruta** en `app/api/`
4. **Registrar router** en `main.py`

### Estructura de Servicios

Los servicios siguen el patrón:
- **Métodos estáticos** para operaciones CRUD
- **Manejo de errores** con logging
- **Transacciones** de base de datos
- **Validación** de datos de entrada

## 🚦 Estado del Proyecto

- ✅ **Core Infrastructure** - Completado
- ✅ **Authentication** - Completado  
- ✅ **Basic Messaging** - Completado
- 🔄 **Advanced Analytics** - En desarrollo
- 🔄 **Real-time Features** - Planificado

## 👥 Contribución

Este es un backend unificado que reemplaza la arquitectura monolítica anterior, ofreciendo:

- **Modularidad** - Fácil mantenimiento y extensión
- **Escalabilidad** - Arquitectura preparada para crecimiento
- **Seguridad** - Autenticación robusta y validación
- **Observabilidad** - Logging y monitoreo integrados

---

**Centro de Terapias Juan Pablo II** - Backend Unificado v1.0.0