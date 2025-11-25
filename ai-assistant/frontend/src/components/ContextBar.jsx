import React from 'react';
import '../assets/styles/ContextBar.css';

const ContextBar = ({ selectedAgent, selectedTable, onClear }) => {
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
      <button className="context-clear-btn" onClick={onClear} title="重新选择表">
        ✕
      </button>
    </div>
  );
};

export default ContextBar;
