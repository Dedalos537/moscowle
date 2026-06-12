# Plan de Rollback

## Rollback de Base de Datos

```bash
# 1. Identificar el backup más reciente
ls -t backups/*.sql.gz | head -1

# 2. Descomprimir
gunzip -c backups/moscowle_20260101_120000.sql.gz > /tmp/rollback.sql

# 3. Parsear URI de MySQL desde .env
# Ejemplo:
#   mysql+pymysql://user:pass@host:3306/dbname
#   MYSQL_USER=user MYSQL_PASS=pass MYSQL_HOST=host MYSQL_DB=dbname

# 4. Ejecutar rollback
mysql -u "$MYSQL_USER" -p"$MYSQL_PASS" -h "$MYSQL_HOST" "$MYSQL_DB" < /tmp/rollback.sql
```

## Rollback de Código

```bash
# Deploy anterior (vía Railway)
railway rollback

# O revertir commit específico
git revert HEAD
git push origin main
```

## Activación de Modo Degradado

Si una feature nueva causa problemas:

1. Deshabilitar vía env var:
```bash
railway variables set FEATURE_FLAGS='{"new_dashboard":{"enabled":false}}'
```

2. Railway reinicia automáticamente el servicio.

3. Verificar que el health endpoint responda:
```bash
curl https://moscowle-backend-production.up.railway.app/api/health
```

## Criterios de Rollback

Hacer rollback si:

- Error rate > 5% en últimos 5 minutos
- /health no responde en > 3 segundos
- Backup más reciente tiene > 24 horas de antigüedad
- Cualquier 500 en ruta crítica (login, dashboard, API payments)
