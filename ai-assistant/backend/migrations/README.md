# 数据库迁移脚本

本目录包含数据库schema变更的SQL迁移脚本。

## 使用方法

### 方式1：MySQL命令行

```bash
# 进入MySQL命令行
mysql -u root -p

# 在MySQL命令行中执行
USE smart_chat_bi_meta;
source migrations/add_selected_table_column.sql;
```

### 方式2：直接执行SQL文件

```bash
mysql -u root -p smart_chat_bi_meta < migrations/add_selected_table_column.sql
```

## 迁移脚本列表

### add_selected_table_column.sql

**作用**: 为conversations表添加selected_table字段

**字段说明**:
- `selected_table` TEXT NULL - 存储用户在对话中选中的数据表信息（JSON格式）

**JSON格式示例**:
```json
{
  "database": "chatbi_data",
  "table": "salary_tracking",
  "comment": "银保满薪追踪表"
}
```

**注意事项**:
- 该脚本会自动检查字段是否已存在，避免重复添加
- 对已有的对话数据不会产生影响
- 新建的对话selected_table字段默认为NULL

## 验证迁移

执行以下SQL验证迁移是否成功：

```sql
USE smart_chat_bi_meta;
DESCRIBE conversations;
```

应该能看到conversations表包含selected_table字段。
