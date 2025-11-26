/**
 * 对话管理侧边栏组件
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  getConversations,
  createConversation,
  updateConversation,
  deleteConversation,
  clearConversationMessages,
} from '../services/api';
import '../assets/styles/ConversationSidebar.css';

const ConversationSidebar = ({ currentConversationId, onSelectConversation, onLogout }) => {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);

  // 加载对话列表
  const loadConversations = async () => {
    try {
      const response = await getConversations();
      setConversations(response.data.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  // 创建新对话
  const handleCreateConversation = async () => {
    try {
      const response = await createConversation({ title: '新对话' });
      const newConversation = response.data;
      setConversations([newConversation, ...conversations]);
      onSelectConversation(newConversation.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
      alert('创建对话失败，请重试');
    }
  };

  // 开始编辑标题
  const handleStartEdit = (conversation) => {
    setEditingId(conversation.id);
    setEditingTitle(conversation.title);
  };

  // 保存标题
  const handleSaveTitle = async (id) => {
    if (!editingTitle.trim()) {
      alert('对话标题不能为空');
      return;
    }

    try {
      await updateConversation(id, { title: editingTitle });
      setConversations(
        conversations.map((conv) =>
          conv.id === id ? { ...conv, title: editingTitle } : conv
        )
      );
      setEditingId(null);
    } catch (error) {
      console.error('Failed to update conversation:', error);
      alert('更新标题失败，请重试');
    }
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingTitle('');
  };

  // 删除对话
  const handleDeleteConversation = async (id) => {
    if (!confirm('确定要删除这个对话吗？')) {
      return;
    }

    try {
      await deleteConversation(id);
      setConversations(conversations.filter((conv) => conv.id !== id));

      // 如果删除的是当前对话，切换到第一个对话
      if (id === currentConversationId) {
        const remaining = conversations.filter((conv) => conv.id !== id);
        if (remaining.length > 0) {
          onSelectConversation(remaining[0].id);
        } else {
          onSelectConversation(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('删除对话失败，请重试');
    }
  };

  // 清除对话消息
  const handleClearMessages = async (id) => {
    if (!confirm('确定要清除这个对话的所有消息吗？')) {
      return;
    }

    try {
      await clearConversationMessages(id);
      alert('对话消息已清除');
    } catch (error) {
      console.error('Failed to clear messages:', error);
      alert('清除消息失败，请重试');
    }
  };

  // 格式化时间
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return '今天';
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric',
      });
    }
  };

  return (
    <div className="conversation-sidebar">
      {/* 顶部用户信息 */}
      <div className="sidebar-header">
        <div className="user-info" onClick={() => setShowUserMenu(!showUserMenu)}>
          <div className="user-avatar">
            {user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="user-details">
            <div className="user-email">{user?.email || '未登录'}</div>
          </div>
          <div className="user-menu-icon">▼</div>
        </div>

        {showUserMenu && (
          <div className="user-menu">
            <button onClick={onLogout} className="user-menu-item logout">
              退出登录
            </button>
          </div>
        )}
      </div>

      {/* 新建对话按钮 */}
      <button className="new-conversation-btn" onClick={handleCreateConversation}>
        <span className="plus-icon">+</span>
        新建对话
      </button>

      {/* 对话列表 */}
      <div className="conversations-list">
        {loading ? (
          <div className="loading-state">加载中...</div>
        ) : conversations.length === 0 ? (
          <div className="empty-state">
            <p>暂无对话</p>
            <p className="empty-hint">点击上方按钮创建新对话</p>
          </div>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`conversation-item ${
                conversation.id === currentConversationId ? 'active' : ''
              }`}
            >
              {editingId === conversation.id ? (
                <div className="edit-mode">
                  <input
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleSaveTitle(conversation.id);
                      }
                    }}
                    autoFocus
                  />
                  <div className="edit-actions">
                    <button
                      className="save-btn"
                      onClick={() => handleSaveTitle(conversation.id)}
                    >
                      ✓
                    </button>
                    <button className="cancel-btn" onClick={handleCancelEdit}>
                      ✕
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div
                    className="conversation-content"
                    onClick={() => onSelectConversation(conversation.id)}
                  >
                    <div className="conversation-title">{conversation.title}</div>
                    <div className="conversation-meta">
                      <span className="message-count">
                        {conversation.message_count || 0} 条消息
                      </span>
                      <span className="conversation-date">
                        {formatDate(conversation.updated_at)}
                      </span>
                    </div>
                  </div>
                  <div className="conversation-actions">
                    <button
                      className="action-btn"
                      onClick={() => handleStartEdit(conversation)}
                      title="重命名"
                    >
                      ✏️
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => handleClearMessages(conversation.id)}
                      title="清除消息"
                    >
                      🗑️
                    </button>
                    <button
                      className="action-btn delete"
                      onClick={() => handleDeleteConversation(conversation.id)}
                      title="删除对话"
                    >
                      ❌
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* 底部提示 */}
      <div className="sidebar-footer">
        <p className="footer-text">历史记录保留7天</p>
      </div>
    </div>
  );
};

export default ConversationSidebar;
