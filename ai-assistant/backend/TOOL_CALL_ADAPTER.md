# Tool Call 适配器使用说明

## ⚠️ 重要提示

这是一个**临时解决方案**，用于兼容不完全支持 OpenAI Tool Calling 格式的模型。

**强烈建议**：生产环境应使用原生支持 Tool Calling 的模型，如：
- `qwen2.5:7b` / `qwen2.5:14b` / `qwen2.5:32b`
- `llama3.1:8b`
- `mistral:7b`

---

## 📋 适配器功能

Tool Call 适配器可以将模型输出的 **XML 格式工具调用** 转换为 **OpenAI 标准格式**。

### 支持的输入格式

```xml
<tool_call>{"name": "get_schema_info", "arguments": {"database": "chatbi_data", "table": "salary_tracking"}}</tool_call>
```

### 输出格式（OpenAI 标准）

```json
{
  "tool_calls": [
    {
      "id": "call_abc123...",
      "type": "function",
      "function": {
        "name": "get_schema_info",
        "arguments": "{\"database\": \"chatbi_data\", \"table\": \"salary_tracking\"}"
      }
    }
  ]
}
```

---

## 🚀 使用方法

### 步骤 1: 启用适配器

编辑 `.env` 文件，设置：

```bash
USE_TOOL_CALL_ADAPTER=true
```

### 步骤 2: 重启服务

```bash
# 停止当前服务（Ctrl+C）
# 重新启动
python -m uvicorn app.main:app --reload
```

### 步骤 3: 验证配置

启动时查看日志，应该看到：

```
============================================================
大模型配置 (OpenAI兼容接口):
  提供商: ollama
  ...
  Tool Call 适配器: 启用 (临时方案)
------------------------------------------------------------
```

以及：

```
LLM实例初始化成功（使用适配器）: provider=ollama, model=qwen-72b-w8a16, ...
```

---

## 🔍 工作原理

### 处理流程

```
1. 模型输出 XML 格式：
   <tool_call>{"name": "get_schema", ...}</tool_call>

2. 适配器拦截输出

3. 解析 XML，提取工具调用信息

4. 转换为 OpenAI 标准格式

5. 注入到 AIMessage.tool_calls

6. LangChain Agent 执行工具
```

### 核心代码

位于 `app/utils/tool_call_adapter.py`：

- `ToolCallAdapter` 类：继承自 `ChatOpenAI`
- `_parse_xml_tool_calls()` 方法：解析 XML 格式
- `_generate()` 方法：重写输出处理逻辑

---

## ⚙️ 配置选项

### 全局配置（`.env`）

```bash
# 启用/禁用适配器
USE_TOOL_CALL_ADAPTER=true  # 启用
USE_TOOL_CALL_ADAPTER=false # 禁用（默认）
```

### 代码配置

如需更精细的控制，可以直接导入：

```python
from app.utils.tool_call_adapter import create_adapted_llm

llm = create_adapted_llm(
    model="qwen-72b-w8a16",
    base_url="http://localhost:11434/v1",
    api_key="sk-dummy-key",
    temperature=0.7,
    max_tokens=2000
)
```

---

## 🧪 测试和调试

### 查看日志

启用 `DEBUG=True` 和 `AGENT_VERBOSE=True` 可以看到详细的处理过程：

```
检测到 XML 格式的工具调用，开始解析...
成功解析工具调用: get_schema_info
成功转换 1 个工具调用为 OpenAI 格式
```

### 测试脚本

运行测试验证适配器是否工作：

```bash
python test_tool_calling.py
```

---

## 🐛 已知问题和限制

### 1. 解析可能失败

**原因**：
- 模型输出格式不一致
- JSON 格式错误
- XML 标签嵌套问题

**解决**：
- 查看错误日志
- 尝试调整模型参数（temperature）
- 考虑切换到原生支持的模型

### 2. 性能开销

**影响**：
- 每次调用增加 XML 解析开销（通常 <5ms）
- 正则表达式匹配成本

**建议**：
- 对于高并发场景，使用原生支持的模型

