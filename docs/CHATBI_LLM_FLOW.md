# ChatBI Agent LLM调用流程说明文档

## 目录
1. [整体架构](#整体架构)
2. [LLM调用点说明](#llm调用点说明)
3. [完整调用流程](#完整调用流程)
4. [日志格式说明](#日志格式说明)
5. [优化建议](#优化建议)

---

## 整体架构

ChatBI Agent 是一个基于 LangChain 的智能数据分析代理，使用了两层 LLM 调用架构：

```
用户请求
    ↓
[第1层] ChatBIAgent (ReAct Agent)
    ├── LLM: 通义千问 (qwen-plus)
    ├── 作用：理解用户意图，决定调用哪个工具
    ├── 工具1: chatbi_query
    └── 工具2: chatbi_get_schema
         ↓
[第2层] ChatBIAnalyzer (工具内部的LLM调用)
    ├── LLM调用1: natural_language_to_sql
    │   ├── 模型：通义千问 (qwen-plus)
    │   ├── Temperature: 0.1
    │   └── 作用：将自然语言转换为SQL
    └── LLM调用2: analyze_data_and_suggest_chart
        ├── 模型：通义千问 (qwen-plus)
        ├── Temperature: 0.1
        └── 作用：分析数据并建议图表类型
```

---

## LLM调用点说明

### 1. ChatBIAgent (第1层 - Agent层)

**文件**: `ai-assistant/backend/app/agents/chatbi_agent.py`

**类**: `ChatBIAgent`

**LLM配置**:
```python
ChatTongyi(
    model=os.getenv("QWEN_MODEL", "qwen-plus"),
    temperature=float(os.getenv("QWEN_TEMPERATURE", "0.3")),
    max_tokens=int(os.getenv("QWEN_MAX_TOKENS", "2000"))
)
```

**执行方法**: `invoke()`

**作用**:
- 接收用户的自然语言查询
- 理解用户意图（是要查询数据还是查看schema）
- 决定调用哪个工具（chatbi_query 或 chatbi_get_schema）
- 根据工具返回结果生成最终回复

**日志格式**:
```
====================================================================================================
[chatbi_agent.py::ChatBIAgent::invoke] Agent执行开始
====================================================================================================
【请求】用户消息: 查询今年3月的销售额同比增长
【请求】增强消息: #sales_db.orders 查询今年3月的销售额同比增长
【请求】对话历史条数: 0
【响应】Agent返回:
好的，我已经查询到了2024年3月的销售额同比数据...
[chatbi_agent.py::ChatBIAgent::invoke] Agent执行完成
====================================================================================================
```

---

### 2. ChatBIAnalyzer - natural_language_to_sql (第2层 - 工具层)

**文件**: `ai-assistant/backend/app/tools/chatbi_tool.py`

**类**: `ChatBIAnalyzer`

**方法**: `natural_language_to_sql()`

**LLM配置**:
```python
ChatTongyi(
    model=settings.QWEN_MODEL,
    temperature=0.1,  # 较低的温度以获得更准确的SQL
    max_tokens=2000
)
```

**作用**:
- 接收用户的自然语言问题和数据库Schema信息
- 将自然语言转换为可执行的SQL查询语句
- 支持同比、环比等时间对比分析

**日志格式**:
```
====================================================================================================
[chatbi_tool.py::ChatBIAnalyzer::natural_language_to_sql] LLM调用开始
====================================================================================================
【请求】用户问题: 查询今年3月的销售额同比增长
【请求】Schema信息:
数据库: sales_db
表名: orders
完整表名: sales_db.orders
表说明: 订单表

字段信息:
  - order_id: int (不允许NULL, 键类型: PRI) // 订单ID
  - order_amount: decimal(10,2) (允许NULL) // 订单金额
  - order_date: datetime (允许NULL) // 订单日期

【响应】LLM原始返回:
SELECT
    DATE_FORMAT(order_date, '%Y-%m') as month,
    SUM(order_amount) as total_amount
FROM sales_db.orders
WHERE DATE_FORMAT(order_date, '%Y-%m') IN ('2024-03', '2023-03')
GROUP BY DATE_FORMAT(order_date, '%Y-%m')

【结果】提取的SQL: SELECT DATE_FORMAT(order_date, '%Y-%m') as month...
[chatbi_tool.py::ChatBIAnalyzer::natural_language_to_sql] LLM调用完成
====================================================================================================
```

---

### 3. ChatBIAnalyzer - analyze_data_and_suggest_chart (第2层 - 工具层)

**文件**: `ai-assistant/backend/app/tools/chatbi_tool.py`

**类**: `ChatBIAnalyzer`

**方法**: `analyze_data_and_suggest_chart()`

**LLM配置**: 同 natural_language_to_sql

**作用**:
- 接收查询结果数据和用户问题
- 分析数据特征（列类型、数值范围、分类数量等）
- 建议最合适的图表类型（柱状图、折线图、饼图等）

**日志格式**:
```
====================================================================================================
[chatbi_tool.py::ChatBIAnalyzer::analyze_data_and_suggest_chart] LLM调用开始
====================================================================================================
【请求】用户问题: 查询今年3月的销售额同比增长
【请求】数据列名: month, total_amount
【请求】数据行数: 2
【请求】数据统计:
month: 分类型, 2 个不同值
total_amount: 数值型, 范围 45000.00 - 52000.00

【响应】LLM原始返回:
{
    "chart_type": "bar",
    "reason": "柱状图适合对比两个时间段的数值差异",
    "x_axis": "month",
    "y_axis": "total_amount",
    "title": "2024年3月与2023年3月销售额对比"
}

【结果】图表建议: {
  "chart_type": "bar",
  "reason": "柱状图适合对比两个时间段的数值差异",
  ...
}
[chatbi_tool.py::ChatBIAnalyzer::analyze_data_and_suggest_chart] LLM调用完成
====================================================================================================
```

---

## 完整调用流程

### 典型场景：用户查询"查询今年3月的销售额同比增长"

```
步骤1: 用户请求进入 ChatBIAgent
    ↓
    日志: [chatbi_agent.py::ChatBIAgent::invoke] Agent执行开始
    ↓
步骤2: ChatBIAgent 的 LLM 决策（LLM调用#1）
    - 输入：用户消息 + 系统提示词（包含工具说明）
    - 输出：决定调用 chatbi_query 工具
    ↓
步骤3: 执行 chatbi_query 工具
    ↓
    3.1: 获取数据库Schema信息
         - 如果指定了 database 和 table：获取单表schema
         - 否则：获取整个数据库或所有数据库schema
    ↓
    日志: [chatbi_tool.py::ChatBIAnalyzer::natural_language_to_sql] LLM调用开始
    ↓
    3.2: 调用 natural_language_to_sql（LLM调用#2）
         - 输入：用户问题 + Schema信息
         - 输出：SQL查询语句
    ↓
    3.3: 执行SQL查询，获取数据
    ↓
    日志: [chatbi_tool.py::ChatBIAnalyzer::analyze_data_and_suggest_chart] LLM调用开始
    ↓
    3.4: 调用 analyze_data_and_suggest_chart（LLM调用#3）
         - 输入：查询结果数据 + 用户问题
         - 输出：图表建议（JSON格式）
    ↓
    3.5: 生成图表配置
    ↓
    3.6: 返回完整结果（包含SQL、数据、图表建议）
    ↓
步骤4: ChatBIAgent 接收工具返回结果（LLM调用#4，可能）
    - 输入：工具返回的JSON
    - 输出：格式化的用户友好回复
    ↓
    日志: [chatbi_agent.py::ChatBIAgent::invoke] Agent执行完成
    ↓
步骤5: 返回最终结果给用户
```

### LLM调用次数统计

一次完整的查询请求，可能涉及的LLM调用：

| 调用点 | 位置 | 作用 | 是否必须 |
|--------|------|------|----------|
| Agent决策 | ChatBIAgent | 决定调用哪个工具 | 是 |
| 生成SQL | ChatBIAnalyzer::natural_language_to_sql | 自然语言转SQL | 是（如果调用chatbi_query） |
| 分析图表 | ChatBIAnalyzer::analyze_data_and_suggest_chart | 建议图表类型 | 是（如果调用chatbi_query） |
| 格式化回复 | ChatBIAgent | 生成用户友好回复 | 可能（如果需要） |

**典型场景**: 3-4次LLM调用

---

## 日志格式说明

### 日志层级

- **INFO**: LLM调用的请求和响应
- **ERROR**: 错误信息
- **DEBUG**: 详细的调试信息（默认不输出）

### 日志标识格式

```
[文件名::类名::方法名]
```

示例：
- `[chatbi_agent.py::ChatBIAgent::invoke]`
- `[chatbi_tool.py::ChatBIAnalyzer::natural_language_to_sql]`
- `[chatbi_tool.py::ChatBIAnalyzer::analyze_data_and_suggest_chart]`

### 日志内容标记

- **【请求】**: 发送给LLM的输入数据
- **【响应】**: LLM返回的原始结果
- **【结果】**: 处理后的最终结果
- **【错误】**: 错误信息

---

## 优化建议

### 1. 减少LLM调用次数

**当前问题**: 一次查询可能需要3-4次LLM调用

**优化方案**:
- 考虑将"生成SQL"和"分析图表"合并为一次LLM调用
- 使用更强大的提示词，让LLM一次性返回SQL和图表建议

### 2. 缓存Schema信息

**当前问题**: 每次查询都需要重新获取Schema

**优化方案**:
- 实现Schema缓存机制（TTL: 10分钟）
- 减少数据库查询次数

### 3. 优化Token使用

**当前问题**: Schema信息可能很大，消耗大量Token

**优化方案**:
- 只获取相关表的Schema（已实现）
- 过滤不必要的字段信息
- 使用更简洁的Schema格式

### 4. 监控LLM调用

**建议**:
- 记录每次LLM调用的Token消耗
- 统计平均响应时间
- 监控错误率

---

## 配置参数

### 环境变量

```bash
# 模型配置
QWEN_MODEL=qwen-plus  # 可选：qwen-turbo, qwen-max
QWEN_TEMPERATURE=0.3  # Agent层温度
QWEN_MAX_TOKENS=2000  # 最大Token数

# 日志配置
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/app.log
```

### 修改建议

- **开发环境**: `LOG_LEVEL=DEBUG` - 查看所有日志
- **生产环境**: `LOG_LEVEL=INFO` - 只看关键信息

---

## 常见问题

### Q1: 如何追踪单次请求的所有LLM调用？

A: 在日志中搜索相同的用户问题，会看到完整的调用链：
```bash
grep "查询今年3月的销售额" logs/app.log
```

### Q2: 如何统计LLM调用次数？

A: 在日志中统计"LLM调用开始"的次数：
```bash
grep "LLM调用开始" logs/app.log | wc -l
```

### Q3: 如何优化慢查询？

A:
1. 查看日志中的SQL语句
2. 检查Schema获取是否过慢
3. 优化数据库索引
4. 考虑限制返回数据量

---

## 更新日志

- **2025-11-27**: 初始版本，添加详细的LLM调用流程说明
