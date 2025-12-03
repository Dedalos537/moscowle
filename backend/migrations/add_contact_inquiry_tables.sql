-- Migration: Add ContactInquiry and Message tables
-- Created for handling contact form submissions and admin messaging

CREATE TABLE IF NOT EXISTS contact_inquiry (
  id INT AUTO_INCREMENT PRIMARY KEY,
  inquiry_code VARCHAR(20) UNIQUE NOT NULL COMMENT 'Format: INQ-XXXXXXXX',
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(20),
  subject VARCHAR(255),
  message LONGTEXT NOT NULL,
  service_interest VARCHAR(255),
  urgency ENUM('low', 'medium', 'high') DEFAULT 'medium',
  status ENUM('new', 'contacted', 'in_progress', 'resolved', 'closed') DEFAULT 'new',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_status (status),
  INDEX idx_email (email),
  INDEX idx_created_at (created_at),
  FULLTEXT INDEX ft_search (first_name, last_name, email, subject, message)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS message (
  id INT AUTO_INCREMENT PRIMARY KEY,
  inquiry_id INT NOT NULL,
  sender_type ENUM('user', 'anonymous', 'system', 'admin') DEFAULT 'user',
  sender_name VARCHAR(255),
  sender_email VARCHAR(255),
  message_text LONGTEXT NOT NULL,
  message_type ENUM('text', 'file', 'image', 'system') DEFAULT 'text',
  is_read BOOLEAN DEFAULT FALSE,
  is_internal BOOLEAN DEFAULT FALSE COMMENT 'Internal notes not shown to user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (inquiry_id) REFERENCES contact_inquiry(id) ON DELETE CASCADE,
  INDEX idx_inquiry_id (inquiry_id),
  INDEX idx_sender_type (sender_type),
  INDEX idx_created_at (created_at),
  INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add triggers for automatic timestamp updates
DELIMITER $$

CREATE TRIGGER contact_inquiry_update_timestamp 
BEFORE UPDATE ON contact_inquiry
FOR EACH ROW
BEGIN
  SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

CREATE TRIGGER message_update_timestamp 
BEFORE UPDATE ON message
FOR EACH ROW
BEGIN
  SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

DELIMITER ;
