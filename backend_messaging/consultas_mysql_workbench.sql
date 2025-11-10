-- =====================================================
-- CONSULTAS PARA MYSQL WORKBENCH
-- Centro de Terapias Juan Pablo II
-- =====================================================

-- Usar la base de datos
USE Moscowle_Complete;

-- Ver todas las consultas de contacto
SELECT 
    id,
    inquiry_code AS 'Código',
    CONCAT(first_name, ' ', last_name) AS 'Nombre Completo',
    email AS 'Email',
    phone AS 'Teléfono',
    subject AS 'Asunto',
    message AS 'Mensaje',
    service_interest AS 'Servicio de Interés',
    urgency AS 'Urgencia',
    status AS 'Estado',
    created_at AS 'Fecha de Creación',
    updated_at AS 'Última Actualización'
FROM contact_inquiries 
ORDER BY created_at DESC;

-- Contar consultas por estado
SELECT 
    status AS 'Estado',
    COUNT(*) AS 'Cantidad'
FROM contact_inquiries 
GROUP BY status;

-- Contar consultas por urgencia
SELECT 
    urgency AS 'Urgencia',
    COUNT(*) AS 'Cantidad'
FROM contact_inquiries 
GROUP BY urgency;

-- Consultas de las últimas 24 horas
SELECT 
    CONCAT(first_name, ' ', last_name) AS 'Nombre',
    email,
    subject AS 'Asunto',
    urgency AS 'Urgencia',
    created_at AS 'Fecha'
FROM contact_inquiries 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY created_at DESC;

-- Ver usuarios del sistema
SELECT 
    u.id,
    u.email,
    u.is_active AS 'Activo',
    r.name AS 'Rol',
    up.first_name AS 'Nombre',
    up.last_name AS 'Apellido',
    u.created_at AS 'Creado en'
FROM users u
LEFT JOIN roles r ON u.role_id = r.id
LEFT JOIN user_profiles up ON u.id = up.user_id
ORDER BY u.created_at DESC;

-- Estadísticas generales
SELECT 
    'Total Consultas' AS 'Métrica',
    COUNT(*) AS 'Valor'
FROM contact_inquiries
UNION ALL
SELECT 
    'Consultas Nuevas',
    COUNT(*)
FROM contact_inquiries 
WHERE status = 'new'
UNION ALL
SELECT 
    'Consultas Pendientes',
    COUNT(*)
FROM contact_inquiries 
WHERE status IN ('new', 'contacted', 'in_progress')
UNION ALL
SELECT 
    'Usuarios Registrados',
    COUNT(*)
FROM users
UNION ALL
SELECT 
    'Consultas Hoy',
    COUNT(*)
FROM contact_inquiries 
WHERE DATE(created_at) = CURDATE();