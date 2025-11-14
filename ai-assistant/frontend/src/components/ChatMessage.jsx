import React from 'react'

function ChatMessage({ message }) {
  const { role, content, timestamp } = message
  
  const formatContent = (text) => {
    // 简单的markdown解析：换行
    return text.split('\n').map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < text.split('\n').length - 1 && <br />}
      </React.Fragment>
    ))
  }
  
  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        {formatContent(content)}
      </div>
      {timestamp && (
        <div className="message-time">
          {new Date(timestamp).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      )}
    </div>
  )
}

export default ChatMessage