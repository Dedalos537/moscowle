# Deploy Guide — Moscowle IA

## Arquitectura

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Frontend    │     │  Backend (Flask)      │     │  MySQL (Railway)    │
│  Railway     │────▶│  Railway              │────▶│  mysql-volume       │
│  + cpanel    │     │  moscowle-backend-    │     │                     │
│              │     │  production.up.       │     └─────────────────────┘
└─────────────┘     │  railway.app          │
                    └──────────────────────┘
```

### URLs

| Servicio | URL |
|----------|-----|
| Frontend (Railway) | `https://moscowle.up.railway.app` |
| Frontend (cpanel) | `https://moscowle.centrojuanpabloii.com` |
| Backend API | `https://moscowle-backend-production.up.railway.app` |
| MySQL | `mysql-production-fe1e.up.railway.app` |

### Credenciales admin
- Email: `diegocenteno537@gmail.com`
- Password: `Rucula_530`

---

## 1. Backend (Railway)

### Deploy automático
Railway despliega automáticamente al hacer push a `main` en `soud31135-stack/moscowle-railway`.

```bash
# Standard flow
git add -A
git commit -m "feat(api): descripción"
git push origin main
```

### Deploy manual
```bash
railway service moscowle-backend
railway redeploy --yes
```

### Verificar deploy
```bash
curl -s https://moscowle-backend-production.up.railway.app/api/health | python3 -m json.tool
```

### Variables de entorno (Railway)
```bash
railway variables                          # Listar todas
railway variables set KEY=value            # Set individual
railway variables set KEY1=val1 KEY2=val2  # Set múltiples
```

### Rollback
```bash
railway rollback
```

---

## 2. Frontend — Railway

### Repo
`soud31135-stack/moscowle-frontend-production`

### Estructura del repo
```
moscowle-frontend-production/
├── Dockerfile          # nginx alpine sirviendo archivos estáticos
├── browser/            # Archivos build de Angular (output de ng build)
│   ├── index.html
│   ├── main-*.js
│   ├── chunk-*.js
│   ├── styles-*.css
│   └── assets/
└── README.md
```

### Flujo de deploy

El frontend de Railway NO compila desde source. Recibe los archivos **ya compilados** (build output).

```bash
# 1. Build local del Angular
cd edysync
npx ng build --configuration production

# 2. Copiar build al repo de Railway
rm -rf /tmp/frontend-prod-check/browser
cp -r dist/edysync/browser /tmp/frontend-prod-check/browser

# 3. Commit y push
cd /tmp/frontend-prod-check
git add -A
git commit -m "feat: actualizar build [fecha]"
git push origin main

# 4. Deploy a Railway
railway service moscowle-frontend-production
railway up
```

### Dockerfile
```dockerfile
FROM nginx:alpine
COPY browser /app
# nginx sirve archivos estáticos en puerto 8080
# Angular llama al backend directamente via apiBaseUrl
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

### Por qué no hay nginx proxy
El build de producción (`environment.prod.ts`) tiene `apiBaseUrl: 'https://moscowle-backend-production.up.railway.app'` hardcodeado. Angular hace llamadas directas al backend. No se necesita proxy en nginx.

### Verificar deploy
```bash
curl -s https://moscowle.up.railway.app/auth/login | grep "<title>"
# Debe mostrar: Centro Juan Pablo II
```

---

## 3. Frontend — cpanel (FTP)

### Servidor
`dedalos` vía FTP → `moscowle.centrojuanpabloii.com`

### Flujo de deploy
```bash
# 1. Build local
cd edysync
npx ng build --configuration production

# 2. Subir vía FTP
ftp -n dedalos << EOF
binary
cd public_html
mdelete *.html *.js *.css
mdelete -r assets
mput dist/edysync/browser/*
mput -r dist/edysync/browser/assets
bye
EOF
```

### Verificar deploy
```bash
curl -s https://moscowle.centrojuanpabloii.com/auth/login | grep "<title>"
```

---

## 4. Convention de Commits

### Formato
```
<tipo>(<ámbito>): <descripción>
```

### Tipos válidos
| Tipo | Uso |
|------|-----|
| `feat` | Nueva feature |
| `fix` | Bug fix |
| `refactor` | Reestructuración sin cambio de comportamiento |
| `test` | Agregar/modificar tests |
| `docs` | Solo documentación |
| `chore` | Build, CI, dependencias |
| `spec` | Especificación o design document |
| `prp` | PRP (Product Requirements Prompt) |
| `plan` | Implementation plan |
| `debug` | Commit de debugging/investigación |

### Ámbitos válidos
`api`, `models`, `auth`, `ui`, `db`, `ci`, `monitor`, `chat`, `payment`, `report`, `core`, `config`, `deploy`, `frontend`

### Ejemplos
```
feat(auth): implementar login OAuth Google
fix(api): corregir validación email en registro
refactor(models): extraer AuditMixin a base.py
feat(deploy): actualizar build frontend Railway
fix(frontend): corregir display timezone en sesiones
```

### Referencia a tickets
En el body del commit:
```
feat(payment): agregar soporte para Yape

Referencia: MOSCOWLE-42
```

Si no hay ticket: `Referencia: N/A`

### Breaking changes
Agregar `!` antes de los dos puntos:
```
refactor(db)!: migrar de SQLite a PostgreSQL
```

---

## 5. Pre-commit Hooks

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Hooks activos:
- `ruff` — linter + formatter
- `ruff (security)` — reglas de seguridad
- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json`
- `check-added-large-files`, `detect-private-key`, `debug-statements`
- `commit-msg-validator` — valida formato del mensaje

---

## 6. Verificación post-deploy

```bash
# Backend health
curl -s https://moscowle-backend-production.up.railway.app/api/health

# Frontend Railway
curl -s -o /dev/null -w "%{http_code}" https://moscowle.up.railway.app/auth/login

# Frontend cpanel
curl -s -o /dev/null -w "%{http_code}" https://moscowle.centrojuanpabloii.com/auth/login

# Login test
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"diegocenteno537@gmail.com","password":"Rucula_530"}' \
  https://moscowle-backend-production.up.railway.app/auth/login
```

---

## 7. Troubleshooting

### Frontend Railway no actualiza
1. Verificar que el push llegó: `gh api repos/soud31135-stack/moscowle-frontend-production/commits --jq '.[0] | {sha: .sha[0:7], message: .commit.message}'`
2. Forzar deploy: `railway service moscowle-frontend-production && railway up`
3. Si Railway no detecta el Dockerfile, agregar `railway.toml`:
   ```toml
   [build]
   builder = "DOCKERFILE"
   dockerfilePath = "Dockerfile"
   ```

### Backend no responde
1. Verificar health: `curl https://moscowle-backend-production.up.railway.app/api/health`
2. Verificar logs: `railway service moscowle-backend && railway logs`
3. Rollback: `railway rollback`

### API CORS errors
El backend permite CORS solo para el frontend configurado. Si cambia la URL del frontend, actualizar `CORS_ORIGINS` en las variables de entorno de Railway.

### 401 en API calls
El JWT token expira. El frontend maneja refresh automático. Si persiste, verificar que `JWT_SECRET_KEY` coincida entre frontend y backend.

---

## 8. Branches

| Branch | Uso |
|--------|-----|
| `main` | Producción (auto-deploy en Railway) |
| `develop` | Integración |
| `fix/*` | Fixes temporales |
| `feat/*` | Features temporales |

### Merge a main
```bash
git checkout main
git merge develop
git push origin main
# Railway despliega automáticamente
```
