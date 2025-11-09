# 🔌 Configuración de Conexión API - Backend

## 📡 Conectar Frontend con Backend API

Si tu página principal necesita conectarse con la API del backend (para formularios de contacto, servicios, etc.), sigue esta guía.

---

## 🎯 Escenarios de Despliegue

### **Escenario 1: Frontend y Backend en el MISMO servidor**
```
tudominio.com               → Frontend (Página principal)
tudominio.com/api           → Backend API
```

### **Escenario 2: Frontend y Backend en DIFERENTES servidores**
```
tudominio.com               → Frontend (Página principal)
api.tudominio.com           → Backend API (subdominio)
```

### **Escenario 3: Backend en servidor externo**
```
tudominio.com               → Frontend (Página principal)
backend.otrodominio.com     → Backend API (servidor diferente)
```

---

## ⚙️ Configuración según Escenario

### **Escenario 1: Mismo Servidor**

#### **Paso 1: Estructura de Carpetas en cPanel**
```
public_html/
├── index.html              ← Frontend
├── assets/
├── .htaccess              ← Frontend config
└── api/                   ← Backend
    ├── app.py             ← API Flask/FastAPI
    ├── requirements.txt
    └── .htaccess          ← API config
```

#### **Paso 2: Configurar .htaccess del Frontend**
Archivo: `public_html/.htaccess`
```apache
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteBase /

  # Excluir carpeta API de las redirecciones
  RewriteCond %{REQUEST_URI} !^/api/
  
  # Si el archivo o directorio existe, servirlo
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  
  # Redirigir a index.html para SPA
  RewriteRule . /index.html [L]
</IfModule>
```

#### **Paso 3: URLs en el Código Frontend**
En tu código React, las URLs de API serían:
```javascript
const API_BASE_URL = '/api';  // Ruta relativa

// Ejemplos:
fetch('/api/contact')
fetch('/api/services')
fetch('/api/inquiries')
```

---

### **Escenario 2: Subdominio API**

#### **Paso 1: Crear Subdominio en cPanel**
1. En cPanel → **"Subdomains"**
2. Crear subdominio: `api`
3. Document Root: `public_html/api` (o carpeta separada)

#### **Paso 2: Estructura**
```
public_html/              ← tudominio.com (frontend)
├── index.html
└── assets/

public_html/api/          ← api.tudominio.com (backend)
├── app.py
└── requirements.txt
```

#### **Paso 3: URLs en el Código**
```javascript
// Para producción
const API_BASE_URL = 'https://api.tudominio.com';

// Para desarrollo local
// const API_BASE_URL = 'http://localhost:8000';

// Uso:
fetch(`${API_BASE_URL}/contact`)
```

#### **Paso 4: Configurar CORS en Backend**
Archivo: `api/app.py` (FastAPI ejemplo)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tudominio.com",
        "https://www.tudominio.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### **Escenario 3: Servidor Externo**

#### **URLs en el Código**
```javascript
const API_BASE_URL = 'https://backend.otrodominio.com';

fetch(`${API_BASE_URL}/contact`)
```

#### **CORS en Backend Externo**
El backend debe permitir tu dominio:
```python
allow_origins=[
    "https://tudominio.com",
    "https://www.tudominio.com"
]
```

---

## 🔐 Variables de Entorno

### **Opción 1: Archivo .env (Desarrollo)**
Archivo: `.env`
```bash
VITE_API_URL=http://localhost:8000
```

Uso en código:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
```

### **Opción 2: Variables en Build**
Al hacer build, puedes especificar:
```bash
VITE_API_URL=https://api.tudominio.com npm run build
```

### **Opción 3: Configuración Condicional**
```javascript
const API_BASE_URL = 
  import.meta.env.MODE === 'production'
    ? 'https://api.tudominio.com'
    : 'http://localhost:8000';
```

---

## 📝 Configuración de Formulario de Contacto

### **Frontend (React)**
```javascript
// src/services/api.js
const API_BASE_URL = '/api'; // Ajusta según tu caso

