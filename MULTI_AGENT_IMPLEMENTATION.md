# 多Agent数据分析系统实现文档

## 项目概述

本项目实现了一个完整的多Agent智能助手系统，支持通用聊天和专业数据分析两种模式。

## 🎯 核心功能

### 1. 多Agent架构
- **通用聊天助手（ChatAgent）**: 处理日常对话、时间查询、计算、搜索等
- **ChatBI数据分析助手（ChatBIAgent）**: 专门用于数据库查询和数据分析

### 2. 表选择机制
- 使用 `#数据库名.表名` 格式选择数据表
- 智能下拉提示框，支持数据库和表的模糊搜索
- 键盘导航支持（上下箭头、Enter选择、Esc关闭）
- 实时展示可用的数据库和表

### 3. 表上下文管理
- 选择表后，所有对话自动基于该表进行分析
- 后续对话自动预先加上所选择的表信息
- 用户可以随时修改表
- 显示当前分析表的上下文提示条

## 📁 项目结构

### 后端结构
```
backend/app/
├── agents/                    # Agent层
│   ├── base_agent.py         # Agent基类
│   ├── agent_manager.py      # Agent管理器
│   ├── chat_agent.py         # 通用聊天Agent
│   └── chatbi_agent.py       # 数据分析Agent
├── services/                  # 服务层
│   ├── conversation_service.py  # 对话服务（支持多Agent）
│   └── database_service.py      # 数据库元数据服务
├── api/                       # API层
│   ├── chat.py               # 聊天API
│   ├── system.py             # 系统API
│   └── database.py           # 数据库API
├── tools/                     # 工具层
│   ├── chatbi_tool.py        # ChatBI工具
│   ├── time_tool.py          # 时间工具
│   ├── calculator_tool.py    # 计算工具
│   ├── search_tool.py        # 搜索工具
│   └── wangwei_info.py       # 自定义工具
├── models/                    # 数据模型
│   └── schemas.py            # Pydantic模型
└── config.py                 # 配置文件
```

### 前端结构
```
frontend/src/
├── components/
│   ├── AgentSelector.jsx     # Agent选择器
│   ├── TableSelector.jsx     # 表选择器（带下拉提示）
│   ├── ContextBar.jsx        # 上下文显示条
│   ├── ChatHeader.jsx        # 聊天头部
│   ├── ChatMessage.jsx       # 消息显示
│   ├── ChatInput.jsx         # 消息输入
│   └── TypingIndicator.jsx   # 输入指示器
├── assets/styles/
│   ├── AgentSelector.css
│   ├── TableSelector.css
│   ├── ContextBar.css
│   └── main.css
└── App.jsx                   # 主应用
```

## 🚀 启动指南

### 后端启动
```bash
cd ai-assistant/backend
python app/main.py
```
访问：http://localhost:8000
- API文档：http://localhost:8000/api/docs

### 前端启动
```bash
cd ai-assistant/frontend
npm install  # 首次运行
npm run dev
```
访问：http://localhost:5173

## 📝 使用流程

### 1. 选择Agent
在顶部Agent选择器中切换：
- **通用聊天助手**: 💬 图标
- **ChatBI数据分析助手**: 📊 图标

### 2. 选择数据表（仅ChatBI模式）
在表选择器中：
1. 输入 `#` - 显示所有数据库
2. 输入 `#test` - 显示匹配的数据库
3. 输入 `#test_db.` - 显示该数据库的所有表
4. 使用键盘或鼠标选择表

### 3. 开始对话
选择表后，所有对话都基于该表进行分析。可以提问如：
- "查询用户总数"
- "统计每天的订单量"
- "分析销售趋势"

### 4. 随时切换
可以随时：
- 切换Agent
- 修改分析表
- 清除对话历史

## 🔧 API端点

