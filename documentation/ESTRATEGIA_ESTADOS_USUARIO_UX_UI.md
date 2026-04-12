# Estrategia de Estados de Usuario - UX/UI Best Practices

## Problema Actual
El sistema tiene un dropdown con 4 estados pero no guardaba correctamente. Ya está resuelto.

## Estados Recomendados (Estándar de Industria)

### 1. **ACTIVO** 🟢
- Usuario puede acceder al sistema
- Todas las funciones disponibles
- Aparece en listas de terapistas
- Puede realizar pagos
- **Indicador Visual**: Punto verde

### 2. **INACTIVO** ⚪
- Usuario NO puede acceder = contraseña desactivada
- No aparece en listas públicas
- Datos conservados (reversible)
- Caso de uso: Suspensión temporal
- **Indicador Visual**: Punto gris

### 3. **RETIRADO** 🔴
- Usuario se fue permanentemente
- NO aparece en ninguna lista o dropdown
- NO puede acceder al sistema
- Datos guardados para auditoría
- Puede ser reactivado si es necesario
- **Indicador Visual**: Punto rojo con X
- **Para Terapistas**: No aparece como opción de asignación

### 4. **DEUDOR** 🟡
- Usuario ACTIVO pero con pagos pendientes
- Puede acceder al sistema
- Aparece en listas de terapistas
- Indicador visual de alerta
- Puede hacer nuevos pagos para resolver
- **Indicador Visual**: Punto amarillo/naranja con ⚠️

## Diagrama de Estados

```
    NUEVO USUARIO
         ↓
      ACTIVO ← → INACTIVO (suspensión temporal)
         ↓
      DEUDOR (si hay pagos vencidos)
         ↓
     RETIRADO (fin de relación)
```

## Implementación en SQL

```sql
-- Valores válidos
CHECK (account_status IN ('active', 'inactive', 'retired', 'debtor'))

-- Índice para queries frecuentes
CREATE INDEX idx_user_account_status ON user(account_status);
```

## Lógica de Negocio Recomendada

### Cuando cambiar a DEUDOR
- Si un paciente tiene pagos vencidos > 5 días
- Automático via scheduler (cada noche)
- Notificación al admin y al usuario

### Cuando cambiar a RETIRADO
- Usuario solicita retirarse
- No asistencia a sesiones > 3 meses (configurable)
- Contrato finalizado

### Cuando cambiar a INACTIVO
- Admin pausa la cuenta temporalmente
- Usuario solicita pausa
- Violación de política (temporal)

## UI/UX Recomendaciones

### 1. Selector de Estado (Página Admin)
```html
<select>
  <option value="active">
    🟢 Activo - Acceso completo
  </option>
  <option value="inactive">
    ⚪ Inactivo - Suspendido (sin acceso)
  </option>
  <option value="debtor">
    🟡 Deudor - Pagos pendientes
  </option>
  <option value="retired">
    🔴 Retirado - Relación finalizada
  </option>
</select>
```

### 2. Badge Visual (Lista de Usuarios)
```
Usuario Activo:   [🟢 Activo]
Usuario Inactivo: [⚪ Inactivo]
Usuario Deudor:   [🟡 S/. 500 deudor]
Usuario Retirado: [🔴 Retirado]
```

### 3. Indicador de Estado (Perfil Usuario)
- Circulito de color en esquina de avatar
- Tooltip: "Estado: Retirado desde 15/03/2026"

## Filtrado Inteligente

### Para Terapistas (al listar pacientes):
```python
# NO mostrar RETIRADOS ni INACTIVOS
query = User.query.filter(
    User.role == 'jugador',
    User.account_status.in_(['active', 'debtor'])
)
```

### Para Admin (lista completa):
- Mostrar TODOS con estado identificado
- Opción de filtro: "Solo Activos", "Deudores", etc.

### Para Pacientes (terap available):
```python
# Solo mostrar TERAPISTAS ACTIVOS
query = User.query.filter(
    User.role == 'terapista',
    User.account_status == 'active'
)
```

## Notificaciones Automáticas

### Transición a DEUDOR
- Email al paciente: "Tienes un pago vencido"
- Notificación al admin: "Nuevo deudor: Juan García - S/. 300"
- En dashboard: Badge rojo con cantidad

### Transición a RETIRADO
- Archive en historial
- Notificación al admin
- Opción de reactivar en 30 días

## Migración de Datos Inicial

```sql
-- Convertir etiquetas antiguas al nuevo campo
UPDATE user 
SET account_status = CASE 
    WHEN notes LIKE '%[RETIRED]%' THEN 'retired'
    WHEN notes LIKE '%[DEBTOR]%' THEN 'debtor'
    WHEN is_active = false THEN 'inactive'
    ELSE 'active'
END
WHERE account_status IS NULL OR account_status = 'active';
```

## Comparativa con Otros ERP

### Xuno (Gym/Clinic)
- Similar: Estados binarios + etiquetas
- Mejor: Indica razón de retiro
- Lección: Agregar campo `retirement_reason`

### Clinica.fit
- 6 estados: active, paused, debt, finished, archived, removed
- Mejor: Diferencia entre "archived" (temporal) y "removed" (definitivo)
- Lección: Considerar agregar "ARCHIVADO"

### Genexus (Facturación)
- Estados: Vigente, Suspendido, Bloqueado, Inactivo
- Mejor: Diferencia entre suspender (temporal) y bloquear (sanción)
- Lección: Modelo actual ya lo cubre bien

## Recomendación Final

**El modelo actual (ACTIVO, INACTIVO, RETIRADO, DEUDOR) es sólido.**

Mejoras futuras sugeridas:
1. ✅ Agregar `retirement_reason` (texto corto)
2. ✅ Agregar `account_status_changed_at` (timestamp)
3. ✅ Agregar `account_status_changed_by` (user_id admin que hizo cambio)
4. ✅ Crear scheduler para auto-cambiar a DEUDOR si hay pagos vencidos
5. ✅ Dashboard widget mostrando estadísticas por estado

## Testing Checklist

- [ ] Admin cambia usuario a Retirado → No aparece en lista de terapistas
- [ ] Paciente deudor → Puede ver su deuda en dashboard
- [ ] Reactivar retirado → Funciona correctamente
- [ ] Dropdown refleja estado actual
- [ ] API filtra correctamente por estado
