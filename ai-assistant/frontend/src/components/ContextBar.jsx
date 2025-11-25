import React from 'react';
import '../assets/styles/ContextBar.css';

const ContextBar = ({ selectedAgent, selectedTable }) => {
  if (!selectedTable || selectedAgent !== 'chatbi') {
    return null;
  }

  return (
    <div className="context-bar">
      <div className="context-badge">
        <span className="context-icon">📊</span>
        <span className="context-label">当前分析表：</span>
        <span className="context-value">
          {selectedTable.comment || `${selectedTable.database}.${selectedTable.table}`}
        </span>
        {selectedTable.comment && (
          <span className="context-subvalue">
            {selectedTable.database}.{selectedTable.table}
          </span>
        )}
      </div>
      <div className="context-hint">
        所有对话将基于此表进行分析
      </div>
    </div>
  );
};

export default ContextBar;
