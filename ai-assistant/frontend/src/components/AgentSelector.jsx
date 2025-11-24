import React, { useState, useEffect } from 'react';
import '../assets/styles/AgentSelector.css';

const AgentSelector = ({ selectedAgent, onAgentChange }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 从后端获取Agent列表
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/agents');
      const data = await response.json();
      setAgents(data);
      setLoading(false);
    } catch (error) {
      console.error('获取Agent列表失败:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="agent-selector-loading">加载Agent列表...</div>;
  }

  return (
    <div className="agent-selector">
      <label className="agent-selector-label">选择助手：</label>
      <div className="agent-selector-options">
        {agents.map((agent) => (
          <button
            key={agent.type}
            className={`agent-option ${selectedAgent === agent.type ? 'active' : ''}`}
            onClick={() => onAgentChange(agent.type)}
            title={agent.description}
          >
            <span className="agent-icon">
              {agent.type === 'chat' ? '💬' : '📊'}
            </span>
            <span className="agent-name">{agent.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default AgentSelector;
