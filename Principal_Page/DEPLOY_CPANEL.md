# 🚀 Guía de Despliegue - Página Principal en cPanel

## ✅ Build Completado

El proyecto ha sido compilado exitosamente:
- **Tamaño total:** 453 KB JavaScript + 58 KB CSS
- **Comprimido (gzip):** 143 KB JS + 9 KB CSS
- **Archivos generados:** Carpeta `build/`

---

## ✅ Archivos Listos para Subir

La carpeta `build/` contiene:
```
build/
├── index.html              ← Archivo principal
├── logo.svg                ← Logo del centro de terapias
├── assets/
│   ├── index-VEeBYM32.css  ← Estilos optimizados
│   └── index-CfEBTmMc.js   ← JavaScript optimizado
└── .htaccess               ← Configuración de Apache
```

---

## 🌐 Pasos para Publicar en cPanel

### **Paso 1: Acceder a cPanel**
1. Abre tu navegador
2. Ve a: `https://tudominio.com/cpanel` o `https://tudominio.com:2083`
3. Ingresa tus credenciales de acceso

### **Paso 2: Abrir File Manager**
1. En el panel de cPanel, busca la sección **"Files"** (Archivos)
2. Haz clic en **"File Manager"** (Administrador de archivos)
3. Se abrirá el explorador de archivos del servidor

### **Paso 3: Preparar el Directorio**

#### **Para Dominio Principal:**
1. Navega a la carpeta `public_html/`
2. **IMPORTANTE:** Haz backup de archivos existentes
3. Elimina cualquier `index.html`, `index.php` antiguo

#### **Para Subdominio:**
1. En cPanel, ve a **"Subdomains"** (Subdominios)
2. Crea un subdominio (ej: `www`, `app`, `terapias`)
3. Navega a la carpeta del subdominio (ej: `public_html/subdominio/`)

#### **Para Carpeta Específica:**
1. Navega a `public_html/nombre-carpeta/`
2. O crea una nueva carpeta si es necesario

### **Paso 4: Subir los Archivos**

#### **Método 1: File Manager (Más Fácil)**
1. En File Manager, haz clic en el botón **"Upload"** (Subir)
2. Se abrirá el gestor de carga
3. Arrastra o selecciona **TODOS** los archivos de `build/`:
   - `index.html`
   - Carpeta `assets/` (completa con todos sus archivos)
   - `.htaccess`
3. Espera a que se complete la carga (verás barras de progreso)
4. **IMPORTANTE:** Asegúrate de subir también `logo.svg` en la raíz
5. Cierra el gestor de carga

#### **Método 2: Comprimir y Extraer (Para Muchos Archivos)**
1. En tu computadora, comprime la carpeta `build/` en un archivo ZIP
2. En File Manager de cPanel, sube el archivo ZIP
3. Haz clic derecho sobre el ZIP → **"Extract"** (Extraer)
4. Mueve los archivos de la carpeta `build/` al directorio raíz
5. Elimina el archivo ZIP y carpeta vacía

#### **Método 3: FTP (Para Usuarios Avanzados)**
1. Descarga FileZilla: https://filezilla-project.org/
2. En cPanel, ve a **"FTP Accounts"** (Cuentas FTP)
3. Obtén las credenciales FTP:
   - **Host:** ftp.tudominio.com
   - **Usuario:** tu usuario FTP
   - **Contraseña:** tu contraseña FTP
   - **Puerto:** 21 (o 22 para SFTP)
4. Conecta con FileZilla
5. Navega a `public_html/`
6. Arrastra todos los archivos de `build/` al servidor

---

## 🔧 Configuración Post-Despliegue

### **1. Verificar Permisos de Archivos**
En File Manager, selecciona todos los archivos y verifica:
- **Archivos:** Permisos `644` (rw-r--r--)
- **Carpetas:** Permisos `755` (rwxr-xr-x)

Para cambiar permisos:
1. Selecciona archivos/carpetas
2. Clic derecho → **"Change Permissions"** (Cambiar permisos)
3. Ajusta según corresponda

### **2. Verificar .htaccess**
1. En File Manager, asegúrate de que `.htaccess` sea visible
2. Si no lo ves, habilita archivos ocultos:
   - Settings → **"Show Hidden Files (dotfiles)"**
3. Verifica que `.htaccess` esté en la raíz junto a `index.html`

### **3. Configurar SSL/HTTPS (Recomendado)**
1. En cPanel, busca **"SSL/TLS Status"**
2. Activa **AutoSSL** para tu dominio (generalmente gratis)
3. Espera 5-10 minutos para la activación
4. Edita `.htaccess` y descomenta las líneas de redirección HTTPS:
```apache
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

### **4. Configurar Dominio/Subdominio**

#### **Para Dominio Principal:**
- Ya está listo: `https://tudominio.com`

#### **Para Subdominio:**
1. En cPanel → **"Subdomains"**
2. Verifica que apunte a la carpeta correcta
3. Espera propagación DNS (5-30 minutos)
4. Accede: `https://subdominio.tudominio.com`

#### **Para Carpeta:**
- Accede: `https://tudominio.com/nombre-carpeta/`

---

## 🧪 Verificación del Despliegue

### **Checklist de Pruebas:**
- [ ] La página principal carga correctamente
- [ ] Todos los estilos CSS se aplican
- [ ] Las imágenes y recursos cargan
- [ ] Los enlaces internos funcionan
- [ ] El formulario de contacto funciona (si tiene backend)
- [ ] La página es responsive (móvil, tablet, desktop)
- [ ] No hay errores en la consola (F12)
- [ ] SSL/HTTPS está activo (candado verde)

