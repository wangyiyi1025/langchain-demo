# LLM 配置指南

本项目已升级为支持任何 **OpenAI 兼容接口**的大模型服务，你可以轻松切换到本地大模型或云端服务。

## 快速开始

### 1. 复制配置文件

```bash
cd ai-assistant/backend
cp .env.example .env
```

### 2. 选择你的大模型服务

在 `.env` 文件中，根据你的需求选择并配置以下任意一种服务：

---

## 支持的服务配置

### 🔥 推荐：Ollama 本地模型

**适用场景**：本地开发、数据隐私要求高、无需联网

**安装 Ollama**：
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# 或访问 https://ollama.com 下载
```

**拉取模型**：
```bash
# 推荐：Qwen2.5（阿里千问，中英文都很好）
ollama pull qwen2.5:latest

# 或其他模型
ollama pull llama3.1:latest
ollama pull mistral:latest
```

**配置 `.env`**：
```bash
OPENAI_API_KEY=sk-dummy-key
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:latest
LLM_PROVIDER=ollama
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
```

---

### ⚡ vLLM 本地部署

**适用场景**：需要高性能推理、GPU 服务器部署

**安装 vLLM**：
```bash
pip install vllm
```

**启动服务**：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --served-model-name Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

**配置 `.env`**：
```bash
OPENAI_API_KEY=sk-dummy-key
OPENAI_BASE_URL=http://localhost:8000/v1
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
LLM_PROVIDER=vllm
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
```

---

### 🖥️ LM Studio

**适用场景**：图形化界面、易于管理模型

**安装**：访问 [https://lmstudio.ai](https://lmstudio.ai) 下载

**启动服务**：
1. 打开 LM Studio
2. 下载模型（如 `qwen2.5-7b-instruct`）
3. 点击 "Start Server"
4. 默认端口为 1234

**配置 `.env`**：
```bash
OPENAI_API_KEY=sk-dummy-key
OPENAI_BASE_URL=http://localhost:1234/v1
LLM_MODEL=qwen2.5-7b-instruct
LLM_PROVIDER=lmstudio
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
```

---

### ☁️ 阿里云千问（原配置）

**适用场景**：云端服务、无需本地部署

**获取 API Key**：访问 [https://dashscope.console.aliyun.com/](https://dashscope.console.aliyun.com/)

**配置 `.env`**：
```bash
OPENAI_API_KEY=your-dashscope-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_PROVIDER=qwen
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
```

---

### 🤖 OpenAI 官方

**适用场景**：使用 GPT-4/GPT-3.5 等模型

**获取 API Key**：访问 [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**配置 `.env`**：
```bash
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4
LLM_PROVIDER=openai
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
```

---

### 🌐 其他兼容服务

只要服务支持 OpenAI API 格式，都可以直接使用，例如：

- **DeepSeek**: `https://api.deepseek.com/v1`
- **智谱 AI (GLM)**: `https://open.bigmodel.cn/api/paas/v4`
- **Moonshot (Kimi)**: `https://api.moonshot.cn/v1`
- **文心一言**: 使用千帆平台的 OpenAI 兼容接口
- **自建服务**: 如 LocalAI、FastChat 等

**通用配置模板**：
```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-service-url/v1
LLM_MODEL=your-model-name
LLM_PROVIDER=your-provider-name
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_MAX_RETRIES=2
```

---

## 配置参数说明

| 参数 | 说明 | 示例 | 必填 |
|------|------|------|------|
| `OPENAI_API_KEY` | API 密钥（本地模型可用任意值） | `sk-dummy-key` | ✅ |
| `OPENAI_BASE_URL` | API 基础地址 | `http://localhost:11434/v1` | ✅ |
| `LLM_MODEL` | 模型名称 | `qwen2.5:latest` | ✅ |
| `LLM_PROVIDER` | 提供商标识（用于日志） | `ollama` | ✅ |
| `LLM_TEMPERATURE` | 温度参数（0-2，控制随机性） | `0.7` | ❌ |
| `LLM_MAX_TOKENS` | 最大生成 token 数 | `2000` | ❌ |
| `LLM_MAX_RETRIES` | 失败重试次数 | `2` | ❌ |

---

## 验证配置

