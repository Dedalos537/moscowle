# 🚀 Guía de Despliegue en cPanel

## ✅ Archivos Listos para Subir

La carpeta `build/` contiene todos los archivos necesarios para producción:
- `index.html` - Archivo principal
- `assets/` - CSS, JavaScript y recursos optimizados
- `.htaccess` - Configuración de Apache para React Router

---

## 📋 Pasos para Publicar en cPanel

### **Paso 1: Acceder a cPanel**
1. Ingresa a tu cuenta de cPanel (generalmente: `tudominio.com/cpanel`)
2. Introduce tus credenciales de acceso

### **Paso 2: Abrir File Manager (Administrador de Archivos)**
1. En cPanel, busca la sección **"Files"** (Archivos)
2. Haz clic en **"File Manager"** (Administrador de archivos)

### **Paso 3: Navegar al Directorio Público**
Dependiendo de tu configuración, debes subir los archivos a:
- `public_html/` - Para el dominio principal
- `public_html/subdominio/` - Para un subdominio
- `public_html/carpeta/` - Para una subcarpeta específica

### **Paso 4: Subir los Archivos**

#### **Opción A: Usando File Manager (Recomendado)**
1. Navega a la carpeta destino (ej: `public_html/`)
2. **IMPORTANTE**: Elimina cualquier archivo `index.html` o `index.php` existente
3. Haz clic en el botón **"Upload"** (Subir)
4. Selecciona **TODOS** los archivos de la carpeta `build/`:
   - `index.html`
   - Carpeta `assets/`
   - `.htaccess`
5. Espera a que se complete la carga

#### **Opción B: Usando FTP**
1. Usa un cliente FTP como FileZilla
2. Conecta con tus credenciales FTP (disponibles en cPanel)
3. Navega al directorio `public_html/`
4. Arrastra todos los archivos de la carpeta `build/` al servidor

---

## 🔧 Configuración Post-Despliegue

### **1. Verificar Permisos de Archivos**
En File Manager, asegúrate de que:
- Archivos: Permisos `644`
- Carpetas: Permisos `755`

### **2. Configurar Variables de Entorno (API)**
Si tu aplicación se conecta a una API:

1. **Opción 1 - API en el mismo servidor:**
   - No necesitas cambios adicionales
   - La URL será: `https://tudominio.com/api`

2. **Opción 2 - API en servidor diferente:**
   - Asegúrate de que la API tenga CORS configurado
   - Verifica que las URLs de API en el código apunten a la dirección correcta

### **3. Habilitar HTTPS (SSL)**
1. En cPanel, busca **"SSL/TLS Status"**
2. Activa AutoSSL para tu dominio
3. Descomenta las líneas de redirección HTTPS en `.htaccess` si lo deseas

### **4. Configurar Subdominios (Opcional)**
Si quieres usar un subdominio como `dashboard.tudominio.com`:
1. En cPanel > **"Subdomains"**
2. Crea el subdominio apuntando a la carpeta con los archivos
3. Espera la propagación DNS (5-30 minutos)

---

## 🌐 Verificación del Despliegue

### **Checklist de Pruebas:**
- [ ] La página principal carga correctamente
- [ ] Las rutas de React Router funcionan (ej: `/dashboard`, `/messages`)
- [ ] Los estilos CSS se aplican correctamente
- [ ] Los archivos estáticos (imágenes, fuentes) cargan bien
- [ ] El login funciona si está conectado a una API
- [ ] No hay errores en la consola del navegador (F12)

### **Comandos de Prueba:**
```bash
# Verificar el sitio
https://tudominio.com

# Verificar SSL
https://www.ssllabs.com/ssltest/analyze.html?d=tudominio.com

# Verificar velocidad
https://pagespeed.web.dev/
```

---

## 🐛 Solución de Problemas Comunes

### **Problema 1: Página en blanco**
**Causa:** Rutas incorrectas en el build
**Solución:**
1. Verifica que `vite.config.ts` tenga `base: './'` o `base: '/'`
2. Regenera el build: `npm run build`
3. Vuelve a subir los archivos

### **Problema 2: Error 404 al refrescar**
**Causa:** `.htaccess` no funciona o no existe
**Solución:**
1. Verifica que el archivo `.htaccess` se haya subido correctamente
2. Asegúrate de que Apache tiene `mod_rewrite` habilitado
3. Contacta a tu proveedor de hosting si persiste

### **Problema 3: Estilos no cargan**
**Causa:** Rutas de assets incorrectas
**Solución:**
1. Verifica la consola del navegador (F12)
2. Asegúrate de que la carpeta `assets/` se subió completamente
3. Verifica permisos de archivos (644)

### **Problema 4: API no se conecta**
**Causa:** CORS o URL incorrecta
**Solución:**
1. Verifica la URL de la API en el código
2. Configura CORS en el servidor de la API
3. Verifica que el backend esté en línea

---

## 📊 Optimizaciones Adicionales

### **1. Cloudflare (Opcional pero Recomendado)**
- Activa Cloudflare para CDN gratuito
- Mejora velocidad y seguridad
- Protección DDoS automática

### **2. Caché del Navegador**
El `.htaccess` ya incluye configuración de caché para:
- Imágenes: 1 año
- CSS/JS: 1 mes
- HTML: Sin caché (para actualizaciones inmediatas)

### **3. Compresión GZIP**
Ya está habilitada en `.htaccess` para reducir el tamaño de los archivos

---

## 🔄 Actualizaciones Futuras

Para actualizar tu sitio:
1. Realiza cambios en el código
2. Ejecuta: `npm run build`
3. Sube SOLO los archivos modificados en `build/` (o todos para estar seguro)
4. El caché del navegador se actualizará automáticamente gracias a los hash en los nombres

---

## 📞 Soporte Adicional

Si necesitas ayuda:
- **Hosting Provider:** Contacta el soporte de tu proveedor
- **Documentación cPanel:** https://docs.cpanel.net/
- **Vite Deployment:** https://vitejs.dev/guide/static-deploy.html

---

## ✨ Resumen Rápido

```bash
# 1. Generar build (YA HECHO)
npm run build

# 2. Archivos a subir están en:
./build/

# 3. Subirlos a cPanel en:
public_html/

# 4. Verificar:
https://tudominio.com
```

¡Tu dashboard está listo para producción! 🎉
