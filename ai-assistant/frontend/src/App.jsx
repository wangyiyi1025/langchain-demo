/**
 * 主应用组件
 * 配置路由和认证
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import ChatPage from './pages/ChatPage';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* 登录页面 */}
          <Route path="/login" element={<Login />} />

          {/* 主聊天页面（需要认证） */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />

          {/* 其他路径重定向到首页 */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
