-- Migration script for SessionMetrics table
-- This creates the session_metrics table to track performance metrics 
-- for therapeutic game sessions

CREATE TABLE IF NOT EXISTS `session_metrics` (
    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `game_name` VARCHAR(255) NOT NULL,
    `accuracy_rate` FLOAT NOT NULL DEFAULT 0.0 COMMENT 'Accuracy percentage (0-100)',
    `average_time` FLOAT NOT NULL DEFAULT 0.0 COMMENT 'Average time in seconds',
    `failed_attempts` INT NOT NULL DEFAULT 0 COMMENT 'Number of failed attempts',
    `previous_level` INT NOT NULL DEFAULT 1 COMMENT 'Current level (1-3)',
    `predicted_next_level` INT COMMENT 'Next predicted level (0, 1, 2, 3, or NULL)',
    `cluster_id` INT COMMENT 'K-Means cluster ID assigned by ML algorithm',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of session creation',
    
    -- Indexes
    INDEX `idx_patient_id` (`patient_id`),
    INDEX `idx_game_name` (`game_name`),
    INDEX `idx_created_at` (`created_at`),
    
    -- Foreign Keys
    CONSTRAINT `fk_session_metrics_patient` FOREIGN KEY (`patient_id`)
        REFERENCES `patients`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: Create composite index for common queries
CREATE INDEX IF NOT EXISTS `idx_patient_game` ON `session_metrics` (`patient_id`, `game_name`);

-- Optional: Create index for ML analysis queries
CREATE INDEX IF NOT EXISTS `idx_cluster_date` ON `session_metrics` (`cluster_id`, `created_at`);