配置完成后，启动服务时会看到以下日志：

```
============================================================
应用配置信息
============================================================
应用名称: AI Assistant
应用版本: 1.0.0
调试模式: True
API前缀: /api/v1
------------------------------------------------------------
大模型配置 (OpenAI兼容接口):
  提供商: ollama
  API Key: sk-d****
  Base URL: http://localhost:11434/v1
  模型: qwen2.5:latest
  温度: 0.7
  最大Token: 2000
  最大重试: 2
------------------------------------------------------------
```

如果配置有误，启动时会报错并提示具体问题。

---

## 常见问题

### Q1: 本地模型需要真实的 API Key 吗？
**A**: 不需要。本地模型（如 Ollama、vLLM、LM Studio）通常不验证 API Key，你可以使用 `sk-dummy-key` 或任意值。

### Q2: 如何选择模型？
**A**:
- **中英文场景**：推荐 `qwen2.5`（阿里千问）
- **纯英文场景**：可选 `llama3.1`、`mistral`
- **性能优先**：选择 7B 参数的模型（如 `qwen2.5:7b`）
- **质量优先**：选择更大参数的模型（如 `qwen2.5:14b` 或云端 `qwen-plus`）

### Q3: 如何测试模型是否正常？
**A**: 启动服务后，发送一条测试消息，查看日志中是否有成功的 LLM 调用记录。

### Q4: 切换模型需要重启服务吗？
**A**: 是的。修改 `.env` 文件后需要重启后端服务才能生效。

### Q5: 如何查看 LLM 调用的详细日志？
**A**: 在 `.env` 中设置 `DEBUG=True` 和 `AGENT_VERBOSE=True`，日志会显示所有 LLM 调用的 prompt 和响应。

---

## 性能优化建议

1. **本地部署**：
   - 使用 GPU 加速（需要 NVIDIA GPU + CUDA）
   - 选择适合显存的模型（7B 需约 8GB 显存）
   - 使用量化模型（如 `qwen2.5:7b-q4` 仅需 4GB 显存）

2. **网络配置**：
   - 本地服务使用 `http://localhost` 而不是 `http://127.0.0.1`
   - 云端服务注意设置合理的超时时间

3. **参数调优**：
   - `LLM_TEMPERATURE`: 0.5-0.7（更稳定）
   - `LLM_MAX_TOKENS`: 根据实际需求调整
   - `LLM_MAX_RETRIES`: 网络不稳定时增加重试次数

---

## 技术架构

本项目使用 **LangChain + ChatOpenAI** 实现，架构如下：

```
应用层 (FastAPI)
    ↓
Agent 层 (LangChain Agent)
    ↓
Tool 层 (原子工具 + 预定义工具链)
    ↓
LLM 层 (ChatOpenAI - 单例模式)
    ↓
任意 OpenAI 兼容接口
```

**关键代码位置**：
- 配置文件：`app/config.py`
- LLM 单例：`app/tools/chatbi_tools_atomic.py:368-385`
- Agent 初始化：`app/agents/chatbi_agent.py:46-57`

---

## 升级说明

如果你之前使用的是阿里云千问配置，本次升级做了以下改动：

| 旧配置变量 | 新配置变量 | 说明 |
|-----------|-----------|------|
| `DASHSCOPE_API_KEY` | `OPENAI_API_KEY` | 更通用的命名 |
| `DASHSCOPE_BASE_URL` | `OPENAI_BASE_URL` | 更通用的命名 |
| `QWEN_MODEL` | `LLM_MODEL` | 去除模型绑定 |
| `QWEN_TEMPERATURE` | `LLM_TEMPERATURE` | 去除模型绑定 |
| `QWEN_MAX_TOKENS` | `LLM_MAX_TOKENS` | 去除模型绑定 |
| `QWEN_MAX_RETRIES` | `LLM_MAX_RETRIES` | 去除模型绑定 |
| ❌ | `LLM_PROVIDER` | 新增：标识提供商 |

**迁移步骤**：只需更新 `.env` 文件中的配置变量名即可，功能完全兼容。

---

## 贡献

如果你成功配置了其他 OpenAI 兼容服务，欢迎提交 PR 更新本文档！

---

**最后更新**: 2025-11-28
