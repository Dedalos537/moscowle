-- Fix 1: Add is_read to notif_item
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'moscowle_prod' AND TABLE_NAME = 'notif_item' AND COLUMN_NAME = 'is_read');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE notif_item ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Fix 2: Add digest_enabled and digest_channel to user_notification_preference
SET @col1 = (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'moscowle_prod' AND TABLE_NAME = 'user_notification_preference' AND COLUMN_NAME = 'digest_enabled');
SET @sql1 = IF(@col1 = 0,
    'ALTER TABLE user_notification_preference ADD COLUMN digest_enabled BOOLEAN NOT NULL DEFAULT 1',
    'SELECT 1');
PREPARE stmt1 FROM @sql1;
EXECUTE stmt1;
DEALLOCATE PREPARE stmt1;

SET @col2 = (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'moscowle_prod' AND TABLE_NAME = 'user_notification_preference' AND COLUMN_NAME = 'digest_channel');
SET @sql2 = IF(@col2 = 0,
    "ALTER TABLE user_notification_preference ADD COLUMN digest_channel VARCHAR(20) NOT NULL DEFAULT 'both'",
    'SELECT 1');
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;
