import { useState, useEffect, useRef } from 'react'
import './assets/styles/main.css'

// 导入组件
import ChatHeader from './components/ChatHeader'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'
import TypingIndicator from './components/TypingIndicator'
import AgentSelector from './components/AgentSelector'
import TableSelector from './components/TableSelector'
import ContextBar from './components/ContextBar'

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '你好！我是你的AI智能助手。\n\n🔹 切换到"ChatBI数据分析助手"可以进行数据库查询和分析\n🔹 切换到"通用聊天助手"可以进行日常对话\n\n请选择一个助手开始使用！',
      timestamp: new Date()
    }
  ])
  const [isTyping, setIsTyping] = useState(false)
  const [ws, setWs] = useState(null)
  const [sessionId] = useState(`session_${Date.now()}`)
  const [isConnected, setIsConnected] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState('chat')  // 当前选择的Agent
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
    // 如果选择了ChatBI但没有选择表，提示用户
    if (selectedAgent === 'chatbi' && !selectedTable) {
      alert('请先选择数据库和表！使用表选择器输入 #数据库名.表名');
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
        agent_type: selectedAgent
      };

      // 如果选择了表，添加表上下文
      if (selectedTable && selectedAgent === 'chatbi') {
        payload.table_context = selectedTable;
      }

      ws.send(JSON.stringify(payload));
    } else {
      alert('连接已断开，正在重新连接...')
      connectWebSocket()
    }
  }

  const handleAgentChange = (agentType) => {
    setSelectedAgent(agentType);

    // 切换Agent时添加提示消息
    const agentName = agentType === 'chat' ? '通用聊天助手' : 'ChatBI数据分析助手';
    const tips = agentType === 'chat'
      ? '我可以帮你查询时间、进行计算、搜索信息等。'
      : '我可以帮你分析数据库数据。请先使用表选择器选择要分析的表！';

    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        content: `已切换到 ${agentName}。\n\n${tips}`,
        timestamp: new Date()
      }
    ]);
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

  const handleClearHistory = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/chat/clear/${sessionId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setMessages([
          {
            role: 'assistant',
            content: '对话历史已清除，让我们重新开始吧！',
            timestamp: new Date()
          }
        ])
      }
    } catch (error) {
      console.error('清除历史失败:', error)
      alert('清除历史失败，请检查后端是否运行')
    }
  }

  return (
    <div className="app">
      <div className="chat-container">
        <ChatHeader onClearHistory={handleClearHistory} />

        {/* Agent选择器 */}
        <AgentSelector
          selectedAgent={selectedAgent}
          onAgentChange={handleAgentChange}
        />

        {/* 表选择器 - 只在ChatBI模式下显示 */}
        {selectedAgent === 'chatbi' && (
          <TableSelector
            onTableSelect={handleTableSelect}
            selectedTable={selectedTable}
          />
        )}

        {/* 上下文显示条 - 只在ChatBI模式且选择了表时显示 */}
        <ContextBar
          selectedAgent={selectedAgent}
          selectedTable={selectedTable}
        />

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

        <ChatInput onSendMessage={handleSendMessage} />
      </div>
    </div>
  )
}

export default App