export const sendContactForm = async (formData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/contact/inquiries`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData),
    });
    
    if (!response.ok) {
      throw new Error('Error al enviar formulario');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};
```

### **Uso en Componente**
```javascript
import { sendContactForm } from './services/api';

const handleSubmit = async (e) => {
  e.preventDefault();
  
  try {
    const result = await sendContactForm({
      first_name: formData.firstName,
      last_name: formData.lastName,
      email: formData.email,
      phone: formData.phone,
      message: formData.message,
      service_interest: formData.service,
    });
    
    toast.success('Mensaje enviado exitosamente');
  } catch (error) {
    toast.error('Error al enviar mensaje');
  }
};
```

---

## 🚀 Despliegue del Backend en cPanel

### **Paso 1: Preparar Backend Python**
```bash
# En tu computadora
cd backend/
pip freeze > requirements.txt
```

### **Paso 2: Subir Backend a cPanel**
1. Via FTP o File Manager
2. Subir a: `public_html/api/`
3. Incluir todos los archivos:
   - `app.py` (o tu archivo principal)
   - `requirements.txt`
   - Modelos, rutas, etc.

### **Paso 3: Configurar Python en cPanel**
1. En cPanel → **"Setup Python App"**
2. Crear nueva aplicación:
   - **Python version:** 3.9+ (la disponible)
   - **Application root:** `api/`
   - **Application URL:** `/api` o subdomain
   - **Application startup file:** `app.py`
   - **Application Entry point:** `app` (nombre de tu FastAPI/Flask app)

### **Paso 4: Instalar Dependencias**
En cPanel, en la aplicación Python:
```bash
source /path/to/virtualenv/bin/activate
pip install -r requirements.txt
```

### **Paso 5: Configurar Passenger**
Archivo: `api/passenger_wsgi.py`
```python
import sys
import os

# Ajusta la ruta a tu aplicación
sys.path.insert(0, os.path.dirname(__file__))

# Para FastAPI
from app import app as application

# Para Flask
# from app import app as application
```

---

## 🧪 Probar la Conexión

### **Test desde Navegador**
```javascript
// Abre consola del navegador (F12)
fetch('/api/health')
  .then(r => r.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

### **Test desde Terminal**
```bash
# Probar endpoint
curl https://tudominio.com/api/health

# Probar POST
curl -X POST https://tudominio.com/api/contact/inquiries \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","email":"test@example.com","message":"Test"}'
```

---

## ⚠️ Problemas Comunes

### **Error: CORS Policy Blocked**
**Solución:** Configurar CORS en backend
```python
allow_origins=["https://tudominio.com"]
```

### **Error: 502 Bad Gateway**
**Solución:** 
- Verifica que la aplicación Python esté corriendo
- Revisa logs: cPanel → "Error Log"
- Reinicia aplicación Python

### **Error: 404 Not Found en API**
**Solución:**
- Verifica rutas en `.htaccess`
- Asegúrate de que `RewriteCond` excluye `/api/`

### **Error: Database Connection Failed**
**Solución:**
- Verifica credenciales de base de datos
- Asegúrate de que MySQL está corriendo
- Verifica host (generalmente `localhost` en cPanel)

---

## 📚 Ejemplo Completo

### **Archivo de Configuración API**
```javascript
// src/config/api.js
export const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
};

export const endpoints = {
  contact: '/contact/inquiries',
  services: '/services',
  appointments: '/appointments',
};
```

### **Servicio de API**
```javascript
// src/services/contactService.js
import { API_CONFIG, endpoints } from '../config/api';

export const contactService = {
  async sendInquiry(data) {
    const response = await fetch(
      `${API_CONFIG.baseURL}${endpoints.contact}`,
      {
        method: 'POST',
        headers: API_CONFIG.headers,
        body: JSON.stringify(data),
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },
  
  async getServices() {
    const response = await fetch(
      `${API_CONFIG.baseURL}${endpoints.services}`
    );
    return await response.json();
  }
};
```

---

## ✅ Checklist de Configuración

- [ ] Backend desplegado en cPanel
- [ ] Python App configurada y corriendo
- [ ] Base de datos creada y configurada
- [ ] CORS configurado en backend
- [ ] URLs de API correctas en frontend
- [ ] .htaccess excluye ruta /api/
- [ ] SSL/HTTPS activo en ambos
- [ ] Formularios probados y funcionando
- [ ] Logs de errores revisados

---

¡Tu frontend y backend ahora están conectados! 🎉