### **Herramientas de Prueba:**
```bash
# Verificar sitio
https://tudominio.com

# Test de SSL
https://www.ssllabs.com/ssltest/analyze.html?d=tudominio.com

# Test de velocidad
https://pagespeed.web.dev/

# Test responsive
https://responsivedesignchecker.com/
```

---

## 🐛 Solución de Problemas

### **Problema 1: Página en blanco**
**Síntomas:** Se ve página vacía o error de consola
**Soluciones:**
1. Presiona `F12` → pestaña "Console" para ver errores
2. Verifica que todos los archivos de `assets/` se hayan subido
3. Revisa permisos: archivos 644, carpetas 755
4. Limpia caché del navegador: `Ctrl+Shift+R` (Windows) o `Cmd+Shift+R` (Mac)

### **Problema 2: Estilos no cargan (página sin diseño)**
**Síntomas:** Texto plano sin formato
**Soluciones:**
1. Verifica que la carpeta `assets/` esté completa
2. Revisa en consola si hay errores 404
3. Asegúrate de que `.htaccess` esté presente
4. Verifica permisos de archivos CSS (644)

### **Problema 3: Error 404 - Not Found**
**Síntomas:** Error al acceder al sitio
**Soluciones:**
1. Verifica que `index.html` esté en la carpeta correcta
2. Asegúrate de estar en `public_html/` (dominio principal)
3. Verifica que el nombre del dominio esté configurado
4. Espera propagación DNS si acabas de configurar el dominio

### **Problema 4: Error 500 - Internal Server Error**
**Síntomas:** Error del servidor
**Soluciones:**
1. Verifica sintaxis de `.htaccess`
2. Revisa permisos: archivos 644, carpetas 755
3. Consulta error logs en cPanel → **"Error Log"**
4. Contacta soporte de hosting si persiste

### **Problema 5: Certificado SSL no funciona**
**Síntomas:** Advertencia de seguridad en navegador
**Soluciones:**
1. Verifica que AutoSSL esté activado en cPanel
2. Espera 15-30 minutos para activación completa
3. Verifica que el dominio apunte a los DNS correctos
4. Contacta soporte para instalación manual si es necesario

### **Problema 6: Formulario de contacto no funciona**
**Síntomas:** Formulario no envía datos
**Soluciones:**
1. Verifica que el backend/API esté en línea
2. Configura CORS en el servidor de la API
3. Revisa la URL de la API en el código
4. Verifica errores en consola del navegador

---

## 🔄 Cómo Actualizar el Sitio

Cuando hagas cambios en el código:

### **Método Rápido:**
1. Realiza cambios en tu proyecto local
2. Ejecuta: `npm run build`
3. En cPanel File Manager:
   - Elimina archivos antiguos de `assets/`
   - Sube nuevos archivos de `build/`
4. Limpia caché del navegador

### **Método Completo:**
1. Haz backup de la versión actual en cPanel
2. Genera nuevo build: `npm run build`
3. Elimina todo el contenido anterior
4. Sube todos los archivos nuevos
5. Verifica funcionamiento

### **Gestión de Caché:**
Los archivos tienen hash en el nombre (ej: `index-VEeBYM32.css`) que cambia con cada build, forzando actualización automática.

---

## 📊 Optimizaciones Aplicadas

### **✅ Ya Incluidas en .htaccess:**
- ✅ Compresión GZIP (reduce tamaño 70%)
- ✅ Caché de navegador configurado
- ✅ Redirecciones para SPA
- ✅ Headers de seguridad
- ✅ Tipos MIME correctos

### **🚀 Optimizaciones Adicionales (Opcionales):**

#### **1. Cloudflare (CDN Gratuito):**
- Acelera carga global
- Protección DDoS
- SSL gratis
- Configuración: https://www.cloudflare.com/

#### **2. Optimización de Imágenes:**
```bash
# Si tienes muchas imágenes, optimízalas antes de subir
# Usa herramientas como:
- TinyPNG: https://tinypng.com/
- ImageOptim (Mac)
- Squoosh: https://squoosh.app/
```

#### **3. Lazy Loading de Imágenes:**
Ya implementado si usas componentes modernos de React.

---

## 📞 Información de Soporte

### **Recursos Útiles:**
- **Documentación cPanel:** https://docs.cpanel.net/
- **Vite Deployment:** https://vitejs.dev/guide/static-deploy.html
- **React Deployment:** https://create-react-app.dev/docs/deployment/

### **Contactar Soporte:**
- **Hosting Provider:** Panel de soporte de tu proveedor
- **Logs de Errores:** cPanel → "Error Log"
- **Tickets:** Sistema de tickets del hosting

---

## ✨ Resumen Ejecutivo

```bash
# 1. Build generado (✅ COMPLETADO)
npm run build

# 2. Archivos listos en:
./build/
├── index.html
├── assets/
└── .htaccess

# 3. Subir a cPanel:
- Ruta: public_html/
- Método: File Manager o FTP

# 4. Verificar:
https://tudominio.com

# 5. Activar SSL:
cPanel → SSL/TLS Status → AutoSSL
```

---

## 🎉 ¡Listo para Producción!

Tu página principal está **optimizada, comprimida y lista** para cPanel:
- ✅ **Tamaño mínimo:** 143 KB (comprimido)
- ✅ **Carga rápida:** Optimizado para rendimiento
- ✅ **SEO ready:** Headers y meta tags correctos
- ✅ **Seguro:** HTTPS y headers de seguridad
- ✅ **Responsive:** Compatible con todos los dispositivos

**¡Solo falta subirlo!** 🚀
