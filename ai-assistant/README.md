# AI Assistant - 智能数据分析助手

基于 LangChain + FastAPI + React 构建的智能数据分析对话系统,支持自然语言查询数据库、数据分析和可视化。

## 项目简介

AI Assistant 是一个功能强大的智能数据分析助手,通过自然语言对话的方式帮助用户查询和分析数据库数据。系统采用 Agent 架构,支持多种大语言模型(LLM),可以理解用户的自然语言问题,自动生成 SQL 查询,执行数据分析,并提供可视化建议。

### 核心特性

- **自然语言转 SQL**: 用户可以用自然语言提问,系统自动生成对应的 SQL 查询
- **智能数据分析**: 基于查询结果进行深度数据分析,提供业务洞察
- **可视化推荐**: 智能推荐最合适的图表类型(柱状图、折线图、饼图等)
- **多 Agent 架构**: 支持扩展不同功能的智能助手
- **流式对话**: 基于 WebSocket 的实时流式响应
- **会话管理**: 支持多会话管理,保存对话历史
- **表上下文管理**: 自动管理数据表上下文,提高查询准确性
- **时间对比分析**: 支持同比、环比、同期等复杂时间维度分析
- **用户认证**: JWT 认证机制保障数据安全
- **灵活部署**: 支持多种 LLM 后端(Ollama、OpenAI、阿里千问等)

## 技术栈

### 后端技术

- **框架**: FastAPI 0.121+ - 现代化的 Python Web 框架
- **AI 框架**: LangChain 0.3+ - Agent 和工具编排
- **LLM 支持**:
  - OpenAI 兼容接口(支持任意兼容服务)
  - Ollama(本地模型)
  - 阿里千问(DashScope)
  - vLLM / LM Studio
- **数据库**:
  - MySQL - 元数据存储
  - StarRocks - 数据分析目标数据库
- **认证**: JWT (PyJWT 2.8+)
- **数据处理**: Pandas 2.2+
- **其他**:
  - uvicorn - ASGI 服务器
  - websockets - WebSocket 支持
  - APScheduler - 定时任务

### 前端技术

- **框架**: React 18.3+
- **构建工具**: Vite 5.4+
- **路由**: React Router DOM 6.22+
- **HTTP 客户端**: Axios 1.6+
- **可视化**: Recharts 3.5+ - 数据可视化图表库
- **样式**: 原生 CSS

## 项目结构

