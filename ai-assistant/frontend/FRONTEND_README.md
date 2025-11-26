# AI Assistant 前端

基于React + Vite构建的智能对话助手前端应用，支持用户认证、对话管理和实时聊天功能。

## 功能特性

### ✅ 已实现功能

1. **用户认证**
   - 邮箱登录
   - 图片验证码
   - JWT token管理
   - 自动登录（记住登录状态）
   - 路由保护（未登录重定向）

2. **对话管理**
   - 创建新对话
   - 删除对话
   - 重命名对话
   - 清除对话消息
   - 对话列表展示
   - 对话切换

3. **实时聊天**
   - WebSocket实时通信
   - 流式响应显示
   - 表选择器
   - 消息历史记录
   - 自动重连机制

4. **安全性**
   - 所有API请求自动携带token
   - Token过期自动跳转登录
   - WebSocket认证保护

## 项目结构

```
frontend/
├── src/
│   ├── assets/
│   │   └── styles/
│   │       ├── main.css                    # 主样式
│   │       ├── Login.css                   # 登录页样式
│   │       └── ConversationSidebar.css     # 对话侧边栏样式
│   ├── components/
│   │   ├── AgentSelector.jsx               # Agent选择器
│   │   ├── ChatHeader.jsx                  # 聊天头部
│   │   ├── ChatInput.jsx                   # 聊天输入框
│   │   ├── ChatMessage.jsx                 # 聊天消息
│   │   ├── ChartRenderer.jsx               # 图表渲染器
│   │   ├── ContextBar.jsx                  # 上下文栏
│   │   ├── ConversationSidebar.jsx         # 对话管理侧边栏 ✨
│   │   ├── ProtectedRoute.jsx              # 路由保护组件 ✨
│   │   ├── TableSelector.jsx               # 表选择器
│   │   └── TypingIndicator.jsx             # 打字指示器
│   ├── contexts/
│   │   └── AuthContext.jsx                 # 认证上下文 ✨
│   ├── pages/
│   │   ├── ChatPage.jsx                    # 主聊天页面 ✨
│   │   └── Login.jsx                       # 登录页面 ✨
│   ├── services/
│   │   └── api.js                          # API服务配置 ✨
│   ├── App.jsx                             # 应用主组件（更新）✨
│   └── main.jsx                            # 应用入口
├── package.json
├── vite.config.js
└── FRONTEND_README.md
```

**✨ 标记的是本次新增或更新的文件**

## 安装和运行

### 1. 安装依赖

```bash
cd ai-assistant/frontend
npm install
```

新增的依赖包：
- `axios` - HTTP客户端，用于API调用
- `react-router-dom` - 路由管理

### 2. 配置环境变量（可选）

创建 `.env` 文件：

```bash
# API基础URL（可选，默认为http://localhost:8000/api/v1）
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### 4. 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录

## 使用指南

### 登录

1. 访问应用，自动跳转到登录页
2. 输入邮箱和密码
3. 输入验证码（点击验证码图片可刷新）
4. 点击"登录"按钮

**默认管理员账号：**
- 邮箱：`admin@tpl.cntaiping.com`
- 密码：`123456`

### 对话管理

#### 创建新对话
1. 点击侧边栏顶部的"新建对话"按钮
2. 新对话会自动添加到列表顶部

#### 重命名对话
1. 点击对话项右侧的"✏️"图标
2. 输入新标题
3. 按Enter或点击"✓"保存

#### 删除对话
1. 点击对话项右侧的"❌"图标
2. 确认删除

#### 清除对话消息
1. 点击对话项右侧的"🗑️"图标
2. 确认清除

### 聊天功能

1. 点击表选择器选择数据库和表
2. 在输入框中输入问题
3. 按Enter或点击发送按钮
4. 查看AI的流式响应

### 退出登录

1. 点击侧边栏顶部的用户信息
2. 点击"退出登录"

## API集成

### 自动Token管理

所有API请求会自动在请求头中添加JWT token：

```javascript
Authorization: Bearer <token>
```

### WebSocket认证

WebSocket连接通过query参数传递token：

```javascript
ws://localhost:8000/api/v1/chat/ws/<session_id>?token=<token>
```

### Token过期处理

当token过期（401错误）时，应用会自动：
1. 清除本地存储的token
2. 重定向到登录页
3. 提示用户重新登录

## 开发说明

### 添加新的API调用

在 `src/services/api.js` 中添加新的API方法：

```javascript
export const myNewApi = (data) => {
  return api.post('/my-endpoint', data);
};
```

### 使用认证上下文

在组件中使用认证信息：

```javascript
import { useAuth } from '../contexts/AuthContext';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();

  // 使用认证状态
}
```

### 创建受保护的路由

```javascript
<Route
  path="/protected"
  element={
    <ProtectedRoute>
      <MyProtectedPage />
    </ProtectedRoute>
  }
/>
```

## 故障排查

### 问题：登录后页面没有跳转

**解决方案：**
1. 检查后端服务是否正常运行
2. 检查浏览器控制台是否有错误
3. 检查Network标签，确认API返回了正确的token

### 问题：WebSocket连接失败

**解决方案：**
1. 检查后端WebSocket服务是否运行
2. 检查token是否有效（在localStorage中查看）
3. 查看浏览器控制台的WebSocket错误信息

### 问题：401认证错误

**解决方案：**
1. Token可能已过期，请重新登录
2. 检查localStorage中是否存在access_token
3. 确认后端JWT配置正确

### 问题：验证码加载失败

**解决方案：**
1. 检查后端是否正常运行
2. 检查Network标签，确认/auth/captcha接口正常
3. 点击验证码图片刷新重试

## 技术栈

- **React 18** - UI框架
- **Vite** - 构建工具
- **React Router** - 路由管理
- **Axios** - HTTP客户端
- **WebSocket** - 实时通信
- **CSS3** - 样式（无UI框架，纯手写）

## 注意事项

1. **Token安全**
   - Token存储在localStorage中
   - 生产环境建议使用httpOnly cookie
   - 定期刷新token以提高安全性

2. **网络错误处理**
   - 所有API调用都有错误处理
   - WebSocket断开会自动重连
   - 显示友好的错误提示

3. **浏览器兼容性**
   - 支持现代浏览器（Chrome、Firefox、Edge、Safari）
   - 需要浏览器支持ES6+
   - 需要支持WebSocket

## 下一步计划

- [ ] 对话消息持久化（从数据库加载历史消息）
- [ ] 对话搜索功能
- [ ] 用户设置页面
- [ ] 深色模式支持
- [ ] 移动端适配优化
- [ ] 消息导出功能

## 贡献

如果您发现bug或有功能建议，请创建Issue或提交Pull Request。
