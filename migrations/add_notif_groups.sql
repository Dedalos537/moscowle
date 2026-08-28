-- Migration: Create notif_group and notif_item tables
-- Reduces notification volume from ~8600/day to ~50-150/day via grouping

CREATE TABLE IF NOT EXISTS notif_group (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    user_id INTEGER NOT NULL,
    group_key VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'system',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    title VARCHAR(200) NULL,
    summary TEXT NULL,
    `count` INTEGER NOT NULL DEFAULT 0,
    last_item_at DATETIME NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    is_collapsed BOOLEAN NOT NULL DEFAULT 1,
    ai_summary_generated BOOLEAN NOT NULL DEFAULT 0,
    digest_sent BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_notif_group_user_key (user_id, group_key),
    INDEX idx_notif_group_user_id (user_id),
    INDEX idx_notif_group_user_read (user_id, is_read),
    INDEX idx_notif_group_last_item (last_item_at),
    INDEX idx_notif_group_user_category (user_id, category),
    CONSTRAINT fk_notif_group_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notif_item (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message VARCHAR(255) NOT NULL,
    type VARCHAR(50) NULL DEFAULT 'info',
    priority VARCHAR(20) NULL DEFAULT 'normal',
    icon VARCHAR(50) NULL,
    link VARCHAR(255) NULL,
    metadata_json JSON NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notif_item_group_id (group_id),
    INDEX idx_notif_item_user_id (user_id),
    INDEX idx_notif_item_timestamp (timestamp),
    CONSTRAINT fk_notif_item_group FOREIGN KEY (group_id) REFERENCES notif_group(id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_item_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migrate existing unread Notification data into notif_group + notif_item
-- Using a subquery approach compatible with only_full_group_by

INSERT IGNORE INTO notif_group (user_id, group_key, category, priority, title, summary, `count`, last_item_at, is_read, is_collapsed, created_at)
SELECT
    sub.user_id,
    sub.group_key,
    sub.category,
    sub.priority,
    NULL AS title,
    NULL AS summary,
    sub.cnt AS `count`,
    sub.last_item_at,
    sub.is_read,
    1 AS is_collapsed,
    sub.created_at
FROM (
    SELECT
        n.user_id,
        CONCAT('legacy:', n.category, ':', DATE(n.timestamp)) AS group_key,
        n.category,
        CASE
            WHEN SUM(CASE WHEN n.priority = 'urgent' THEN 1 ELSE 0 END) > 0 THEN 'urgent'
            WHEN SUM(CASE WHEN n.priority = 'high' THEN 1 ELSE 0 END) > 0 THEN 'high'
            ELSE 'normal'
        END AS priority,
        COUNT(*) AS cnt,
        MAX(n.timestamp) AS last_item_at,
        CASE WHEN SUM(n.is_read) = COUNT(*) THEN 1 ELSE 0 END AS is_read,
        MIN(n.created_at) AS created_at
    FROM notification n
    WHERE n.is_active = 1
    GROUP BY n.user_id, CONCAT('legacy:', n.category, ':', DATE(n.timestamp)), n.category
) sub;

-- Insert items for migrated groups
INSERT INTO notif_item (group_id, user_id, message, type, priority, icon, link, metadata_json, timestamp)
SELECT
    ng.id,
    n.user_id,
    n.message,
    n.type,
    n.priority,
    n.icon,
    n.link,
    n.metadata_json,
    n.timestamp
FROM notification n
INNER JOIN notif_group ng
    ON ng.user_id = n.user_id
    AND ng.group_key = CONCAT('legacy:', n.category, ':', DATE(n.timestamp))
WHERE n.is_active = 1;

-- Add digest preferences columns to user_notification_preference
-- (MySQL 5.7 doesn't support IF NOT EXISTS for ADD COLUMN, so we use a workaround)

SET @dbname = DATABASE();
SET @tablename = 'user_notification_preference';
SET @column1 = 'digest_enabled';
SET @column2 = 'digest_channel';

SELECT COUNT(*) INTO @col1exists FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @column1;
SET @sql1 = IF(@col1exists = 0,
    'ALTER TABLE user_notification_preference ADD COLUMN digest_enabled BOOLEAN NOT NULL DEFAULT 1',
    'SELECT 1');
PREPARE stmt1 FROM @sql1;
EXECUTE stmt1;
DEALLOCATE PREPARE stmt1;

SELECT COUNT(*) INTO @col2exists FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @column2;
SET @sql2 = IF(@col2exists = 0,
    'ALTER TABLE user_notification_preference ADD COLUMN digest_channel VARCHAR(20) NOT NULL DEFAULT \'both\'',
    'SELECT 1');
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;