```
ai-assistant/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent 实现
│   │   │   ├── base_agent.py      # Agent 基类
│   │   │   ├── chatbi_agent.py    # ChatBI 数据分析 Agent
│   │   │   └── agent_manager.py   # Agent 管理器
│   │   ├── api/               # API 路由
│   │   │   ├── auth.py           # 认证接口
│   │   │   ├── chat.py           # 聊天接口(WebSocket/HTTP)
│   │   │   ├── conversations.py  # 会话管理接口
│   │   │   ├── database.py       # 数据库查询接口
│   │   │   └── system.py         # 系统信息接口
│   │   ├── models/            # 数据模型
│   │   │   ├── user.py           # 用户模型
│   │   │   ├── conversation.py   # 会话模型
│   │   │   └── schemas.py        # Pydantic 模式定义
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── auth_service.py         # 认证服务
│   │   │   ├── conversation_service.py # 会话服务
│   │   │   ├── database_service.py     # 数据库服务
│   │   │   └── cleanup_service.py      # 清理服务
│   │   ├── tools/             # LangChain 工具
│   │   │   ├── chatbi_tools_atomic.py  # 原子工具(推荐)
│   │   │   ├── chatbi_chains.py        # 预定义工具链
│   │   │   ├── chatbi_tool.py          # 向后兼容工具
│   │   │   └── time_tool.py            # 时间工具
│   │   ├── utils/             # 工具函数
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库初始化
│   │   ├── logger.py          # 日志配置
│   │   └── main.py            # 应用入口
│   ├── requirements.txt       # Python 依赖
│   └── .env.example          # 环境配置示例
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── components/       # React 组件
│   │   │   ├── AgentSelector.jsx       # Agent 选择器
│   │   │   ├── TableSelector.jsx       # 数据表选择器
│   │   │   ├── ConversationSidebar.jsx # 会话侧边栏
│   │   │   ├── ContextBar.jsx          # 上下文显示条
│   │   │   ├── ChatMessage.jsx         # 消息组件
│   │   │   ├── ChatInput.jsx           # 输入组件
│   │   │   ├── ChartRenderer.jsx       # 图表渲染
│   │   │   └── TypingIndicator.jsx     # 输入指示器
│   │   ├── pages/            # 页面组件
│   │   │   ├── Login.jsx             # 登录页
│   │   │   └── ChatPage.jsx          # 主聊天页
│   │   ├── contexts/         # React Context
│   │   │   └── AuthContext.jsx       # 认证上下文
│   │   ├── services/         # API 服务
│   │   │   └── api.js               # API 客户端
│   │   ├── assets/           # 静态资源
│   │   ├── App.jsx          # 应用根组件
│   │   └── main.jsx         # 应用入口
│   ├── package.json         # npm 依赖
│   └── vite.config.js       # Vite 配置
└── README.md                # 项目文档
```

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ 登录页面 │  │ 聊天界面 │  │ 可视化   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket / HTTP
┌────────────────────┴────────────────────────────────────┐
│                   后端 (FastAPI)                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │          API Layer (路由层)                      │   │
│  │  /auth  /chat  /conversations  /database       │   │
│  └──────────────────┬──────────────────────────────┘   │
│  ┌──────────────────┴──────────────────────────────┐   │
│  │        Service Layer (业务逻辑层)                │   │
│  │  AuthService  ConversationService               │   │
│  └──────────────────┬──────────────────────────────┘   │
│  ┌──────────────────┴──────────────────────────────┐   │
│  │         Agent Layer (智能代理层)                 │   │
│  │  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │ ChatBI Agent │  │  更多 Agent  │            │   │
│  │  └──────┬───────┘  └──────────────┘            │   │
│  │         │ LangChain                             │   │
│  └─────────┼───────────────────────────────────────┘   │
│  ┌─────────┴──────────────────────┐                    │
│  │       Tools (工具层)            │                    │
│  │  • 原子工具(推荐):              │                    │
│  │    - get_schema_info           │                    │
│  │    - nl_to_sql                 │                    │
│  │    - execute_sql               │                    │
│  │    - analyze_data              │                    │
│  │    - suggest_chart             │                    │
│  │  • 预定义工具链(快速):          │                    │
│  │    - chatbi_query_only_chain   │                    │
│  │    - chatbi_query_with_analysis│                    │
│  │    - chatbi_full_analysis      │                    │
│  └────────────────────────────────┘                    │
└──────────────┬──────────────┬─────────────────────────┘
               │              │
         ┌─────┴────┐   ┌────┴─────────┐
         │  MySQL   │   │  StarRocks   │
         │ (元数据) │   │ (分析数据)   │
         └──────────┘   └──────────────┘
```

### ChatBI Agent 工作流程

```
用户输入: "查询销售额前10的产品"
           ↓
