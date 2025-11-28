# ChatBI 架构重构文档

## 📋 重构概述

本次重构采用**职责分离 + 原子工具 + 上下文传递**的设计模式，解决了之前架构中的以下问题：

### ❌ 旧架构的问题

1. **双重意图理解**：Agent层和Tool层都在理解用户业务需求（同比、环比等）
2. **Prompt工程重复**：业务逻辑在两处定义，维护成本高，容易不一致
3. **职责混乱**：chatbi_query是一个"工具"，但内部包含完整的分析流程（3次LLM调用）
4. **难以扩展**：添加新功能需要同时修改Agent和Tool的prompt

### ✅ 新架构的优势

1. **职责清晰**：Agent只做编排，nl_to_sql只做业务理解，其他工具单一职责
2. **易维护**：所有业务逻辑（同比/环比）**只在一处**定义（nl_to_sql工具）
3. **可测试**：每个工具独立测试，接口明确
4. **可扩展**：添加新工具不影响现有代码
5. **消除歧义**：只有nl_to_sql理解用户意图，Agent不会"优化"问题

---

## 🏗️ 新架构设计

```
┌─────────────────────────────────────────────────┐
│  ChatBI Agent (编排层)                           │
│  - 任务拆解和工作流编排                            │
│  - 不理解业务细节（不知道什么是同比、环比）         │
│  - 管理上下文在工具间传递                          │
└─────────────────────────────────────────────────┘
                       ↓
        调用原子工具，传递上下文
                       ↓
┌─────────────────────────────────────────────────┐
│  原子工具层 (chatbi_tools_atomic.py)             │
│  ├─ get_schema_info      获取表结构 (无LLM)      │
│  ├─ nl_to_sql           NL→SQL (有LLM) ⭐️       │
│  ├─ execute_sql         执行SQL (无LLM)          │
│  ├─ analyze_data        分析数据 (有LLM)         │
│  ├─ suggest_chart       推荐图表 (有LLM)         │
│  └─ generate_chart_config 生成配置 (无LLM)      │
└─────────────────────────────────────────────────┘
```

---

## 🔧 原子工具详解

### 1. get_schema_info
- **职责**：获取数据库表结构
- **LLM调用**：❌ 无
- **输入**：database, table (可选)
- **输出**：JSON格式的schema信息
- **替代**：chatbi_get_schema (已弃用)

### 2. nl_to_sql ⭐️ 唯一业务理解点
- **职责**：将自然语言转换为SQL
- **LLM调用**：✅ 是
- **业务知识**：包含所有同比、环比、同期等业务逻辑
- **输入**：question, schema_info, context
- **输出**：JSON格式，包含sql, explanation

### 3. execute_sql
- **职责**：执行SQL查询
- **LLM调用**：❌ 无
- **输入**：sql, database
- **输出**：JSON格式的查询结果

### 4. analyze_data
- **职责**：分析查询结果，提供洞察
- **LLM调用**：✅ 是
- **输入**：data, question
- **输出**：JSON格式的分析结果

### 5. suggest_chart
- **职责**：推荐图表类型
- **LLM调用**：✅ 是
- **输入**：data, question, analysis (可选)
- **输出**：JSON格式的图表推荐

### 6. generate_chart_config
- **职责**：生成前端图表配置
- **LLM调用**：❌ 无
- **输入**：data, chart_suggestion
- **输出**：JSON格式的图表配置

---

## 🔄 标准工作流程

### 完整流程（查询 + 可视化）

```python
# Step 1: 获取当前时间
time_info = get_current_time()

# Step 2: 获取表结构
schema_result = get_schema_info(database="sales_db", table="products")
schema_info = json.loads(schema_result)["schema_info"]

# Step 3: 生成SQL（唯一业务理解点）
sql_result = nl_to_sql(
    question="2025年销售额同期同比增长最多的产品前五",  # 原样传递，不修改
    schema_info=schema_info,
    context=time_info
)
sql_data = json.loads(sql_result)

# Step 4: 执行SQL
query_result = execute_sql(
    sql=sql_data["sql"],
    database="sales_db"
)
query_data = json.loads(query_result)

# Step 5: 分析数据
analysis_result = analyze_data(
    data=query_result,  # 传递JSON字符串
    question="2025年销售额同期同比增长最多的产品前五"
)

# Step 6: 推荐图表
chart_suggestion = suggest_chart(
    data=query_result,
    question="2025年销售额同期同比增长最多的产品前五",
    analysis=analysis_result
)

# Step 7: 生成图表配置
chart_config = generate_chart_config(
    data=query_result,
    chart_suggestion=chart_suggestion
)
```

---

## 📊 对比：旧 vs 新

