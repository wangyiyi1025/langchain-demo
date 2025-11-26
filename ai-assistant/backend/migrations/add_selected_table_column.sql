-- 为conversations表添加selected_table字段
-- 执行方法:
--   mysql -u root -p smart_chat_bi_meta < migrations/add_selected_table_column.sql
-- 或者在MySQL命令行中执行:
--   USE smart_chat_bi_meta;
--   source migrations/add_selected_table_column.sql;

USE smart_chat_bi_meta;

-- 检查字段是否已存在，如果不存在则添加
SET @dbname = 'smart_chat_bi_meta';
SET @tablename = 'conversations';
SET @columnname = 'selected_table';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  "SELECT 'Column already exists, skipping...' AS message;",
  "ALTER TABLE conversations ADD COLUMN selected_table TEXT NULL COMMENT '选中的表信息（JSON格式）' AFTER title;"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
