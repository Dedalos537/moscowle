-- Script de inicialización de la base de datos para el sistema de mensajería
-- Centro de Terapias Juan Pablo II

-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS Moscowle_Complete CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE Moscowle_Complete;

-- Tabla de roles del sistema
CREATE TABLE IF NOT EXISTS roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL COMMENT 'admin, therapist, assistant, patient, parent',
    description TEXT,
    permissions JSON COMMENT 'Permisos específicos por módulo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla principal de usuarios
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP NULL,
    last_login TIMESTAMP NULL,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    INDEX idx_email (email),
    INDEX idx_status (status)
);

-- Perfiles de usuarios del sistema (staff)
CREATE TABLE IF NOT EXISTS user_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    specialty VARCHAR(100) COMMENT 'Para terapeutas',
    license_number VARCHAR(100) COMMENT 'Número de cédula profesional',
    hire_date DATE,
    birth_date DATE,
    address TEXT,
    emergency_contact_name VARCHAR(200),
    emergency_contact_phone VARCHAR(20),
    photo_url VARCHAR(500),
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Formularios de contacto desde la web (leads y mensajes anónimos)
CREATE TABLE IF NOT EXISTS contact_inquiries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inquiry_code VARCHAR(20) UNIQUE NOT NULL COMMENT 'Código único para seguimiento',
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    subject VARCHAR(200),
    message TEXT NOT NULL,
    service_interest VARCHAR(200) COMMENT 'Servicio de interés',
    urgency ENUM('low', 'medium', 'high') DEFAULT 'medium',
    status ENUM('new', 'contacted', 'in_progress', 'resolved', 'closed') DEFAULT 'new',
    assigned_to INT COMMENT 'Usuario administrativo asignado',
    follow_up_date DATE,
    notes TEXT COMMENT 'Notas internas del staff',
    source VARCHAR(100) DEFAULT 'website' COMMENT 'website, referral, social_media, etc.',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_assigned_to (assigned_to)
);

-- Conversaciones/hilos de mensajes
CREATE TABLE IF NOT EXISTS conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inquiry_id INT COMMENT 'Relacionado con un inquiry específico',
    title VARCHAR(200),
    type ENUM('inquiry', 'support', 'internal') DEFAULT 'inquiry',
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
    status ENUM('open', 'pending', 'resolved', 'closed') DEFAULT 'open',
    is_archived BOOLEAN DEFAULT FALSE,
    created_by INT COMMENT 'Usuario que inició la conversación',
    assigned_to INT COMMENT 'Usuario asignado para responder',
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES contact_inquiries(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    INDEX idx_status (status),
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_last_message_at (last_message_at)
);

-- Mensajes en conversaciones
CREATE TABLE IF NOT EXISTS messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT,
    inquiry_id INT COMMENT 'Puede estar asociado directamente a un inquiry',
    sender_type ENUM('user', 'anonymous', 'system') NOT NULL,
    sender_user_id INT COMMENT 'Si es un usuario del sistema',
    sender_name VARCHAR(200) COMMENT 'Nombre del remitente anónimo',
    sender_email VARCHAR(255) COMMENT 'Email del remitente anónimo',
    message_text TEXT NOT NULL,
    message_type ENUM('text', 'file', 'image', 'system') DEFAULT 'text',
    file_url VARCHAR(500),
    file_name VARCHAR(255),
    file_size INT COMMENT 'Tamaño en bytes',
    is_read BOOLEAN DEFAULT FALSE,
    is_internal BOOLEAN DEFAULT FALSE COMMENT 'Mensaje interno del staff',
    read_at TIMESTAMP NULL,
    read_by INT COMMENT 'Usuario que leyó el mensaje',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (inquiry_id) REFERENCES contact_inquiries(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_user_id) REFERENCES users(id),
    FOREIGN KEY (read_by) REFERENCES users(id),
    INDEX idx_conversation (conversation_id),
    INDEX idx_inquiry (inquiry_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_read (is_read)
);

-- Notificaciones del sistema
CREATE TABLE IF NOT EXISTS notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    type VARCHAR(50) NOT NULL COMMENT 'new_inquiry, new_message, assignment, etc.',
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSON COMMENT 'Datos adicionales específicos del tipo',
    is_read BOOLEAN DEFAULT FALSE,
    action_url VARCHAR(500) COMMENT 'URL para acción directa',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_created_at (created_at)
);

-- Log de actividades para auditoría
CREATE TABLE IF NOT EXISTS activity_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) COMMENT 'inquiry, conversation, message, etc.',
    entity_id INT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_action (user_id, action),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_created_at (created_at)
);

-- Insertar roles básicos
INSERT IGNORE INTO roles (name, description, permissions) VALUES
('admin', 'Administrador del sistema', '{"all": true}'),
('therapist', 'Terapeuta profesional', '{"patients": ["read", "write"], "appointments": ["read", "write"], "messages": ["read", "write"]}'),
('assistant', 'Asistente administrativo', '{"inquiries": ["read", "write"], "messages": ["read", "write"], "appointments": ["read"]}');

-- Insertar usuario administrador por defecto
INSERT IGNORE INTO users (email, password_hash, role_id, status, email_verified) VALUES
('admin@juanpablo2.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdXrYvfHGz3uO', 1, 'active', TRUE);

-- Insertar perfil del administrador
INSERT IGNORE INTO user_profiles (user_id, first_name, last_name, phone) VALUES
(1, 'Administrador', 'Principal', '+52 555 0000 0000');

-- Crear índices adicionales para optimización
CREATE INDEX idx_inquiry_status_created ON contact_inquiries(status, created_at);
CREATE INDEX idx_message_type_created ON messages(message_type, created_at);
CREATE INDEX idx_conversation_status_updated ON conversations(status, updated_at);

-- Crear trigger para actualizar last_message_at en conversations
DELIMITER //
CREATE TRIGGER IF NOT EXISTS update_conversation_last_message
    AFTER INSERT ON messages
    FOR EACH ROW
BEGIN
    IF NEW.conversation_id IS NOT NULL THEN
        UPDATE conversations 
        SET last_message_at = NEW.created_at,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.conversation_id;
    END IF;
END//
DELIMITER ;

-- Crear trigger para generar código único de inquiry
DELIMITER //
CREATE TRIGGER IF NOT EXISTS generate_inquiry_code
    BEFORE INSERT ON contact_inquiries
    FOR EACH ROW
BEGIN
    IF NEW.inquiry_code IS NULL OR NEW.inquiry_code = '' THEN
        SET NEW.inquiry_code = CONCAT('INQ', LPAD(LAST_INSERT_ID() + 1, 6, '0'));
    END IF;
END//
DELIMITER ;

-- Mostrar resumen de tablas creadas
SELECT 
    'Tablas creadas para el sistema de mensajería:' as resumen,
    COUNT(*) as total_tablas
FROM information_schema.tables 
WHERE table_schema = 'Moscowle_Complete' 
AND table_name IN ('roles', 'users', 'user_profiles', 'contact_inquiries', 'conversations', 'messages', 'notifications', 'activity_logs');