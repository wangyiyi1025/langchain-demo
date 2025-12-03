/**
 * 主聊天页面组件
 * 包含对话管理侧边栏和聊天界面
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  sendMessage,
  getConversation,
  addMessage,
  updateConversationTable,
  createConversation
} from '../services/api';
import ConversationSidebar from '../components/ConversationSidebar';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TypingIndicator from '../components/TypingIndicator';
import TableSelector from '../components/TableSelector';
import ContextBar from '../components/ContextBar';
import '../assets/styles/main.css';

function ChatPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '你好！我是智慧报表数据助手。\n\n我可以帮你分析数据库数据。请先使用表选择器选择要分析的表！',
      timestamp: new Date()
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedTable, setSelectedTable] = useState(null);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSendMessage = async (message) => {
    if (!selectedTable) {
      alert('请先选择数据库和表！');
      return;
    }

    if (!currentConversationId) {
      alert('请先创建或选择一个对话！');
      return;
    }

    // 添加用户消息到本地状态
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: message,
        timestamp: new Date()
      }
    ]);

    // 保存用户消息到数据库
    try {
      await addMessage(currentConversationId, {
        conversation_id: currentConversationId,
        role: 'user',
        content: message
      });
    } catch (error) {
      console.error('保存用户消息失败:', error);
    }

    // 显示加载状态
    setIsTyping(true);

    try {
      // 调用非流式 API
      const response = await sendMessage({
        message,
        session_id: String(currentConversationId),
        stream: false,
        agent_type: 'chatbi',
        table_context: selectedTable
      });

      // 隐藏加载状态
      setIsTyping(false);

      // 添加助手回复到本地状态
      const assistantMessage = {
        role: 'assistant',
        content: response.data.message,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // 保存助手消息到数据库
      await addMessage(currentConversationId, {
        conversation_id: currentConversationId,
        role: 'assistant',
        content: response.data.message
      });

    } catch (error) {
      setIsTyping(false);
      console.error('发送消息失败:', error);

      // 显示错误消息
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `抱歉，出现错误：${error.response?.data?.detail || error.message || '未知错误'}`,
          timestamp: new Date()
        }
      ]);
    }
  };

  const handleTableSelect = async (table) => {
    setSelectedTable(table);

    if (table) {
      const tableDisplay = table.comment
        ? `${table.comment} (${table.database}.${table.table})`
        : `${table.database}.${table.table}`;

      const assistantMessage = {
        role: 'assistant',
        content: `已选择表：${tableDisplay}\n\n现在所有对话都将基于这个表进行分析。你可以开始提问了！`,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // 保存选中的表到数据库
      if (currentConversationId) {
        try {
          await updateConversationTable(currentConversationId, table);

          // 保存助手消息到数据库
          await addMessage(currentConversationId, {
            conversation_id: currentConversationId,
            role: 'assistant',
            content: assistantMessage.content
          });
        } catch (error) {
          console.error('保存选中表失败:', error);
        }
      }
    }
  };

  const handleClearTable = () => {
    setSelectedTable(null);
    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        content: '已取消表选择。请重新选择要分析的表。',
        timestamp: new Date()
      }
    ]);
  };

  const handleSelectConversation = async (conversationId) => {
    try {
      if (!conversationId) {
        // 清空当前对话（新建对话在ConversationSidebar中处理）
        setCurrentConversationId(null);
        setMessages([{
          role: 'assistant',
          content: '你好！我是智慧报表数据助手。\n\n我可以帮你分析数据库数据。请先使用表选择器选择要分析的表！',
          timestamp: new Date()
        }]);
        setSelectedTable(null);
        return;
      }

      setCurrentConversationId(conversationId);

      // 加载对话的历史消息和选中的表
      const response = await getConversation(conversationId);
      const conversation = response.data;

      // 恢复消息历史
      if (conversation.messages && conversation.messages.length > 0) {
        const formattedMessages = conversation.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at)
        }));
        setMessages(formattedMessages);
      } else {
        // 如果没有历史消息，显示默认欢迎消息
        setMessages([{
          role: 'assistant',
          content: '你好！我是智慧报表数据助手。\n\n我可以帮你分析数据库数据。请先使用表选择器选择要分析的表！',
          timestamp: new Date()
        }]);
      }

      // 恢复选中的表
      if (conversation.selected_table) {
        setSelectedTable(conversation.selected_table);
      } else {
        setSelectedTable(null);
      }
    } catch (error) {
      console.error('加载对话失败:', error);
      alert('加载对话失败');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="app">
      {/* 对话管理侧边栏 */}
      <ConversationSidebar
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onLogout={handleLogout}
      />

      {/* 主内容区 */}
      <div className="main-content">
        {/* 表选择器 */}
        {!selectedTable && (
          <TableSelector
            onTableSelect={handleTableSelect}
            selectedTable={selectedTable}
          />
        )}

        {/* 上下文显示条 */}
        <ContextBar
          selectedAgent="chatbi"
          selectedTable={selectedTable}
          onClear={handleClearTable}
        />

        {/* 消息区域 */}
        <div className="chat-messages">
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <ChatInput onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
}

export default ChatPage;
