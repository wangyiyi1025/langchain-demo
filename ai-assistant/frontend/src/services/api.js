/**
 * API 服务配置
 * 配置axios实例，自动添加token和处理认证错误
 */
import axios from 'axios';

// API基础URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理401错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token过期或无效，清除本地存储并跳转到登录页
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');

      // 只在不是登录页时才跳转
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ==================== 认证相关 API ====================

/**
 * 获取验证码
 */
export const getCaptcha = () => {
  return api.get('/auth/captcha');
};

/**
 * 用户登录
 */
export const login = (credentials) => {
  return api.post('/auth/login', credentials);
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = () => {
  return api.get('/auth/me');
};

/**
 * 登出
 */
export const logout = () => {
  return api.post('/auth/logout');
};

// ==================== 对话管理 API ====================

/**
 * 创建新对话
 */
export const createConversation = (data) => {
  return api.post('/conversations', data);
};

/**
 * 获取对话列表
 */
export const getConversations = (params = {}) => {
  return api.get('/conversations', { params });
};

/**
 * 获取对话详情
 */
export const getConversation = (id) => {
  return api.get(`/conversations/${id}`);
};

/**
 * 更新对话标题
 */
export const updateConversation = (id, data) => {
  return api.put(`/conversations/${id}`, data);
};

/**
 * 删除对话
 */
export const deleteConversation = (id) => {
  return api.delete(`/conversations/${id}`);
};

/**
 * 清除对话消息
 */
export const clearConversationMessages = (id) => {
  return api.delete(`/conversations/${id}/messages`);
};

/**
 * 获取对话消息列表
 */
export const getConversationMessages = (id, params = {}) => {
  return api.get(`/conversations/${id}/messages`, { params });
};

// ==================== 聊天 API ====================

/**
 * 发送消息（同步）
 */
export const sendMessage = (data) => {
  return api.post('/chat/message', data);
};

/**
 * 获取Agent列表
 */
export const getAgents = () => {
  return api.get('/chat/agents');
};

/**
 * 清除会话历史
 */
export const clearChatHistory = (sessionId) => {
  return api.delete(`/chat/clear/${sessionId}`);
};

/**
 * 获取会话历史
 */
export const getChatHistory = (sessionId) => {
  return api.get(`/chat/history/${sessionId}`);
};

// ==================== 数据库 API ====================

/**
 * 获取数据库列表
 */
export const getDatabases = () => {
  return api.get('/database/databases');
};

/**
 * 获取表列表
 */
export const getTables = (database) => {
  return api.get(`/database/databases/${database}/tables`);
};

/**
 * 获取表结构
 */
export const getTableSchema = (database, table) => {
  return api.get(`/database/databases/${database}/tables/${table}/schema`);
};

/**
 * 获取元数据（简单版本，只包含表名）
 */
export const getMetadata = () => {
  return api.get('/database/metadata');
};

/**
 * 获取元数据（包含注释）
 */
export const getMetadataWithComments = () => {
  return api.get('/database/metadata-with-comments');
};

/**
 * 搜索表
 */
export const searchTables = (keyword) => {
  return api.get('/database/search/tables', {
    params: { keyword },
  });
};

// ==================== 系统 API ====================

/**
 * 获取系统信息
 */
export const getSystemInfo = () => {
  return api.get('/system/info');
};

/**
 * 健康检查
 */
export const healthCheck = () => {
  return api.get('/system/health');
};

/**
 * 获取工具列表
 */
export const getTools = () => {
  return api.get('/system/tools');
};

// ==================== WebSocket 连接 ====================

/**
 * 创建WebSocket连接
 */
export const createWebSocket = (sessionId) => {
  const token = localStorage.getItem('access_token');
  const wsUrl = API_BASE_URL.replace('http', 'ws').replace('/api/v1', '');
  return new WebSocket(`${wsUrl}/api/v1/chat/ws/${sessionId}?token=${token}`);
};

export default api;
