# API 认证说明

## 概述

所有API端点（除了公开端点）现在都需要JWT认证。用户必须先登录获取token，然后在后续请求中携带token才能访问受保护的API。

## 公开端点（无需认证）

以下端点可以直接访问，无需提供token：

- `GET /api/v1/system/health` - 健康检查
- `GET /api/v1/auth/captcha` - 获取验证码
- `POST /api/v1/auth/login` - 用户登录
- `GET /` - 根路径

## 受保护端点（需要认证）

以下端点需要在请求头中携带有效的JWT token：

### 用户认证API
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/auth/logout` - 登出

### 对话管理API
- `POST /api/v1/conversations` - 创建对话
- `GET /api/v1/conversations` - 获取对话列表
- `GET /api/v1/conversations/{id}` - 获取对话详情
- `PUT /api/v1/conversations/{id}` - 更新对话标题
- `DELETE /api/v1/conversations/{id}` - 删除对话
- `DELETE /api/v1/conversations/{id}/messages` - 清除对话消息
- `GET /api/v1/conversations/{id}/messages` - 获取对话消息

### 聊天API
- `POST /api/v1/chat/message` - 发送消息（同步）
- `WS /api/v1/chat/ws/{session_id}?token=<jwt_token>` - WebSocket聊天（流式）
- `DELETE /api/v1/chat/clear/{session_id}` - 清除会话历史
- `GET /api/v1/chat/history/{session_id}` - 获取会话历史
- `GET /api/v1/chat/agents` - 获取Agent列表
- `POST /api/v1/chat/table-context/{session_id}` - 设置表上下文
- `GET /api/v1/chat/table-context/{session_id}` - 获取表上下文
- `DELETE /api/v1/chat/table-context/{session_id}` - 清除表上下文

### 数据库API
- `GET /api/v1/database/databases` - 获取数据库列表
- `GET /api/v1/database/databases/{database}/tables` - 获取表列表
- `GET /api/v1/database/databases/{database}/tables/{table}/schema` - 获取表结构
- `GET /api/v1/database/metadata` - 获取元数据
- `GET /api/v1/database/metadata-with-comments` - 获取元数据（含注释）
- `GET /api/v1/database/search/tables` - 搜索表

### 系统API
- `GET /api/v1/system/info` - 获取系统信息
- `GET /api/v1/system/tools` - 获取工具列表

## 认证流程

### 1. 获取验证码

```bash
GET /api/v1/auth/captcha
```

响应：
```json
{
  "captcha_key": "uuid-string",
  "captcha_image": "data:image/png;base64,...",
  "expires_in": 300
}
```

### 2. 用户登录

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@tpl.cntaiping.com",
  "password": "123456",
  "captcha_key": "uuid-string",
  "captcha_code": "ABCD"
}
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@tpl.cntaiping.com",
    "created_at": "2024-01-01T00:00:00",
    "last_login_at": "2024-01-01T00:00:00",
    "is_active": true
  }
}
```

### 3. 使用Token访问受保护的API

#### HTTP请求示例

```bash
GET /api/v1/conversations
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### WebSocket连接示例

```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/session_123?token=${token}`);
```

## 前端集成

### 1. 存储Token

登录成功后，将token存储在localStorage或sessionStorage中：

```javascript
// 登录成功后
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('user', JSON.stringify(response.user));
```

### 2. 在请求中添加Token

使用Axios拦截器自动添加token：

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1'
});

// 请求拦截器：自动添加token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// 响应拦截器：处理401错误
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token过期或无效，跳转到登录页
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 3. WebSocket连接

```javascript
const token = localStorage.getItem('access_token');
const sessionId = 'session_' + Date.now();
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/chat/ws/${sessionId}?token=${token}`
);

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onerror = (event) => {
  console.error('WebSocket error:', event);
  // 如果是认证错误，跳转到登录页
};

ws.onclose = (event) => {
  if (event.code === 1008) {
    // 认证失败
    alert('认证失败，请重新登录');
    window.location.href = '/login';
  }
};
```

## 错误响应

### 401 Unauthorized

当token无效、过期或未提供时，返回：

```json
{
  "detail": "认证令牌无效或已过期"
}
```

### 403 Forbidden

当用户没有权限访问资源时，返回：

```json
{
  "detail": "没有权限访问此资源"
}
```

## Token有效期

- 默认有效期：7天（10080分钟）
- 可以在`.env`文件中配置：`JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080`

## 安全建议

1. **HTTPS**: 生产环境必须使用HTTPS，避免token在传输过程中被窃取
2. **Token存储**: 建议使用httpOnly cookie存储token（需要修改代码）
3. **密钥安全**: 确保`JWT_SECRET_KEY`足够复杂且保密
4. **Token刷新**: 考虑实现refresh token机制，提高安全性
5. **跨域配置**: 生产环境需要正确配置CORS白名单

## 默认管理员账号

系统启动时会自动创建默认管理员账号：

- 邮箱：`admin@tpl.cntaiping.com`
- 密码：`123456`

**⚠️ 生产环境请立即修改默认密码！**
