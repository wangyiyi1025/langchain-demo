import React from 'react'

function ChatHeader({ onClearHistory }) {
  const handleClear = () => {
    if (window.confirm('确定要清除所有对话历史吗？')) {
      onClearHistory()
    }
  }

  return (
    <div className="chat-header">
      <div className="header-left">
        <h1>🤖 AI智能助手</h1>
      </div>
      <button className="clear-btn" onClick={handleClear}>
        清除历史
      </button>
    </div>
  )
}

export default ChatHeader