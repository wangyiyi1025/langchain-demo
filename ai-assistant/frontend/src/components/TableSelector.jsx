import React, { useState, useEffect, useRef } from 'react';
import '../assets/styles/TableSelector.css';

const TableSelector = ({ onTableSelect, selectedTable }) => {
  const [inputValue, setInputValue] = useState('');
  const [metadata, setMetadata] = useState({});
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    // 获取数据库元数据
    fetchMetadata();
  }, []);

  useEffect(() => {
    // 当选择的表变化时，更新输入框
    if (selectedTable) {
      setInputValue(`#${selectedTable.database}.${selectedTable.table}`);
    }
  }, [selectedTable]);

  useEffect(() => {
    // 点击外部关闭下拉菜单
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        !inputRef.current.contains(event.target)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchMetadata = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/database/metadata');
      const data = await response.json();
      setMetadata(data);
    } catch (error) {
      console.error('获取数据库元数据失败:', error);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);

    // 解析输入内容
    if (value.startsWith('#')) {
      const query = value.slice(1).toLowerCase();
      const parts = query.split('.');

      let newSuggestions = [];

      if (parts.length === 1) {
        // 只输入了数据库名的一部分
        const dbQuery = parts[0];

        // 如果只输入了 '#'，显示所有数据库
        if (dbQuery === '') {
          Object.keys(metadata).forEach(db => {
            newSuggestions.push({
              type: 'database',
              display: `#${db}.`,
              database: db,
              description: `数据库 (${metadata[db].length} 个表)`
            });
          });
        } else {
          // 搜索匹配的数据库
          Object.keys(metadata).forEach(db => {
            if (db.toLowerCase().includes(dbQuery)) {
              newSuggestions.push({
                type: 'database',
                display: `#${db}.`,
                database: db,
                description: `数据库 (${metadata[db].length} 个表)`
              });
            }
          });
        }
      } else if (parts.length === 2) {
        // 输入了数据库名和表名的一部分
        const dbName = parts[0];
        const tableQuery = parts[1];

        Object.keys(metadata).forEach(db => {
          if (db.toLowerCase() === dbName.toLowerCase() || db.toLowerCase().includes(dbName.toLowerCase())) {
            const tables = metadata[db];

            // 如果表查询为空，显示所有表
            if (tableQuery === '') {
              tables.forEach(table => {
                newSuggestions.push({
                  type: 'table',
                  display: `#${db}.${table}`,
                  database: db,
                  table: table,
                  description: `${db}.${table}`
                });
              });
            } else {
              // 搜索匹配的表
              tables.forEach(table => {
                if (table.toLowerCase().includes(tableQuery)) {
                  newSuggestions.push({
                    type: 'table',
                    display: `#${db}.${table}`,
                    database: db,
                    table: table,
                    description: `${db}.${table}`
                  });
                }
              });
            }
          }
        });
      }

      setSuggestions(newSuggestions.slice(0, 10)); // 最多显示10个建议
      setShowDropdown(newSuggestions.length > 0);
      setSelectedIndex(0);
    } else {
      setShowDropdown(false);
      setSuggestions([]);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    if (suggestion.type === 'database') {
      // 如果点击的是数据库，显示该数据库下的所有表
      const newValue = suggestion.display;
      setInputValue(newValue);

      // 立即显示该数据库下的所有表
      const tables = metadata[suggestion.database] || [];
      const tableSuggestions = tables.map(table => ({
        type: 'table',
        display: `#${suggestion.database}.${table}`,
        database: suggestion.database,
        table: table,
        description: `${suggestion.database}.${table}`
      }));

      setSuggestions(tableSuggestions.slice(0, 10));
      setShowDropdown(tableSuggestions.length > 0);
      setSelectedIndex(0);
      inputRef.current.focus();
    } else {
      // 如果点击的是表，选择该表
      setInputValue(suggestion.display);
      setShowDropdown(false);
      onTableSelect({
        database: suggestion.database,
        table: suggestion.table
      });
    }
  };

  const handleKeyDown = (e) => {
    if (!showDropdown) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (suggestions[selectedIndex]) {
        handleSuggestionClick(suggestions[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  const handleClear = () => {
    setInputValue('');
    setSuggestions([]);
    setShowDropdown(false);
    onTableSelect(null);
    inputRef.current.focus();
  };

  return (
    <div className="table-selector">
      <div className="table-selector-input-wrapper">
        <span className="table-selector-icon">📊</span>
        <input
          ref={inputRef}
          type="text"
          className="table-selector-input"
          placeholder="输入 #数据库名.表名 来选择数据表"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) {
              setShowDropdown(true);
            }
          }}
        />
        {inputValue && (
          <button className="table-selector-clear" onClick={handleClear}>
            ✕
          </button>
        )}
      </div>

      {showDropdown && suggestions.length > 0 && (
        <div className="table-selector-dropdown" ref={dropdownRef}>
          {suggestions.map((suggestion, index) => (
            <div
              key={`${suggestion.database}-${suggestion.table || 'db'}`}
              className={`table-selector-item ${index === selectedIndex ? 'selected' : ''} ${suggestion.type}`}
              onClick={() => handleSuggestionClick(suggestion)}
            >
              <span className="item-icon">
                {suggestion.type === 'database' ? '🗄️' : '📋'}
              </span>
              <div className="item-content">
                <div className="item-display">{suggestion.display}</div>
                <div className="item-description">{suggestion.description}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TableSelector;