| 维度 | 旧架构 | 新架构 |
|------|--------|--------|
| **Agent职责** | 理解业务 + 编排工具 | 只编排工具 |
| **业务逻辑位置** | Agent Prompt + Tool Prompt | 只在nl_to_sql工具 |
| **工具粒度** | chatbi_query（复合工具，3次LLM） | 6个原子工具 |
| **Prompt维护** | 两处（Agent + Tool） | 一处（nl_to_sql） |
| **可测试性** | 难（复合逻辑） | 易（每个工具独立） |
| **扩展性** | 低（需改多处） | 高（添加新工具） |
| **上下文传递** | 隐式 | 显式（JSON字符串） |

---

## 🔧 迁移指南

### 文件变更

```
新增：
✅ chatbi_tools_atomic.py - 所有原子工具

修改：
🔄 chatbi_agent.py - 简化prompt，移除业务逻辑
🔄 chatbi_tool.py - 标记为DEPRECATED，保留向后兼容
```

### Prompt变更

#### Agent Prompt（chatbi_agent.py）

**删除的内容**：
- ❌ 所有业务知识（同比、环比、同期定义）
- ❌ 时间对比分析说明
- ❌ SQL生成规则
- ❌ 数据分析指导

**新增的内容**：
- ✅ 工作流程编排说明
- ✅ 工具调用顺序
- ✅ 上下文传递规则
- ✅ 明确"不要修改用户问题"

#### nl_to_sql Prompt（chatbi_tools_atomic.py）

**包含的内容**：
- ✅ 所有业务知识（TIME_PERIOD_ANALYSIS_KNOWLEDGE）
- ✅ SQL生成规则
- ✅ 时间对比分析处理逻辑
- ✅ 典型场景SQL模板

---

## 📝 使用示例

### 示例1: Agent调用原子工具

用户问题："2025年销售额同期同比增长最多的产品前五"

Agent执行流程：
1. 识别需要数据查询 + 可视化
2. 调用 get_current_time()
3. 调用 get_schema_info(database="sales_db", table="products")
4. 调用 nl_to_sql，**原样传递**用户问题
5. nl_to_sql理解"同期同比"，生成正确的SQL
6. 调用 execute_sql 执行查询
7. 调用 analyze_data 分析数据
8. 调用 suggest_chart 推荐图表（可能推荐柱状图）
9. 调用 generate_chart_config 生成配置
10. 整合所有结果返回给用户

**关键点**：
- Agent不理解"同期同比"是什么意思
- Agent只知道标准流程：get_schema → nl_to_sql → execute_sql → ...
- 业务理解完全由nl_to_sql处理

---

## 🎯 核心设计原则

### 1. 单一职责原则
每个工具只做一件事，接口明确

### 2. 业务逻辑集中
所有业务理解（同比、环比、SQL生成）**只在nl_to_sql**

### 3. Agent只编排
Agent不理解业务术语，只知道调用顺序

### 4. 明确数据流
工具间通过结构化的JSON传递数据

### 5. 消除歧义
只有一个地方理解用户意图（nl_to_sql）

---

## 🚀 后续优化方向

1. **QueryContext对象**：
   - 当前已定义但未强制使用
   - 可以用dataclass规范化工具间传递的数据结构

2. **工具组合器**：
   - 创建预定义的工具链（如"查询+可视化链"）
   - 减少Agent编排的复杂度

3. **中间结果缓存**：
   - 缓存schema_info避免重复查询
   - 缓存时间信息

4. **错误恢复机制**：
   - 某个工具失败时的fallback策略
   - 自动重试逻辑

---

## 📞 常见问题

### Q1: 旧的chatbi_query还能用吗？
**A**: 可以，已标记为DEPRECATED但保留向后兼容。建议尽快迁移到新架构。

### Q2: 如果只想查询数据，不需要可视化怎么办？
**A**: Agent会智能判断，只执行Step 1-4，跳过分析和可视化步骤。

### Q3: 如何添加新的分析功能？
**A**: 创建新的原子工具，在Agent的工具列表中注册即可，不需要修改现有代码。

### Q4: nl_to_sql工具太重了，能不能拆分？
**A**: 不建议。nl_to_sql是**唯一的业务理解点**，这是设计核心。拆分会导致业务逻辑分散。

### Q5: Agent会不会调用工具顺序错误？
**A**: Agent的prompt中有明确的标准流程，LLM会按照流程执行。如果出现问题，可以在prompt中强化流程说明。

---

## 📄 相关文件

- `chatbi_tools_atomic.py` - 新的原子工具实现
- `chatbi_agent.py` - 重构后的Agent（编排层）
- `chatbi_tool.py` - 旧工具（DEPRECATED）
- `CHATBI_REFACTOR.md` - 本文档

---

**最后更新**: 2025-11-28
**版本**: v2.0 - 职责分离架构
