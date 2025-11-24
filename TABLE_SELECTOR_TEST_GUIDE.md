# 表选择器测试和调试指南

## 🔧 已修复的问题

### 1. 点击数据库后自动显示表
**问题**: 点击数据库后，没有自动显示该数据库下的表

**修复**: 现在点击数据库后，会立即显示该数据库下的所有表

### 2. 改进搜索逻辑
**问题**: 搜索逻辑不够智能

**修复**:
- 输入 `#` → 显示所有数据库
- 输入 `#detail` → 显示匹配的数据库
- 输入 `#detail.` → 显示detail数据库的所有表
- 输入 `#detail.user` → 显示匹配的表

### 3. 添加调试日志
在后端添加了详细的日志，帮助诊断问题

## 🧪 测试步骤

### 1. 重启后端服务

```bash
cd ai-assistant/backend
python app/main.py
```

**观察后端输出**，应该看到：
```
已注册Agent: 通用聊天助手 (类型: chat)
已注册Agent: ChatBI数据分析助手 (类型: chatbi)
```

### 2. 测试数据库连接

在浏览器中访问：
```
http://localhost:8000/api/v1/database/metadata
```

**应该返回**类似这样的JSON：
```json
{
  "detail": ["table1", "table2", "table3"],
  "test_db": ["users", "orders"],
  "...": ["..."]
}
```

**如果只返回一个数据库**，说明：
- 你的Starrocks数据库中确实只有一个用户数据库
- 或者数据库连接配置需要调整

### 3. 查看后端日志

当访问数据库API时，后端控制台应该输出：
```
数据库查询返回结果数: 6
所有数据库: ['detail', 'information_schema', 'mysql', 'performance_schema', 'sys', '_statistics_']
过滤后的用户数据库: ['detail']
数据库 detail 的表查询返回结果数: 5
数据库 detail 的表列表: ['table1', 'table2', 'table3', 'table4', 'table5']
```

### 4. 重启前端服务

```bash
cd ai-assistant/frontend
npm run dev
```

### 5. 测试表选择器

#### 测试场景1: 显示所有数据库
1. 切换到"ChatBI数据分析助手"
2. 在表选择器中输入 `#`
3. **预期结果**: 下拉框显示所有可用数据库

#### 测试场景2: 点击数据库显示表
1. 输入 `#`
2. 点击某个数据库（如 detail）
3. **预期结果**: 输入框变为 `#detail.`，下拉框自动显示该数据库的所有表

#### 测试场景3: 搜索表
1. 输入 `#detail.user`
2. **预期结果**: 下拉框显示所有包含"user"的表

#### 测试场景4: 选择表
1. 点击某个表
2. **预期结果**:
   - 输入框显示 `#detail.table_name`
   - 下拉框关闭
   - 出现蓝色的上下文提示条
   - 聊天区显示"已选择表"的消息

## 🐛 调试数据库问题

### 问题: 只显示一个数据库

**可能原因1: 数据库中确实只有一个用户数据库**

验证：
```bash
# 连接到Starrocks
mysql -h 127.0.0.1 -P 9030 -u admin -p

# 查看所有数据库
SHOW DATABASES;
```

**可能原因2: 数据库连接配置不正确**

检查 `ai-assistant/backend/app/services/database_service.py`:
```python
def __init__(
    self,
    host: str = "127.0.0.1",  # ← 检查这个
    port: int = 9030,          # ← 检查这个
    user: str = "admin",       # ← 检查这个
    password: str = "123456"   # ← 检查这个
):
```

**可能原因3: 系统数据库过滤太严格**

检查 `database_service.py` 第78行：
```python
system_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys', '_statistics_'}
```

如果你的数据库名字在这个列表中，它会被过滤掉。

### 问题: 数据库连接失败

**检查后端日志**，如果看到：
```
数据库连接失败: ...
```

**解决方案**:
1. 确认Starrocks服务正在运行
2. 确认端口9030可访问
3. 确认用户名密码正确
4. 检查防火墙设置

### 问题: 表列表为空

**检查后端日志**，如果看到：
```
数据库 detail 的表查询返回结果数: 0
数据库 detail 的表列表: []
```

**可能原因**:
1. 数据库确实没有表
2. 用户没有权限查看表

**验证**:
```sql
USE detail;
SHOW TABLES;
```

## 📊 API测试命令

### 获取所有数据库
```bash
curl http://localhost:8000/api/v1/database/databases
```

### 获取指定数据库的表
```bash
curl http://localhost:8000/api/v1/database/databases/detail/tables
```

### 获取所有元数据
```bash
curl http://localhost:8000/api/v1/database/metadata
```

### 搜索表
```bash
curl "http://localhost:8000/api/v1/database/search/tables?keyword=user"
```

## 🎯 预期行为

### 正常情况下的工作流程

1. **用户输入 `#`**
   - 前端显示所有数据库
   - 后端日志显示查询结果

2. **用户点击数据库**
   - 输入框更新为 `#database.`
   - 自动显示该数据库的所有表
   - 不需要再次输入

3. **用户点击表**
   - 输入框显示完整路径
   - 下拉框关闭
   - 显示上下文提示条
   - 可以开始查询

4. **用户开始提问**
   - "统计用户数量"
   - "查询最近的订单"
   - 等等...

## 🔍 常见问题

### Q: 为什么只显示一个数据库？
A:
1. 检查后端日志，确认实际有多少数据库
2. 检查数据库连接配置
3. 确认Starrocks中确实有多个数据库

### Q: 为什么点击数据库后没有显示表？
A: 已修复！现在点击数据库会立即显示所有表

### Q: 如何修改数据库连接配置？
A: 编辑 `ai-assistant/backend/app/services/database_service.py`，修改构造函数的默认参数

### Q: 如何添加环境变量配置？
A: 可以在 `config.py` 中添加数据库配置，然后在 `.env` 文件中设置

## 📝 下一步改进建议

1. **配置化数据库连接**
   - 将数据库配置移到 `.env` 文件
   - 支持配置多个数据库

2. **缓存元数据**
   - 添加Redis缓存
   - 定期刷新元数据

3. **更智能的搜索**
   - 支持拼音搜索
   - 支持模糊匹配

4. **UI改进**
   - 添加加载状态
   - 添加错误提示
   - 支持键盘快捷键

---

**最后更新**: 2024年
**Git Commit**: c2f5ded