┌──────────────────────────────────────┐
│  ChatBI Agent (任务编排)              │
│  - 识别用户意图                       │
│  - 选择合适的工具链/工具组合           │
│  - 管理上下文传递                     │
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  场景识别与工具选择                   │
│  只查询? → chatbi_query_only_chain    │
│  查询+分析? → chatbi_query_with_...   │
│  复杂场景? → 原子工具组合             │
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  工具执行流程(以完整分析为例)         │
│  1. get_schema_info                  │
│     ├─ 获取表结构和字段注释           │
│     └─ 返回结构化 schema 信息         │
│  2. nl_to_sql                        │
│     ├─ 接收自然语言问题和 schema      │
│     ├─ LLM 理解业务术语和时间逻辑     │
│     └─ 生成准确的 SQL 查询            │
│  3. execute_sql                      │
│     ├─ 执行 SQL 查询                 │
│     └─ 返回查询结果数据               │
│  4. analyze_data                     │
│     ├─ LLM 分析数据特征和趋势         │
│     └─ 生成业务洞察                   │
│  5. suggest_chart                    │
│     ├─ 根据数据和问题推荐图表类型     │
│     └─ 返回图表建议                   │
│  6. generate_chart_config            │
│     ├─ 生成前端图表配置               │
│     └─ 返回完整的 JSON 配置           │
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  返回结果                             │
│  {                                   │
│    "success": true,                  │
│    "sql": "SELECT ...",              │
│    "data": [...],                    │
│    "analysis": "...",                │
│    "chart_config": {...}             │
│  }                                   │
└──────────────────────────────────────┘
```

## 功能模块说明

### 1. ChatBI Agent - 数据分析代理

ChatBI Agent 是系统的核心功能模块,专门负责数据库查询和数据分析任务。

**主要能力**:
- 自然语言转 SQL(支持复杂的时间对比分析:同比、环比、同期)
- 数据库表结构查询
- SQL 执行
- 数据分析和洞察生成
- 图表类型智能推荐
- 图表配置生成

**架构特点**:
- **职责分离**: Agent 专注任务编排,LLM 调用封装在工具中
- **预定义工具链**: 针对常见场景(只查询、查询+分析等)提供优化的快速链路
- **原子工具**: 灵活组合处理复杂场景
- **上下文传递**: 工具间通过结构化数据传递信息

**支持的 Agent 类型**:
1. **ReAct Agent**(推荐用于本地模型):
   - 基于 Thought/Action/Action Input 格式
   - 适用于 Ollama、vLLM、LM Studio 等本地部署模型
   - 不依赖特定 API 格式,兼容性好

2. **Tool Calling Agent**(推荐用于 OpenAI):
   - 使用 OpenAI function calling 格式
   - 支持多轮对话历史
   - 需要模型原生支持 function calling

### 2. 会话管理系统

- **多会话支持**: 用户可以创建和管理多个对话会话
- **历史记录**: 自动保存对话历史到数据库
- **会话恢复**: 切换会话时自动加载历史消息和上下文
- **自动清理**: 定时清理过期会话(可配置)

### 3. 表上下文管理

- **智能上下文**: 自动记住当前分析的数据表
- **上下文传递**: 在对话中保持表上下文,无需重复指定
- **灵活切换**: 支持随时切换分析目标表

### 4. 认证与安全

- **JWT 认证**: 基于 Token 的无状态认证
- **用户注册/登录**: 完整的用户管理系统
- **密码加密**: 使用 bcrypt 加密存储
- **会话隔离**: 不同用户的会话数据完全隔离

### 5. 数据可视化

- **多种图表类型**: 柱状图、折线图、饼图、散点图、表格等
- **智能推荐**: 根据数据特征自动推荐最合适的图表
- **交互式图表**: 基于 Recharts 的可交互图表
- **导出功能**: 支持图表和数据导出

## 安装部署

### 环境要求

- Python 3.9+
- Node.js 16+
- MySQL 5.7+ / 8.0+
- StarRocks 2.0+ (或其他兼容 MySQL 协议的数据库)
- Ollama (如使用本地模型) 或 OpenAI API Key

### 后端部署

1. **安装依赖**

```bash
cd ai-assistant/backend
pip install -r requirements.txt
```

2. **配置环境变量**

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 文件,配置以下关键参数:
# - 数据库连接信息(MySQL、StarRocks)
# - LLM 配置(API Key、Base URL、模型名称)
# - Agent 类型选择
# - JWT 密钥
```

3. **初始化数据库**

```bash
# 系统会在首次启动时自动创建必要的表结构
# 确保 MySQL 服务已启动且配置的数据库存在
```

4. **启动后端服务**

```bash
# 开发模式(支持热重载)
python app/main.py

# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务将在 `http://localhost:8000` 启动。

### 前端部署

1. **安装依赖**

```bash
cd ai-assistant/frontend
npm install
```

2. **配置 API 地址**

编辑 `src/services/api.js`,确保后端 API 地址正确:

```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
const WS_BASE_URL = 'ws://localhost:8000/api/v1';
```

3. **启动前端服务**

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build
```

前端将在 `http://localhost:5173` 启动。

## 使用说明

### 1. 注册登录

首次使用需要注册账号:
1. 访问登录页面
2. 输入用户名和密码
3. 点击注册或登录

