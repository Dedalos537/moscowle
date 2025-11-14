-- Script de inicialización de la base de datos
-- Centro de Terapias Juan Pablo II - Backend Unificado

CREATE DATABASE IF NOT EXISTS Moscowle_Complete CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE Moscowle_Complete;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'therapist') DEFAULT 'therapist',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
);

-- Perfiles de usuarios
CREATE TABLE IF NOT EXISTS user_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    specialization VARCHAR(200),
    bio TEXT,
    license_number VARCHAR(100),
    experience_years INT,
    avatar_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Consultas de contacto
CREATE TABLE IF NOT EXISTS contact_inquiries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    message TEXT NOT NULL,
    inquiry_code VARCHAR(10) UNIQUE NOT NULL,
    status ENUM('new', 'contacted', 'in_progress', 'resolved', 'closed') DEFAULT 'new',
    service_type VARCHAR(100),
    preferred_contact_method VARCHAR(50) DEFAULT 'email',
    urgency_level VARCHAR(20) DEFAULT 'medium',
    assigned_therapist_id INT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_therapist_id) REFERENCES users(id),
    INDEX idx_status (status),
    INDEX idx_inquiry_code (inquiry_code),
    INDEX idx_created_at (created_at)
);

-- Conversaciones
CREATE TABLE IF NOT EXISTS conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inquiry_id INT,
    therapist_id INT,
    client_name VARCHAR(200),
    client_email VARCHAR(255),
    status ENUM('active', 'paused', 'closed') DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES contact_inquiries(id) ON DELETE SET NULL,
    FOREIGN KEY (therapist_id) REFERENCES users(id),
    INDEX idx_inquiry (inquiry_id),
    INDEX idx_therapist (therapist_id),
    INDEX idx_status (status)
);

-- Mensajes
CREATE TABLE IF NOT EXISTS messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    sender_type ENUM('client', 'therapist', 'admin', 'system') NOT NULL,
    sender_id INT,
    content TEXT NOT NULL,
    message_type ENUM('text', 'file', 'image', 'system') DEFAULT 'text',
    attachments TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_conversation (conversation_id),
    INDEX idx_sender (sender_type, sender_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_read (is_read)
);

-- Respuestas NPS
CREATE TABLE IF NOT EXISTS nps_responses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inquiry_id INT,
    conversation_id INT,
    score INT NOT NULL CHECK (score >= 0 AND score <= 10),
    category ENUM('detractor', 'passive', 'promoter') NOT NULL,
    comment TEXT,
    service_type VARCHAR(100),
    therapist_id INT,
    anonymous_email VARCHAR(255),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES contact_inquiries(id) ON DELETE SET NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    FOREIGN KEY (therapist_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_score (score),
    INDEX idx_category (category),
    INDEX idx_created_at (created_at)
);

-- Interacciones para mapa de calor
CREATE TABLE IF NOT EXISTS heat_map_interactions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    page_url VARCHAR(500) NOT NULL,
    element_selector VARCHAR(500),
    interaction_type ENUM('click', 'hover', 'scroll', 'focus') NOT NULL,
    coordinates_x INT,
    coordinates_y INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    user_agent TEXT,
    ip_address VARCHAR(45),
    inquiry_id INT,
    conversation_id INT,
    FOREIGN KEY (inquiry_id) REFERENCES contact_inquiries(id) ON DELETE SET NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    INDEX idx_page_url (page_url),
    INDEX idx_interaction_type (interaction_type),
    INDEX idx_timestamp (timestamp),
    INDEX idx_session_id (session_id)
);

-- Insertar usuario admin por defecto
INSERT IGNORE INTO users (username, email, password_hash, role, is_active) VALUES
('admin', 'admin@moscowle.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdXrYvfHGz3uO', 'admin', TRUE);

-- Insertar perfil del admin
INSERT IGNORE INTO user_profiles (user_id, first_name, last_name) VALUES
(1, 'Administrador', 'Sistema');

-- Mostrar resumen
SELECT 'Base de datos inicializada correctamente' as status;