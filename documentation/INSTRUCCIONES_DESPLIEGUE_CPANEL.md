# Guía de Despliegue en cPanel

Este documento detalla los pasos exactos para desplegar tu aplicación Flask (`moscowle_ia_mvp`) en un servidor cPanel usando "Setup Python App".

## 1. Archivos Requeridos
Asegúrate de subir la siguiente estructura al servidor (puedes crear un zip con todo esto):

- `app/` (Carpeta completa con tu código)
- `instance/` (Donde se guarda la BD sqlite y uploads)
- `ai_models/` (Carpeta para los modelos entrenados)
- `passenger_wsgi.py` (Archivo clave para cPanel)
- `requirements.txt`
- `.env` (Variables de entorno)
- `.htaccess` (Opcional, para forzar HTTPS)
- `config.py`

*(No subas la carpeta local `venv` o `.venv`, ni `__pycache__`)*

## 2. Configurar "Setup Python App" en cPanel

1. Inicia sesión en tu cPanel y busca **Setup Python App** (o "Administrador de aplicaciones Python").
2. Haz clic en **Create Application**.
3. Rellena los campos:
   - **Python Version**: Selecciona una versión reciente (3.9, 3.10 o 3.11 recomendada).
   - **Application Root**: La ruta donde subiste tus archivos (ej. `moscowle_ia_mvp`).
   - **Application URL**: Selecciona tu dominio (ej. `tudominio.com`).
   - **Application Startup File**: `passenger_wsgi.py` (Déjalo en blanco si usas el predeterminado, pero es mejo especificarlo o asegurarte de que `passenger_wsgi.py` existe).
   - **Application Entry Point**: `application` (Esto debe coincidir con la variable en `passenger_wsgi.py`).

4. Haz clic en **Create**.

## 3. Instalar Dependencias

1. En la misma pantalla de la aplicación creada, verás una ruta bajo "Virtual Environment", algo como `source /home/usuario/virtualenv/moscowle_ia_mvp/3.11/bin/activate`.
2. Copia ese comando comando para entrar a la terminal (o usa la interfaz gráfica si tu cPanel permite instalar `requirements.txt` directamente).
3. Si usas terminal (SSH o Terminal de cPanel):
   ```bash
   cd /home/usuario/moscowle_ia_mvp
   source /home/usuario/virtualenv/moscowle_ia_mvp/3.11/bin/activate
   pip install -r requirements.txt
   ```

## 4. Configurar Variables de Entorno

En la sección **Configuration** de tu app Python en cPanel, añade las variables de tu archivo `.env`:

| Name | Value |
|------|-------|
| `FLASK_APP` | `passenger_wsgi.py` |
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | (Tu clave secreta larga) |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:////home/usuario/moscowle_ia_mvp/instance/moscowle.db` (Usa ruta absoluta si es posible) |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_USERNAME` | (Tu gmail) |
| `MAIL_PASSWORD` | (Tu app password) |
| `USE_PROXYFIX` | `True` (Importante para HTTPS en cPanel) |
| `SESSION_COOKIE_SECURE` | `True` |

*Nota: Reemplaza `/home/usuario/...` con la ruta real de tu hosting.*

## 5. Reiniciar Aplicación
Después de cualquier cambio (código o configuración), siempre haz clic en **Restart** en la interfaz de Python App.

## 6. Verificación
Visita tu dominio. Si ves un error 500, revisa los logs en cPanel (generalmente archivos `error_log` en la carpeta raíz o en `/var/log/apache2/`).

## Solución de Problemas Comunes
- **Static files 404**: Flask sirve estáticos automáticamente en desarrollo, pero en producción a veces Passenger interfiere. Asegúrate de que no haya una carpeta `static` en `public_html` que "tape" la de Flask, o configura alias de estáticos en cPanel si es necesario.
- **Database read-only**: Asegúrate de que la carpeta `instance/` tenga permisos de escritura (`chmod 755` o `777` si es estrictamente necesario y seguro en tu entorno).
