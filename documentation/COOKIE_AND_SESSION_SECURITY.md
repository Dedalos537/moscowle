# 🛡️ Cookie & Session Security (Guía rápida)

**Propósito:** explicar cómo configurar cookies seguras y recordar cookies para producción.

## Recomendación
- En producción, siempre habilitar `SESSION_COOKIE_SECURE=True` para que cookies solo se envíen por HTTPS.
- Usar `SESSION_COOKIE_HTTPONLY=True` para prevenir acceso desde JavaScript.
- Ajustar `SESSION_COOKIE_SAMESITE='Lax'` (o `Strict` si aplica) para mitigar CSRF de tercer partido.
- Para `remember me` (Flask-Login) usar `REMEMBER_COOKIE_*` con mismos flags.

## Cómo configurarlo (.env)

Añade estas líneas a tu archivo `.env` en el servidor de producción:

```env
# Forzar esquema url generation
PREFERRED_URL_SCHEME=https

# Session cookies (activar en producción)
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Remember cookie (Flask-Login)
REMEMBER_COOKIE_SECURE=True
REMEMBER_COOKIE_HTTPONLY=True
REMEMBER_COOKIE_SAMESITE=Lax

# HSTS (Strict-Transport-Security)
HSTS_SECONDS=31536000
HSTS_INCLUDE_SUBDOMAINS=True
```

## Notas operativas
- En desarrollo local no uses `SESSION_COOKIE_SECURE=True` a menos que sirvas sobre HTTPS localmente.
- Si usas un proxy inverso (Nginx) asegúrate de pasar `X-Forwarded-Proto` y configurar Flask/Gunicorn para reconocerlo (ej. `ProxyFix`).
- Verifica cookies en el navegador (DevTools → Application → Cookies) y comprueba `Secure`, `HttpOnly` y `SameSite` flags.

## Comprobación rápida (post-deploy)
1. Accede a la app en `https://your.domain`.
2. En DevTools → Application → Cookies, inspecciona las cookies de sesión y recuerda:
   - `Secure` debe estar activado
   - `HttpOnly` debe estar activado
   - `SameSite` debe ser `Lax` o `Strict`
3. Verifica cabeceras HSTS en respuesta HTTP:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (si `HSTS_INCLUDE_SUBDOMAINS` True)

## Problemas comunes
- Cookie no marcada como `Secure`: probablemente estás en HTTP o no configuraste el proxy para pasar `X-Forwarded-Proto`.
- `HttpOnly` ausente: revisa que la configuración cargue desde `.env` y que no haya sobrescritura posterior.

## Recursos
- Flask docs: https://flask.palletsprojects.com/
- Flask-Login remember cookie: https://flask-login.readthedocs.io/
- OWASP Secure Cookie Recommendations: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