### 2. 选择数据表

1. 在主界面点击"选择表"按钮
2. 在表选择器中搜索或浏览数据表
3. 选择要分析的表

### 3. 开始对话

选择表后,即可开始自然语言对话:

**示例问题**:
- "查询销售额前10的产品"
- "分析最近7天的订单趋势"
- "显示各地区的销售额占比"
- "2025年销售额同比增长前五的产品"
- "本月用户数环比上月的增长情况"

### 4. 理解时间对比分析

系统支持复杂的时间维度分析:

- **同比**: 与去年同期对比
  - 例: "2025年3月销售额同比增长"
  - 对比: 2025年3月 vs 2024年3月

- **环比**: 与上一个相邻周期对比
  - 例: "本月销售额环比上月"
  - 对比: 当前月 vs 上一个月

- **同期**: 截止当前时点的累计数据
  - 例: "2025年同期销售额"
  - 范围: 2025-01-01 至当前日期

### 5. 查看分析结果

系统会返回:
- SQL 查询语句
- 查询数据(表格形式)
- 数据分析洞察
- 可视化图表(如适用)

### 6. 会话管理

- 点击侧边栏的"+"创建新会话
- 点击历史会话可切换和恢复
- 每个会话独立保存对话历史和表上下文

## 配置说明

### 主要配置项

#### 应用配置

```env
APP_NAME=AI Assistant
APP_VERSION=1.0.0
DEBUG=True
API_PREFIX=/api/v1
```

#### LLM 配置

```env
# OpenAI 兼容接口配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:latest
LLM_TEMPERATURE=0.1      # 建议 ReAct: 0.1-0.3, Tool Calling: 0.5-0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
LLM_PROVIDER=ollama
```

#### Agent 配置

```env
AGENT_TYPE=react              # react 或 tool_calling
AGENT_MAX_ITERATIONS=5        # 最大迭代次数
AGENT_VERBOSE=True            # 是否显示详细日志
AGENT_HANDLE_PARSING_ERRORS=True  # 是否处理解析错误
```

#### 数据库配置

```env
# MySQL (元数据存储)
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=smart_chat_bi_meta

# StarRocks (分析数据库)
STARROCKS_HOST=127.0.0.1
STARROCKS_PORT=9030
STARROCKS_USER=admin
STARROCKS_PASSWORD=your-password
```

#### 认证配置

```env
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # Token 有效期(分钟)
```

## API 文档

### 在线文档

启动后端服务后,访问以下地址查看完整的 API 文档:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## 开发指南

### 添加新的 Agent

1. 在 `backend/app/agents/` 创建新的 Agent 类,继承 `BaseAgent`
2. 实现必需的方法: `get_agent_type()`, `get_agent_name()`, `invoke()`, `stream()`
3. 在 `main.py` 中注册 Agent

```python
from app.agents.your_agent import YourAgent
from app.agents.agent_manager import agent_manager

# 注册 Agent
your_agent = YourAgent()
agent_manager.register_agent(your_agent)
```

### 添加新的工具

1. 在 `backend/app/tools/` 创建工具文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 Agent 的 `tools` 列表中引用

```python
from langchain_core.tools import tool

@tool
def your_tool(param: str) -> str:
    """工具描述"""
    # 实现逻辑
    return result
```

### 前端组件开发

- 遵循 React Hooks 模式
- 组件放在 `frontend/src/components/`
- 页面放在 `frontend/src/pages/`
- API 调用统一在 `frontend/src/services/api.js` 中定义

### 日志管理

系统使用 `logging` 模块,日志文件位于 `backend/logs/app.log`

查看日志:
```bash
tail -f backend/logs/app.log
```

### 调试技巧

1. **启用详细日志**: 设置 `AGENT_VERBOSE=True` 和 `LOG_LEVEL=DEBUG`
2. **查看 LLM 请求**: 日志中会记录所有 LLM 调用的 prompt 和响应
3. **WebSocket 调试**: 使用浏览器开发者工具的 Network 标签查看 WebSocket 消息

## 联系方式

如有问题或建议,请提交 Issue 或联系项目维护者。
