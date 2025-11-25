import { useState, useEffect, useRef } from 'react'
import './assets/styles/main.css'

// 导入组件
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'
import TypingIndicator from './components/TypingIndicator'
import TableSelector from './components/TableSelector'
import ContextBar from './components/ContextBar'

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '你好！我是智慧报表数据助手。\n\n我可以帮你分析数据库数据。请先使用表选择器选择要分析的表！',
      timestamp: new Date()
    }
  ])
  const [isTyping, setIsTyping] = useState(false)
  const [ws, setWs] = useState(null)
  const [sessionId] = useState(`session_${Date.now()}`)
  const [isConnected, setIsConnected] = useState(false)
  const [selectedTable, setSelectedTable] = useState(null)  // 当前选择的表
  const messagesEndRef = useRef(null)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // WebSocket连接
  useEffect(() => {
    connectWebSocket()
    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//localhost:8000/api/v1/chat/ws/${sessionId}`
      
      console.log('连接 WebSocket:', wsUrl)
      
      const websocket = new WebSocket(wsUrl)
      
      websocket.onopen = () => {
        console.log('✅ WebSocket连接成功')
        setWs(websocket)
        setIsConnected(true)
      }
      
      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        handleWebSocketMessage(data)
      }
      
      websocket.onerror = (error) => {
        console.error('❌ WebSocket错误:', error)
        setIsConnected(false)
      }
      
      websocket.onclose = () => {
        console.log('🔌 WebSocket连接关闭')
        setIsConnected(false)
        // 3秒后重连
        setTimeout(connectWebSocket, 3000)
      }
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      setIsConnected(false)
    }
  }

  const handleWebSocketMessage = (data) => {
    if (data.type === 'start') {
      setIsTyping(true)
    } else if (data.type === 'stream') {
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1]
        if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
          // 追加到最后一条消息
          return [
            ...prev.slice(0, -1),
            {
              ...lastMessage,
              content: lastMessage.content + data.content
            }
          ]
        } else {
          // 创建新消息
          return [
            ...prev,
            {
              role: 'assistant',
              content: data.content,
              timestamp: new Date(),
              isStreaming: true
            }
          ]
        }
      })
    } else if (data.type === 'end') {
      setIsTyping(false)
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1]
        if (lastMessage && lastMessage.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...lastMessage, isStreaming: false }
          ]
        }
        return prev
      })
    } else if (data.type === 'error') {
      setIsTyping(false)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `抱歉，出现错误：${data.content}`,
          timestamp: new Date()
        }
      ])
    }
  }

  const handleSendMessage = (message) => {
    // 如果没有选择表，提示用户
    if (!selectedTable) {
      alert('请先选择数据库和表！');
      return;
    }

    // 添加用户消息
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: message,
        timestamp: new Date()
      }
    ])

    // 通过WebSocket发送，包含agent_type和table_context
    if (ws && ws.readyState === WebSocket.OPEN) {
      const payload = {
        message,
        agent_type: 'chatbi',  // 固定使用chatbi
        table_context: selectedTable
      };

      ws.send(JSON.stringify(payload));
    } else {
      alert('连接已断开，正在重新连接...')
      connectWebSocket()
    }
  }

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
  }

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
  }

  const handleClearHistory = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/chat/clear/${sessionId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setMessages([
          {
            role: 'assistant',
            content: '对话历史已清除。请选择要分析的表，然后开始提问！',
            timestamp: new Date()
          }
        ])
        // 清除选择的表
        setSelectedTable(null)
      }
    } catch (error) {
      console.error('清除历史失败:', error)
      alert('清除历史失败，请检查后端是否运行')
    }
  }

  return (
    <div className="app">
      {/* 侧边栏 */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>📊 智慧报表数据助手</h1>
        </div>
        <div className="sidebar-content">
          <button className="clear-btn" onClick={handleClearHistory}>
            清除历史
          </button>
          {/* 未来可以在这里添加历史会话列表 */}
        </div>
      </div>

      {/* 主内容区 */}
      <div className="main-content">
        {/* 表选择器 - 只在未选择表时显示 */}
        {!selectedTable && (
          <TableSelector
            onTableSelect={handleTableSelect}
            selectedTable={selectedTable}
          />
        )}

        {/* 上下文显示条 - 只在选择了表时显示 */}
        <ContextBar
          selectedAgent="chatbi"
          selectedTable={selectedTable}
          onClear={handleClearTable}
        />

        {/* 消息区域 */}
        <div className="chat-messages">
          {/* 连接状态提示 */}
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
  )
}

export default App