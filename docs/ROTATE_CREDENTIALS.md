# Rotación de Credenciales — Moscowle IA

> **Estado:** Pendiente
> **Creado:** 2026-06-09
> **Riesgo:** Crítico — contraseña `Rucula_530` reusada en DB, email y admin

---

## Resumen

El archivo `.env` existe en disco con credenciales de producción reales. Aunque `.env` está en `.gitignore` y `.dockerignore` (no trackeado por git, no incluido en builds Docker), **las siguientes credenciales deben rotarse** por seguridad:

---

## Secreto #1: Contraseña Admin/DB/Mail (`Rucula_530`)

**Reusada en 3 servicios diferentes — riesgo máximo.**

| Servicio | Usuario | Dónde cambiar |
|----------|---------|---------------|
| MySQL DB | `centroju_diego` | cPanel > phpMyAdmin o Railway MySQL |
| Email corporativo | `info@centrojuanpabloii.com` | cPanel > Email Accounts |
| Admin del sistema | `diegocenteno537@gmail.com` | Flask admin password (en `config.py`) |

**Política:** 3 contraseñas diferentes, 16+ caracteres cada una, con mayúscula, número y símbolo.

---

## Secreto #2: Gemini API Key

| Actual | `AIzaSyAyowkKss2KoREfUQoZ-G39E5bOZdmrc98` |
|--------|--------------------------------------------|
| Dónde rotar | https://makersuite.google.com/app/apikey |
| Riesgo | Si se filtra, cualquiera puede usar tu cuenta de Gemini (costo $) |
| Acción | Generar nueva API key, revocar la actual |

---

## Secreto #3: Groq API Key

| Actual | `gsk_REVOCADO_rotar_en_console_groq` |
|--------|-------------------------------------------------------------|
| Dónde rotar | https://console.groq.com/keys |
| Riesgo | Si se filtra, cualquiera puede usar tu cuenta de Groq (costo $) |
| Acción | Generar nueva API key, revocar la actual |

---

## Secreto #4: Flask Secret Key

| Actual | `moscowle_secret_key_production_2024` |
|--------|---------------------------------------|
| Dónde cambiar | `config.py` lee de `APP_SECRET_KEY` env var |
| Riesgo | Si se filtra, cualquiera puede forjar sesiones |
| Acción | Generar con: `python -c "import secrets; print(secrets.token_hex(32))"` |

---

## Secreto #5: Gmail App Password (respaldo)

| Actual | `dmvpyuskpjahwfjr` |
|--------|--------------------|
| Dónde rotar | https://myaccount.google.com/apppasswords |
| Riesgo | Acceso a Gmail de diegocenteno537@gmail.com |
| Acción | Generar nuevo app password, revocar el actual |

---

## Procedimiento de Rotación

1. **Generar** nuevas credenciales fuera del proyecto
2. **Actualizar** Railway environment variables (dashboard.railway.app)
3. **Actualizar** cPanel si corresponde (email, MySQL)
4. **Actualizar** `.env` local con nuevas credenciales
5. **Verificar** que `/api/health` retorna healthy
6. **Revocar** credenciales anteriores después de verificar

---

## Archivos que Protegen `.env`

| Archivo | Protege contra |
|---------|----------------|
| `.gitignore` (line 2) | Commit accidental a git |
| `.dockerignore` (line 3) | Inclusión en build Docker |
