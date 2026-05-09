# Environment & Proxy — Guía de Entornos

## Índice

1. [Problema que resuelve](#1-problema-que-resuelve)
2. [Arquitectura](#2-arquitectura)
3. [Archivos involucrados](#3-archivos-involucrados)
4. [Flujos de trabajo](#4-flujos-de-trabajo)
5. [Cómo agregar un nuevo endpoint](#5-cómo-agregar-un-nuevo-endpoint)
6. [Solución de problemas](#6-solución-de-problemas)

---

## 1. Problema que resuelve

En producción, Flask corre detrás de **Passenger/cPanel** que inyecta `SCRIPT_NAME=/moscowle`. Esto significa que:

- Una ruta definida como `@auth_bp.route('/login')` en Flask se sirve en `/moscowle/login`
- Angular en producción debe llamar a `/moscowle/login`
- Lo mismo aplica para TODAS las rutas: `/api/sessions` → `/moscowle/api/sessions`

En desarrollo local, Flask corre con `python run.py` **sin `SCRIPT_NAME`**:

- La misma ruta `/login` se sirve en `/login`
- Angular en dev debe llamar a `/login`

El patrón **`ApiBaseInterceptor` + `environment.apiBaseUrl`** resuelve esto automáticamente sin tocar los services.

---

## 2. Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                         Angular (browser)                         │
│                                                                   │
│  Cualquier service:  return this.http.get('/api/sessions')        │
│                           ↓                                      │
│  ApiBaseInterceptor:  apiBaseUrl = environment.apiBaseUrl         │
│                       '/api/sessions'  →  '/moscowle/api/sessions'│
│                           ↓                                      │
│  AuthInterceptor:  withCredentials: true                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │  ng serve (solo dev)
                           │  proxy.conf.js
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Proxy Target                                 │
│                                                                   │
│  PROXY_TARGET = process.env.PROXY_TARGET                          │
│               | 'http://localhost:5000'  (default)                 │
│                                                                   │
│  Contextos: /api, /admin/api, /therapist/api, /uploads            │
│            /moscowle/api, /moscowle/admin/api, ...                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Backend                                     │
│                                                                   │
│  Dev:  localhost:5000  (python run.py)  — sin SCRIPT_NAME         │
│  Prod: www.centrojuanpabloii.com  (Passenger con SCRIPT_NAME)     │
└──────────────────────────────────────────────────────────────────┘
```

### Cómo funciona el interceptor

```typescript
// core/interceptors/api-base.interceptor.ts
intercept(req, next) {
  const base = environment.apiBaseUrl;  // '' o '/moscowle'
  if (base && req.url.startsWith('/')) {
    req = req.clone({ url: base + req.url });
  }
  return next.handle(req);
}
```

**En dev** (`apiBaseUrl = ''`): no modifica URLs. Todo sale como está escrito en los services.

**En producción** (`apiBaseUrl = '/moscowle'`): antepone `/moscowle` a TODA ruta que empiece con `/`. Así:
- `/login` → `/moscowle/login`
- `/api/sessions` → `/moscowle/api/sessions`
- `/admin/api/expenses` → `/moscowle/admin/api/expenses`

---

## 3. Archivos involucrados

### `src/environments/environment.ts` — Desarrollo local

```typescript
export const environment = {
  production: false,
  apiBaseUrl: '',  // ← Sin prefijo, el proxy se encarga
};
```

Usado por: `ng serve`, `npm start`

### `src/environments/environment.prod.ts` — Producción

```typescript
export const environment = {
  production: true,
  apiBaseUrl: '/moscowle',  // ← Passenger SCRIPT_NAME
};
```

Usado por: `ng build --prod`, `ng serve -c production`

Intercambiado automáticamente por `fileReplacements` en `angular.json`.

### `src/app/core/interceptors/api-base.interceptor.ts`

```typescript
@Injectable()
export class ApiBaseInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler) {
    const base = environment.apiBaseUrl;
    if (base && req.url.startsWith('/')) {
      const newReq = req.clone({ url: base + req.url });
      return next.handle(newReq);
    }
    return next.handle(req);
  }
}
```

Registrado en `CoreModule` con `multi: true` en los `HTTP_INTERCEPTORS`.

### `proxy.conf.js` — Proxy de desarrollo

```javascript
const TARGET = process.env.PROXY_TARGET || 'http://localhost:5000';

const common = ['/api', '/admin/api', '/therapist/api', '/uploads'];
const moscowle = common.map(p => '/moscowle' + p);

module.exports = [
  {
    context: [...common, ...moscowle],
    target: TARGET,
    ...
  },
];
```

Incluye ambos sets de contextos:
- Sin `/moscowle`: para `npm start` (dev, `apiBaseUrl = ''`)
- Con `/moscowle`: para `npm run start:prod` (producción, `apiBaseUrl = '/moscowle'`)

## 4. Flujos de trabajo

### 4.1 Desarrollo local

```bash
# Terminal 1: Backend Flask
cd /home/eduar/proyectos/moscowle_ia
python run.py
# Flask corre en http://localhost:5000

# Terminal 2: Frontend Angular
cd /home/eduar/proyectos/moscowle_ia/edysync
npm start
# Angular corre en http://localhost:4200
```

**Data flow:**

```
localhost:4200/login               → proxy no aplica (no está en context)
                                      → directo a localhost:5000/login → Flask ✅

localhost:4200/api/sessions         → proxy detecta /api
                                      → reenvía a localhost:5000/api/sessions → Flask ✅

localhost:4200/therapist/api/profile → proxy detecta /therapist/api
                                        → reenvía a localhost:5000/therapist/api/profile → Flask ✅
```

### 4.2 Probar contra producción desde local

```bash
cd /home/eduar/proyectos/moscowle_ia/edysync
npm run start:prod
```

**Qué hace:**
1. `PROXY_TARGET=https://www.centrojuanpabloii.com` — proxy apunta a producción
2. `-c production` — usa `environment.prod.ts` → `apiBaseUrl = '/moscowle'`
3. `ApiBaseInterceptor` antepone `/moscowle` a TODAS las rutas
4. `/login` → `/moscowle/login` → proxy contexto `/moscowle` → `www.centrojuanpabloii.com/moscowle/login` ✅
5. `/api/sessions` → `/moscowle/api/sessions` → proxy contexto `/moscowle/api` → `www.centrojuanpabloii.com/moscowle/api/sessions` ✅

### 4.3 Build producción

```bash
cd /home/eduar/proyectos/moscowle_ia/edysync
npm run build:prod
```

Genera archivos estáticos en `dist/` con `apiBaseUrl = '/moscowle'`. Al servirlos desde Flask/Passenger, todas las peticiones llevan el prefijo correcto.

---

## 5. Cómo agregar un nuevo endpoint

Simplemente escribe la ruta relativa en el service:

```typescript
// NO necesitas importar environment
// NO necesitas preocuparte por el prefijo
return this.http.get('/api/mi-endpoint');
return this.http.post('/therapist/api/algo', data);
```

El `ApiBaseInterceptor` se encarga de anteponer `apiBaseUrl` automáticamente. Los únicos archivos que conocen `environment` son:

- `api-base.interceptor.ts` — lo usa para el prefijo
- Cualquier service que necesite lógica específica por entorno (poco común)

### Registrar en el proxy si es necesario

Si el endpoint es nuevo y usas `ng serve` con proxy, verifica que el contexto esté en `proxy.conf.js`. Los contextos actuales cubren:

```
/api, /admin/api, /therapist/api, /uploads
/moscowle/api, /moscowle/admin/api, /moscowle/therapist/api, /moscowle/uploads
```

Si tu nuevo endpoint usa un prefijo diferente, agrégalo al array `common` en `proxy.conf.js`.

---

## 6. Solución de problemas

### 6.1 "401 Unauthorized" en dev

Causa: El proxy no está redirigiendo correctamente. Verifica:
- Flask corriendo en `localhost:5000`
- Proxy apunta a `localhost:5000`
- No estás usando `-c production` sin querer

### 6.2 "404 Not Found"

Causa: La ruta no existe en el backend. Revisa Network tab en DevTools:
- Dev: la ruta debe ser `/api/sessions` (sin prefijo)
- `start:prod`: la ruta debe ser `/moscowle/api/sessions` (con prefijo)

Si ves `/moscowle/api/sessions` en dev mode, significa que estás usando `environment.prod.ts` por error.

### 6.3 CORS

No debería ocurrir porque Angular se sirve desde el mismo dominio que Flask (Passenger). Si ocurre:

```python
from flask_cors import CORS
CORS(app, origins=['https://www.centrojuanpabloii.com'])
```

### 6.4 Proxy no funciona

Verifica que `angular.json` tenga:

```json
"serve": {
  "options": {
    "proxyConfig": "proxy.conf.js"
  }
}
```

### 6.5 Apuntar a un servidor custom

```bash
# Servidor sin SCRIPT_NAME
PROXY_TARGET=https://staging.miservidor.com ng serve

# Servidor con SCRIPT_NAME=/moscowle
PROXY_TARGET=https://staging.miservidor.com ng serve -c production
```
