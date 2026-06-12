# Plan Integral Post-Auditoría

## Hallazgos vs Especificación Técnica (Semanas 1-13)

## Fases de Implementación

### Fase A: Seguridad (P0 — Crítica)
- A.1 Rotar credenciales (.env out of git, contraseñas únicas)
- A.2 Ollama URL a env var (9 archivos)
- A.3 CSP headers estrictos (sin unsafe-inline)
- A.4 Password strength validation
- A.5 SQL injection fix (backup_service.py)
- A.6 Verificar XSS sanitizer en runtime

### Fase B: Base de Datos (P1 — Alta)
- B.1 Soft delete + auditoría en 25 tablas
- B.2 Índices B-Tree explícitos
- B.3 Read/Write Split: documentar deuda, preparar SQLALCHEMY_BINDS

### Fase C: Pruebas (P1 — Alta)
- C.1 BDD/Gherkin: 3 escenarios Login
- C.2 Fix 15 tests fallidos
- C.3 SQLi simulation tests
- C.4 Security test suite (XSS, CSRF, CORS, rate limit)

### Fase D: Operaciones & Monitoreo (P2 — Media)
- D.1 Feature flags system
- D.2 Prometheus /metrics endpoint
- D.3 Backup SQL real (mysqldump script)
- D.4 Plan de rollback operable
- D.5 Catálogo de Solicitudes (request/approve workflow)
- D.6 Protocolo de crisis (feature flags + thresholds)

### Fase E: Frontend & UX (P3 — Baja)
- E.1 Mobile First consistente (max-width → min-width)
- E.2 Password strength UI indicator

### Fase F: Trazabilidad (P3 — Baja, continua)
- F.1 Commits con user stories + criterios de aceptación
- F.2 PR template con checklist

## Deuda Técnica Documentada
- Read/Write Split: requiere infraestructura MySQL con réplicas
- JWT: sesiones Flask-Login funcionan, migrar si hay clientes no-browser