### 聊天相关
- `GET /api/v1/chat/agents` - 获取所有Agent列表
- `POST /api/v1/chat/message` - 同步聊天
- `WebSocket /api/v1/chat/ws/{session_id}` - 流式聊天
- `DELETE /api/v1/chat/clear/{session_id}` - 清除历史
- `POST /api/v1/chat/table-context/{session_id}` - 设置表上下文
- `GET /api/v1/chat/table-context/{session_id}` - 获取表上下文
- `DELETE /api/v1/chat/table-context/{session_id}` - 清除表上下文

### 数据库相关
- `GET /api/v1/database/databases` - 获取所有数据库
- `GET /api/v1/database/databases/{db}/tables` - 获取指定数据库的表
- `GET /api/v1/database/databases/{db}/tables/{table}/schema` - 获取表结构
- `GET /api/v1/database/metadata` - 获取所有元数据
- `GET /api/v1/database/search/tables?keyword=xxx` - 搜索表

### 系统相关
- `GET /api/v1/system/info` - 系统信息
- `GET /api/v1/system/health` - 健康检查
- `GET /api/v1/system/tools` - 工具列表

## 💡 关键实现

### 1. Agent基类设计
```python
class BaseAgent(ABC):
    @abstractmethod
    def get_agent_type(self) -> str: pass

    @abstractmethod
    def invoke(self, message: str, chat_history: List, **kwargs) -> str: pass

    @abstractmethod
    def stream(self, message: str, chat_history: List, **kwargs): pass
```

### 2. Agent管理器
```python
class AgentManager:
    def register_agent(self, agent: BaseAgent): ...
    def get_agent(self, agent_type: str) -> Optional[BaseAgent]: ...
    def get_all_agents(self) -> List[Dict]: ...
```

### 3. WebSocket消息格式
```json
// 客户端发送
{
  "message": "用户消息",
  "agent_type": "chat" | "chatbi",
  "table_context": {"database": "db_name", "table": "table_name"}
}

// 服务器响应
{"type": "start", "message": "...", "agent_type": "..."}
{"type": "stream", "content": "..."}
{"type": "end", "full_response": "...", "agent_type": "..."}
{"type": "error", "content": "..."}
```

## 🎨 UI特性

### Agent选择器
- 按钮式切换设计
- 图标+文字组合
- 活动状态高亮显示

### 表选择器
- 实时搜索和过滤
- 数据库和表分类显示
- 键盘快捷键支持
- 清除按钮快速重置

### 上下文显示条
- 仅在ChatBI模式且选择表时显示
- 渐变背景设计
- 清晰显示当前分析表

## 🔐 安全考虑

1. **SQL注入防护**: 使用参数化查询
2. **CORS配置**: 限制允许的源
3. **输入验证**: Pydantic模型验证所有输入
4. **错误处理**: 完善的异常捕获和用户友好提示

## 📊 性能优化

1. **流式响应**: WebSocket流式输出，提升用户体验
2. **对话历史限制**: 只保留最近6条消息
3. **元数据缓存**: 数据库元数据服务单例模式
4. **异步处理**: 使用asyncio提升并发性能

## 🐛 已知问题和解决

### 问题1: 相对导入错误
**症状**: `ImportError: attempted relative import beyond top-level package`

**解决**: 将相对导入改为绝对导入
```python
# 错误
from .base_agent import BaseAgent
from ..tools.chatbi_tool import chatbi_query

# 正确
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base_agent import BaseAgent
from tools.chatbi_tool import chatbi_query
```

## 📈 后续优化建议

1. **用户认证**: 添加用户登录和权限管理
2. **对话持久化**: 将对话历史存储到数据库
3. **更多Agent**: 添加代码生成、文档分析等专用Agent
4. **可视化增强**: 集成图表库展示查询结果
5. **性能监控**: 添加日志和性能追踪
6. **缓存优化**: 添加Redis缓存查询结果

## 🎉 总结

本项目成功实现了：
✅ 清晰的多Agent架构
✅ 智能的表选择机制
✅ 完善的上下文管理
✅ 良好的用户体验
✅ 可扩展的代码结构

## 📞 技术支持

如有问题，请查看：
- API文档：http://localhost:8000/api/docs
- 项目仓库：https://github.com/wangyiyi1025/langchain-demo
