# Runbook de Rollback — Moscowle IA

## Cuando Ejecutar Rollback

Rollback es forzado cuando:
- Health check falla 3+ veces consecutivas
- Tasa de error > 5% por mas de 5 minutos
- Incidente Critico (P1) causado por deploy reciente
- Feature flag `auto_rollback_enabled` esta activo

## Procedimiento

### 1. Rollback Automatico (Feature Flags)

Si esta habilitado `ROLLBACK_TRIGGERS`, el sistema automaticamente:
1. Detecta la condicion de fallo
2. Desactiva la feature flag problematica
3. Notifica al equipo
4. Genera incidente automatico

### 2. Rollback Manual — Railway

```bash
# Ver deployment actual
railway status

# Rollback al deploy anterior
railway rollback
```

### 3. Rollback Manual — cPanel (Frontend)

```bash
# Restaurar build anterior desde backup
cp -r /backups/frontend/latest/* /public_html/moscowle/
```

### 4. Rollback de Base de Datos

**PELIGRO**: Solo en casos criticos.

```bash
# Si hay migracion problematica
flask db downgrade
```

## Pre-Rollback Checklist

- [ ] Identificar la causa del fallo
- [ ] Verificar que el rollback resuelve el problema
- [ ] Notificar al equipo antes de ejecutar
- [ ] Crear incidente si no existe
- [ ] Documentar en el post-mortem

## Post-Rollback

1. Verificar que el sistema funciona correctamente
2. Ejecutar smoke tests: `flask diagnose`
3. Monitorear por 30 minutos
4. Crear post-mortem si es necesario