### 3. 维护成本

**问题**：
- 不同模型可能有不同的输出格式
- LangChain 更新可能导致兼容性问题
- 需要持续维护和测试

**建议**：
- 将此作为临时过渡方案
- 制定迁移到原生模型的计划

---

## 📊 性能对比

| 方案 | 响应时间 | 可靠性 | 维护成本 | 推荐度 |
|------|---------|--------|---------|--------|
| 原生 Tool Calling (qwen2.5:14b) | 快 | 高 | 低 | ⭐⭐⭐⭐⭐ |
| Tool Call 适配器 | 中等 | 中 | 高 | ⭐⭐ |
| ReAct Agent | 慢 | 中 | 中 | ⭐⭐⭐ |

---

## 🔄 迁移到原生模型

### 推荐迁移步骤

**1. 准备阶段**
```bash
# 拉取推荐模型
ollama pull qwen2.5:14b
```

**2. 测试阶段**
```bash
# 在 .env 中临时切换
LLM_MODEL=qwen2.5:14b
USE_TOOL_CALL_ADAPTER=false

# 重启并测试
python -m uvicorn app.main:app --reload
```

**3. 验证阶段**
- 运行测试脚本：`python test_tool_calling.py`
- 测试实际业务场景
- 对比响应速度和质量

**4. 正式切换**
- 更新生产环境配置
- 监控日志和错误率
- 准备回滚方案

---

## 🛠️ 故障排除

### 问题 1: 适配器启用但工具仍未执行

**检查**：
1. 确认 `.env` 中 `USE_TOOL_CALL_ADAPTER=true`
2. 查看启动日志是否显示"使用适配器"
3. 检查模型是否真的输出 `<tool_call>` 标签

**解决**：
```bash
# 查看详细日志
tail -f logs/app.log | grep -E "(tool_call|适配器)"
```

### 问题 2: 解析失败

**现象**：
```
解析工具调用 JSON 失败: <content>, 错误: <error>
```

**原因**：
- 模型输出的 JSON 格式不正确
- XML 标签内容被截断

**解决**：
1. 增加 `LLM_MAX_TOKENS`（如 3000）
2. 降低 `LLM_TEMPERATURE`（如 0.5）
3. 尝试其他模型

### 问题 3: 性能下降

**现象**：
- 响应时间明显增加
- 资源占用上升

**解决**：
1. 监控适配器处理时间
2. 考虑切换到更小的模型（如 qwen2.5:7b）
3. 或切换到原生支持的模型

---

## 📞 技术支持

### 日志分析

启用详细日志以便排查：

```bash
# .env
DEBUG=True
AGENT_VERBOSE=True
LOG_LEVEL=DEBUG
```

### 相关文件

- 适配器实现：`app/utils/tool_call_adapter.py`
- 配置文件：`app/config.py`
- LLM 初始化：
  - `app/tools/chatbi_tools_atomic.py:368-398`
  - `app/agents/chatbi_agent.py:44-70`

### 参考文档

- [LLM_CONFIG.md](./LLM_CONFIG.md) - LLM 配置指南
- [TOOL_CALLING_FIX.md](./TOOL_CALLING_FIX.md) - Tool Calling 问题修复
- [test_tool_calling.py](./test_tool_calling.py) - 测试脚本

---

## 📝 更新日志

### 2025-11-28
- ✅ 初始版本实现
- ✅ 支持 XML 格式解析
- ✅ 集成到 Agent 和工具系统
- ✅ 添加配置开关

---

## ⚠️ 最后提醒

**这是临时方案！** 请尽快迁移到原生支持 Tool Calling 的模型：

```bash
# 推荐配置
ollama pull qwen2.5:14b
```

```bash
# .env
LLM_MODEL=qwen2.5:14b
USE_TOOL_CALL_ADAPTER=false  # 禁用适配器
```

**好处**：
- ✅ 更快的响应速度
- ✅ 更高的可靠性
- ✅ 零维护成本
- ✅ 官方支持

祝使用愉快！如有问题，请查看日志并参考故障排除章节。
