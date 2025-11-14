import { useState, useEffect, useRef } from 'react'
import './assets/styles/main.css'

// 先导入组件，如果失败会报错
import ChatHeader from './components/ChatHeader'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'
import TypingIndicator from './components/TypingIndicator'

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '你好！我是你的AI助手，可以帮你：\n• 查询当前时间\n• 进行数学计算\n• 搜索网络信息\n• 查询天气\n有什么可以帮到你的吗？',
      timestamp: new Date()
    }
  ])
  const [isTyping, setIsTyping] = useState(false)
  const [ws, setWs] = useState(null)
  const [sessionId] = useState(`session_${Date.now()}`)
  const [isConnected, setIsConnected] = useState(false)
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
    // 添加用户消息
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: message,
        timestamp: new Date()
      }
    ])

    // 通过WebSocket发送
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message }))
    } else {
      alert('连接已断开，正在重新连接...')
      connectWebSocket()
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