# 🚀 Guía Completa: K-Means Clustering en Docker

**Fecha:** 3 de diciembre de 2025  
**Status:** ✅ Listo para producción

---

## 📋 Tabla de Contenidos

1. [Inicio Rápido](#inicio-rápido)
2. [Arquitectura Docker](#arquitectura-docker)
3. [Verificación Completa](#verificación-completa)
4. [Comandos Útiles](#comandos-útiles)
5. [Solución de Problemas](#solución-de-problemas)

---

## 🚀 Inicio Rápido

### Opción 1: Todo Automático (Recomendado)

```bash
# 1. Ir al directorio raíz del proyecto
cd /Users/apple/Documents/moscowle

# 2. Ejecutar script de inicio y verificación
bash run_and_verify.sh
```

Esto:
- ✅ Levanta todos los servicios (DB, Backend, Frontend, Dashboard)
- ✅ Ejecuta verificaciones automáticas
- ✅ Prueba los endpoints de la API

### Opción 2: Solo Backend + Verificación

```bash
# 1. Ir al directorio backend
cd backend

# 2. Ejecutar script de backend
bash start_backend_only.sh

# 3. En otra terminal, ejecutar verificación
cd ..
python3 verify_k_means_complete.py
```

### Opción 3: Manual Paso a Paso

```bash
# 1. Limpiar ambiente anterior
docker-compose down

# 2. Construir imagen backend
docker-compose build backend

# 3. Iniciar servicios
docker-compose up -d

# 4. Verificar
python3 verify_k_means_complete.py
```

---

## 🏗️ Arquitectura Docker

### Estructura de Servicios

```
┌─────────────────────────────────────────────────┐
│           Docker Compose Setup                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐       ┌──────────────┐      │
│  │   Backend    │       │   Frontend   │      │
│  │   (Puerto    │       │   (Puerto    │      │
│  │    8000)     │       │    3001)     │      │
│  └──────┬───────┘       └──────────────┘      │
│         │                                      │
│  ┌──────▼───────────────────────────────┐     │
│  │      MySQL Database                  │     │
│  │   (puerto 3307)                      │     │
│  │   DB: Moscowle_Complete              │     │
│  └───────────────────────────────────────┘     │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Cambios en Docker

1. **docker-compose.override.yml** - Nuevo
   - Override para desarrollo local
   - Mapea puerto 8000 → 5000 interno
   - Monta volumen para cambios en vivo

2. **Dockerfile (backend/)** - Actualizado
   - Agregados compiladores para ML (g++, gfortran)
   - Librerías matemáticas (BLAS, LAPACK)
   - Instalación mejorada de dependencias

---

## ✅ Verificación Completa

### Script Automático: verify_k_means_complete.py

Realiza **9 verificaciones** automáticas:

```bash
python3 verify_k_means_complete.py
```

**Qué verifica:**

| # | Verificación | Descripción |
|---|---|---|
| 1 | 🐳 Docker Running | ¿Docker está activo? |
| 2 | 🐳 Container Active | ¿El contenedor del backend está corriendo? |
| 3 | 📄 Archivos | ¿ai_service.py y tests existen? |
| 4 | ⚙️ Función K-Means | ¿run_k_means_segmentation existe? |
| 5 | 📚 Imports ML | ¿scikit-learn, numpy, pandas, etc. cargables? |
| 6 | 📦 Dependencias | ¿Todas las dependencias instaladas? |
| 7 | 🔧 Flask App | ¿Aplicación Flask se crea correctamente? |
| 8 | 🔧 AI Service | ¿El módulo ai_service importa sin errores? |
| 9 | 🧪 Tests | ¿El test de K-Means pasa? |

**Salida esperada:**

```
✅ TODAS LAS VERIFICACIONES PASARON

✨ K-Means Clustering está listo para usar!

Endpoints disponibles:
  POST /api/ai/run_clustering - Ejecutar K-Means
  GET  /api/ai/clustering_status - Estado del clustering
```

---

## 🛠️ Comandos Útiles

### Ver Logs

```bash
# Logs en tiempo real
docker-compose logs -f backend

# Últimas 50 líneas
docker-compose logs --tail=50 backend

# Logs de todos los servicios
docker-compose logs -f
```

### Ejecutar Comandos en el Contenedor

```bash
# Test de K-Means
docker exec moscowle_backend_ai python3 /app/test_k_means_segmentation.py

# Python interactivo
docker exec -it moscowle_backend_ai python3

# Shell bash
docker exec -it moscowle_backend_ai bash

# Ver estructura de archivos
docker exec moscowle_backend_ai ls -la /app/app/services/
```

### Verificar Imports

```bash
docker exec moscowle_backend_ai python3 -c "
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
print('✅ Imports OK')
"
```

### Conectar a la Base de Datos

```bash
# Desde host
mysql -h localhost -P 3307 -u root -pRucula_530 Moscowle_Complete

# Desde contenedor backend
docker exec moscowle_backend_ai mysql -h db -u root -pRucula_530 Moscowle_Complete
```

### Estado de los Servicios

```bash
# Ver contenedores activos
docker ps

# Ver todos los contenedores (incluyendo parados)
docker ps -a

# Ver detalles de un contenedor
docker inspect moscowle_backend_ai
```

### Detener y Limpiar

```bash
# Detener servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Eliminar images
docker-compose down --rmi all

# Limpiar todo
docker system prune -a
```

---

## 🔗 URLs de Acceso

Una vez que todo está corriendo:

| Servicio | URL | Puerto |
|----------|-----|--------|
| Backend API | http://localhost:8000 | 8000 |
| Frontend | http://localhost:3002 | 3002 |
| Dashboard | http://localhost:3001 | 3001 |
| MySQL | localhost:3307 | 3307 |

---

## 🧪 Testing la API Manualmente

### Test 1: Health Check

```bash
curl -X GET http://localhost:8000/health
```

### Test 2: Ejecutar K-Means

```bash
curl -X POST http://localhost:8000/api/ai/run_clustering \
  -H "Content-Type: application/json" \
  -d '{"k": 3}'
```

### Test 3: Con Autenticación JWT

```bash
# Primero obten un token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "password"}' \
  | jq -r '.access_token')

# Luego usa el token
curl -X POST http://localhost:8000/api/ai/run_clustering \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"k": 3}'
```

---

## 🐛 Solución de Problemas

### Problema: "Container already exists"

**Solución:**
```bash
docker-compose down
docker-compose up -d
```

### Problema: "Port already in use"

**Solución:**
```bash
# Encuentra el proceso usando el puerto
lsof -i :8000

# O mata todos los contenedores
docker-compose down -v
```

### Problema: "Can't connect to database"

**Solución:**
```bash
# Verifica que DB está corriendo
docker-compose logs db

# Espera unos segundos y reintenta
sleep 10
python3 verify_k_means_complete.py
```

### Problema: "ModuleNotFoundError: No module named 'sklearn'"

**Solución:**
```bash
# Reconstruir imagen
docker-compose build --no-cache backend

# Reiniciar
docker-compose down && docker-compose up -d
```

### Problema: "Test falla sin conexión a DB"

**Solución:**
```bash
# Asegúrate que MySQL está healthy
docker-compose logs db

# Espera a que esté listo
docker-compose up db
# (espera 20 segundos)
# Luego en otra terminal: docker-compose up backend
```

---

## 📊 Estructura de Ficheros Docker

```
/Users/apple/Documents/moscowle/
├── docker-compose.yml                 # Configuración principal
├── backend/
│   ├── Dockerfile                     # Dockerfile actualizado
│   ├── docker-compose.override.yml    # Override para desarrollo
│   ├── requirements.txt               # Dependencias (actualizado con ML)
│   ├── start_backend_only.sh          # Script para iniciar solo backend
│   ├── test_k_means_segmentation.py   # Test unitario
│   ├── verify_k_means_docker.sh       # Script bash de verificación
│   ├── wsgi.py                        # Entry point Flask
│   └── app/
│       ├── __init__.py
│       └── services/
│           └── ai_service.py          # Módulo con run_k_means_segmentation()
│
├── run_and_verify.sh                  # Script maestro (TODO en Docker)
├── verify_k_means_complete.py         # Verificación Python (9 checks)
└── verify_k_means_docker.sh           # Verificación bash

```

---

## 📈 Verificación Post-Deploy

Después de desplegar, ejecuta:

```bash
# 1. Verificación completa
python3 verify_k_means_complete.py

# 2. Ver logs
docker-compose logs -f backend

# 3. Test manual
curl -X POST http://localhost:8000/api/ai/run_clustering -H "Content-Type: application/json" -d '{"k": 3}'
```

**Deberías ver:**
- ✅ 9/9 verificaciones pasando
- ✅ Logs sin errores
- ✅ Respuesta JSON con resultados de clustering

---

## 🎯 Checklist de Deployment

- [ ] Docker está corriendo (`docker --version`)
- [ ] Ejecuté `run_and_verify.sh` o `start_backend_only.sh`
- [ ] Ejecuté `python3 verify_k_means_complete.py` (9/9 pasó)
- [ ] Probé endpoints manualmente con curl
- [ ] Revisé logs sin errores
- [ ] Backend responde en puerto 8000
- [ ] MySQL responde en puerto 3307
- [ ] Test de K-Means pasó

---

## 🚀 Próximos Pasos

1. **Integración Frontend:** Usar hook `useAIRecommendation` en Dashboard
2. **Testing E2E:** Probar flujo completo backend → frontend
3. **Monitoreo:** Configurar logs y alertas en producción
4. **Optimización:** Ajustar recursos de contenedores según demanda

---

## 📞 Referencia Rápida

```bash
# Inicio rápido (TODO)
bash run_and_verify.sh

# Solo backend
cd backend && bash start_backend_only.sh

# Verificación
python3 verify_k_means_complete.py

# Logs
docker-compose logs -f backend

# Parar
docker-compose down
```

---

**Versión:** 1.0  
**Status:** ✅ Ready for Production  
**Última actualización:** 3 de diciembre de 2025
