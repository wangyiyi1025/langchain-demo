/**
 * 主聊天页面组件
 * 包含对话管理侧边栏和聊天界面
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { createWebSocket } from '../services/api';
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
  const [ws, setWs] = useState(null);
  const [sessionId] = useState(`session_${Date.now()}`);
  const [isConnected, setIsConnected] = useState(false);
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

  // WebSocket连接
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const websocket = createWebSocket(sessionId);

      websocket.onopen = () => {
        console.log('✅ WebSocket连接成功');
        setWs(websocket);
        setIsConnected(true);
      };

      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      websocket.onerror = (error) => {
        console.error('❌ WebSocket错误:', error);
        setIsConnected(false);
      };

      websocket.onclose = (event) => {
        console.log('🔌 WebSocket连接关闭', event.code, event.reason);
        setIsConnected(false);

        // 如果是认证错误(1008)，不自动重连，跳转到登录页
        if (event.code === 1008) {
          alert('认证失败，请重新登录');
          handleLogout();
        } else {
          // 其他错误，3秒后重连
          setTimeout(connectWebSocket, 3000);
        }
      };
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      setIsConnected(false);
    }
  };

  const handleWebSocketMessage = (data) => {
    if (data.type === 'start') {
      setIsTyping(true);
    } else if (data.type === 'stream') {
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMessage,
              content: lastMessage.content + data.content
            }
          ];
        } else {
          return [
            ...prev,
            {
              role: 'assistant',
              content: data.content,
              timestamp: new Date(),
              isStreaming: true
            }
          ];
        }
      });
    } else if (data.type === 'end') {
      setIsTyping(false);
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...lastMessage, isStreaming: false }
          ];
        }
        return prev;
      });
    } else if (data.type === 'error') {
      setIsTyping(false);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `抱歉，出现错误：${data.content}`,
          timestamp: new Date()
        }
      ]);
    }
  };

  const handleSendMessage = (message) => {
    if (!selectedTable) {
      alert('请先选择数据库和表！');
      return;
    }

    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: message,
        timestamp: new Date()
      }
    ]);

    if (ws && ws.readyState === WebSocket.OPEN) {
      const payload = {
        message,
        agent_type: 'chatbi',
        table_context: selectedTable
      };
      ws.send(JSON.stringify(payload));
    } else {
      alert('连接已断开，正在重新连接...');
      connectWebSocket();
    }
  };

  const handleTableSelect = (table) => {
    setSelectedTable(table);

    if (table) {
      const tableDisplay = table.comment
        ? `${table.comment} (${table.database}.${table.table})`
        : `${table.database}.${table.table}`;

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `已选择表：${tableDisplay}\n\n现在所有对话都将基于这个表进行分析。你可以开始提问了！`,
          timestamp: new Date()
        }
      ]);
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

  const handleSelectConversation = (conversationId) => {
    setCurrentConversationId(conversationId);
    // TODO: 加载对话的历史消息
    console.log('切换到对话:', conversationId);
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
          {!isConnected && (
            <div style={{
              padding: '10px',
              background: '#fff3cd',
              color: '#856404',
              borderRadius: '8px',
              marginBottom: '10px',
              textAlign: 'center'
            }}>
              ⚠️ 正在连接后端服务...
            </div>
          )}

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
