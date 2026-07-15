# Runbook de Diagnostico — Moscowle IA

## Comando Rapido

```bash
flask diagnose
```

Ejecuta todos los checks de diagnostico en secuencia.

## Diagnostico Manual

### 1. Base de Datos
```bash
flask diagnose-db
```

Verifica:
- Conexion a la base de datos
- Latencia de respuesta
- Conteo de registros principales (users, appointments, incidents)

### 2. API
```bash
flask diagnose-api
```

Verifica:
- Endpoint `/api/health` responde
- Estado de la base de datos
- Estado de servicios externos (LLM, CrisisMonitor)

### 3. Verificacion de Servicios

Si la API no responde:
1. Verificar que el proceso Flask este corriendo
2. Revisar logs: `railway logs` o `tail -f /var/log/app.log`
3. Verificar variables de entorno (DATABASE_URL, JWT_SECRET_KEY)
4. Verificar conectividad a la base de datos

### 4. Incidentes

Si hay alertas de incidentes:
1. Revisar `/api/incidents/dashboard` para KPIs
2. Verificar SLA compliance en `/api/incidents/metrics`
3. Escalar segun la matriz de escalamiento (N1 -> N2 -> N3)

## Umbrales de Alerta

| Metrica | Warning | Critical | Accion |
|---------|---------|----------|--------|
| CPU | >=70% | >=80% | Notificar -> Auto-scale |
| RAM | >=80% | >=90% | Notificar -> Restart |
| Disco | >=80% | >=85% | Notificar -> Cleanup |
| Latencia API | >=2.0s p95 | >=3.0s p95 | Notificar -> Scale |
| DB Connections | >=50 | >=80 | Notificar -> Restart |

## Contactos

- **N1 (Warning)**: Terapeuta/Leader — Email
- **N2 (Error)**: Equipo TI — Email + Slack
- **N3 (Critical)**: Directorio — Email + Slack + SMS
