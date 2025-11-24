import React, { useMemo } from 'react'
import ChartRenderer from './ChartRenderer'

function ChatMessage({ message }) {
  const { role, content, timestamp } = message

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

  // 如果有 JSON 数据，格式化显示
  const formatJsonInfo = () => {
    if (!jsonData) return null

    const info = []

    if (jsonData.sql) {
      info.push(
        <div key="sql" className="message-sql">
          <strong>SQL 查询：</strong>
          <pre>{jsonData.sql}</pre>
        </div>
      )
    }

    if (jsonData.row_count !== undefined) {
      info.push(
        <div key="rowcount" className="message-info">
          返回 {jsonData.row_count} 行数据
        </div>
      )
    }

    if (jsonData.chart_suggestion) {
      const suggestion = jsonData.chart_suggestion
      info.push(
        <div key="suggestion" className="message-suggestion">
          <strong>图表建议：</strong>{suggestion.chart_type} - {suggestion.reason}
        </div>
      )
    }

    return info.length > 0 ? <div className="message-json-info">{info}</div> : null
  }

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        {textContent && formatContent(textContent)}
        {formatJsonInfo()}
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