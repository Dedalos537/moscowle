# Guía de Despliegue en DirectAdmin

Este documento detalla los pasos para desplegar tu aplicación Flask (`moscowle_ia_mvp`) en un servidor DirectAdmin usando "Setup Python App" (CloudLinux).

## 1. Preparar Archivos
Hemos generado un archivo `deploy_moscowle.zip` que contiene todo lo necesario.
Este archivo incluye:
- `app/` (Código fuente)
- `instance/` (Estructura para uploads y base de datos)
- `ai_models/` (Modelos de IA)
- `migrations/` (Migraciones de base de datos)
- `passenger_wsgi.py` (Punto de entrada para el servidor)
- `config.py` (Configuración)
- `requirements.txt` (Dependencias actualizadas)
- `run.py` (Script de ejecución opcional)

**NO incluido (Configurar manualmente):**
- `.env` (Debes crear este archivo en el servidor con tus secretos)
- Base de datos (Si usas MySQL, crea la base de datos en DirectAdmin)

## 2. Configurar "Setup Python App" en DirectAdmin

1. Inicia sesión en DirectAdmin.
2. Busca la sección **Extra Features** (o similar) y haz clic en **Setup Python App**.
3. Haz clic en **Create Application**.
4. Configura:
   - **Python Version**: Recomendado 3.10 o superior.
   - **Application Root**: `domains/tudominio.com/public_html/moscowle` (o la carpeta que prefieras).
   - **Application URL**: `tudominio.com/moscowle` (o la raíz si prefieres).
   - **Application Startup File**: `passenger_wsgi.py` (Dejar vacío suele crear uno por defecto, pero nosotros subiremos el nuestro. Si lo pide, escribe `passenger_wsgi.py`).
   - **Application Entry Point**: `application` (Muy importante: debe ser `application`).
   - **Passenger Log File**: Opcional, útil para depurar (`logs/passenger.log`).

5. Haz clic en **Create**.

## 3. Subir Archivos

1. Ve al **File Manager** de DirectAdmin.
2. Navega a la carpeta que definiste como **Application Root** (ej. `domains/tudominio.com/public_html/moscowle`).
3. Sube el archivo `deploy_moscowle.zip`.
4. Extrae el contenido del zip en esa carpeta.
   - Asegúrate de que `passenger_wsgi.py` reemplaza al que DirectAdmin pudo haber creado.
5. Crea la carpeta `instance/uploads` si no existe y dale permisos de escritura.

## 4. Instalar Dependencias

1. Vuelve a **Setup Python App** en DirectAdmin.
2. Abre la configuración de tu aplicación.
3. En la sección "Configuration files", escribe `requirements.txt` y haz clic en "Add".
4. Una vez añadido, haz clic en el botón **Run Pip Install**.
   - Esto instalará todas las librerías automáticamente en el entorno virtual.

## 5. Configurar Variables de Entorno

En la misma pantalla de configuración de la app:
1. Busca la sección **Environment variables**.
2. Añade las variables clave de tu archivo `.env` local:
   - `FLASK_APP`: `passenger_wsgi.py`
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: (Genera una clave segura)
   - `SQLALCHEMY_DATABASE_URI`: (Tu conexión a MySQL o la ruta a SQLite, ej. `sqlite:////home/usuario/domains/tudominio.com/public_html/moscowle/instance/moscowle.db`)
   - `MAIL_SERVER`, `MAIL_PASSWORD`, etc.

## 6. Base de Datos (Migraciones)

Si usas MySQL:
1. Crea la base de datos en DirectAdmin -> MySQL Management.
2. Configura `SQLALCHEMY_DATABASE_URI` con `mysql+pymysql://usuario:password@localhost/nombre_db`.
3. Para inicializar la base de datos, necesitas ejecutar los comandos de Flask.
4. Accede por SSH al servidor (si tienes acceso):
   ```bash
   source /home/usuario/virtualenv/moscowle/3.10/bin/activate  # Ruta virtualenv mostrada en Setup Python App
   cd /home/usuario/domains/tudominio.com/public_html/moscowle
   export FLASK_APP=passenger_wsgi.py
   flask db upgrade
   ```
   *Nota: Si no puedes usar SSH, puedes crear una ruta temporal en Flask que ejecute `db.create_all()` o usar un script python ejecutado desde el Cron Job una sola vez.*

## 7. Reiniciar

1. En **Setup Python App**, haz clic en **Restart** para aplicar los cambios.
2. Visita tu URL.
