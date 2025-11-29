import React, { useMemo, useState } from 'react'
import ChartRenderer from './ChartRenderer'

function ChatMessage({ message }) {
  const { role, content, timestamp } = message
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)

  // 尝试从内容中提取 JSON 数据（包括 chart_config）
  const { textContent, chartConfig, jsonData } = useMemo(() => {
    try {
      // 尝试查找 JSON 代码块
      const jsonBlockRegex = /```json\s*([\s\S]*?)\s*```/g
      const matches = [...content.matchAll(jsonBlockRegex)]

      if (matches.length > 0) {
        // 提取最后一个 JSON 块
        const jsonStr = matches[matches.length - 1][1]
        const parsed = JSON.parse(jsonStr)

        // 移除 JSON 代码块，保留其他文本
        const textOnly = content.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()

        return {
          textContent: textOnly,
          chartConfig: parsed.chart_config || null,
          jsonData: parsed
        }
      }

      // 如果没有代码块，尝试直接解析整个内容
      const parsed = JSON.parse(content)
      return {
        textContent: '',
        chartConfig: parsed.chart_config || null,
        jsonData: parsed
      }
    } catch (e) {
      // 不是 JSON 格式，返回原始内容
      return {
        textContent: content,
        chartConfig: null,
        jsonData: null
      }
    }
  }, [content])

  const formatContent = (text) => {
    if (!text) return null

    // 简单的markdown解析：换行
    return text.split('\n').map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < text.split('\n').length - 1 && <br />}
      </React.Fragment>
    ))
  }

  // 检查是否有 SQL 详情（SQL、解释、图表建议）
  const hasSqlDetails = () => {
    if (!jsonData) return false
    return jsonData.sql || jsonData.sql_explanation || jsonData.chart_suggestion
  }

  // 渲染 SQL 详情区域（可折叠）
  const renderSqlDetails = () => {
    if (!hasSqlDetails()) return null

    const details = []

    // SQL 查询
    if (jsonData.sql) {
      details.push(
        <div key="sql" className="sql-detail-item">
          <strong>SQL 查询：</strong>
          <pre>{jsonData.sql}</pre>
        </div>
      )
    }

    // SQL 解释（新增）
    if (jsonData.sql_explanation) {
      details.push(
        <div key="explanation" className="sql-detail-item">
          <strong>查询说明：</strong>
          <div className="sql-explanation">{jsonData.sql_explanation}</div>
        </div>
      )
    }

    // 图表建议
    if (jsonData.chart_suggestion) {
      const suggestion = jsonData.chart_suggestion
      details.push(
        <div key="suggestion" className="sql-detail-item">
          <strong>图表建议：</strong>
          <span>{suggestion.chart_type} - {suggestion.reason}</span>
        </div>
      )
    }

    return (
      <div className="sql-details-container">
        <button
          className="sql-details-toggle"
          onClick={() => setIsDetailsOpen(!isDetailsOpen)}
        >
          {isDetailsOpen ? '▼' : '▶'} SQL详情
        </button>
        {isDetailsOpen && (
          <div className="sql-details-content">
            {details}
          </div>
        )}
      </div>
    )
  }

  // 如果有其他 JSON 数据（如 row_count），单独显示
  const formatOtherJsonInfo = () => {
    if (!jsonData) return null

    const info = []

    if (jsonData.row_count !== undefined) {
      info.push(
        <div key="rowcount" className="message-info">
          返回 {jsonData.row_count} 行数据
        </div>
      )
    }

    return info.length > 0 ? <div className="message-json-info">{info}</div> : null
  }

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        {textContent && formatContent(textContent)}
        {formatOtherJsonInfo()}
        {renderSqlDetails()}
        {chartConfig && <ChartRenderer chartConfig={chartConfig} />}
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