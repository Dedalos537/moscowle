# Instrucciones de Actualización v5 (Multi-Terapista + Google Drive)

Este despliegue incluye cambios importantes en la base de datos para permitir asignar múltiples terapeutas a un paciente, así como la integración con Google Drive para guardar fotos de sesiones.

## Pasos para Desplegar

1. Subir el archivo `deploy_moscowle_v5.zip` a su servidor (cPanel/DirectAdmin).
2. Descomprimir el archivo, sobrescribiendo los existentes.
3. **Instalar Dependencias Nuevas**:
   
   Dentro de la carpeta del proyecto, ejecute:
   ```bash
   pip install -r requirements.txt
   ```

4. **IMPORTANTE: Ejecutar la Migración de Base de Datos**
   
   Es necesario crear la nueva tabla de unión `patient_therapist`. Para ello, ejecute el siguiente comando en la terminal (SSH) dentro de la carpeta del proyecto:

   ```bash
   python migrations/create_patient_therapist_table.py
   ```

   Si ve un mensaje como "Table 'patient_therapist' created successfully" o "Migrated X existing relationships", todo salió bien.

5. **Configurar Google Drive**:
   - Debe crear una "Cuenta de Servicio" (Service Account) en Google Cloud Console.
   - Descargar el archivo JSON de credenciales y renombrarlo a `google_credentials.json`.
   - Subir este archivo a la carpeta `instance/` de su aplicación en el servidor.
   - **Crucial**: Compartir la carpeta de Google Drive `https://drive.google.com/drive/folders/1eOJfoqKA2rFriGChB5O2INPHh4UZE55j` con el **email de la cuenta de servicio** (ej: `my-service-account@project-id.iam.gserviceaccount.com`) y darle permisos de "Editor".

6. Reiniciar la aplicación Python (desde el panel de control de cPanel/Passenger).

## Cambios Incluidos

1. **Sesiones Grupales**: Ahora puede crear sesiones con hasta 5 pacientes.
2. **Múltiples Terapeutas**: En el panel de administrador, puede asignar hasta 3 terapeutas a un mismo paciente.
3. **Respaldo en Drive**: Las fotos subidas en las sesiones se guardarán automáticamente en la carpeta de Drive especificada, organizadas por `NombrePaciente/FechaSesion`.
