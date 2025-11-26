/**
 * 主聊天页面组件
 * 包含对话管理侧边栏和聊天界面
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  createWebSocket,
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

  const handleWebSocketMessage = async (data) => {
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
          const finishedMessage = { ...lastMessage, isStreaming: false };

          // 保存助手回复到数据库
          if (currentConversationId) {
            addMessage(currentConversationId, {
              conversation_id: currentConversationId,
              role: 'assistant',
              content: finishedMessage.content
            }).catch(error => {
              console.error('保存助手消息失败:', error);
            });
          }

          return [
            ...prev.slice(0, -1),
            finishedMessage
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
      setCurrentConversationId(conversationId);

      if (!conversationId) {
        // 创建新对话
        const response = await createConversation({ title: '新对话' });
        const newConversationId = response.data.id;
        setCurrentConversationId(newConversationId);

        // 重置状态
        setMessages([{
          role: 'assistant',
          content: '你好！我是智慧报表数据助手。\n\n我可以帮你分析数据库数据。请先使用表选择器选择要分析的表！',
          timestamp: new Date()
        }]);
        setSelectedTable(null);
        return;
      }

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
