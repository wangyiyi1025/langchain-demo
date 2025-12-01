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
        try {
          const parsed = JSON.parse(jsonStr)

          // 移除 JSON 代码块，保留其他文本
          const textOnly = content.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()

          return {
            textContent: textOnly,
            chartConfig: parsed.chart_config || null,
            jsonData: parsed
          }
        } catch (parseError) {
          console.error('JSON 解析失败:', parseError)
          console.error('JSON 字符串:', jsonStr.substring(0, 500)) // 只打印前500个字符避免控制台过长
          // 解析失败时，返回原始内容
          return {
            textContent: content,
            chartConfig: null,
            jsonData: null
          }
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
      // 不是 JSON 格式，返回原始内容（这是正常情况，不需要打印错误）
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

  // 检查是否有分析详情（SQL、解释、图表建议等 - 不包括仅有 row_count 的情况）
  const hasAnalysisDetails = () => {
    if (!jsonData) return false
    // 如果只有 row_count 但是 scenario 是 table_schema 或 database_schema，不显示分析详情
    if (jsonData.scenario === 'table_schema' || jsonData.scenario === 'database_schema') {
      return false
    }
    // 其他情况，有 SQL 或解释或图表建议时才显示
    return jsonData.sql || jsonData.sql_explanation || jsonData.chart_suggestion
  }

  // 渲染数据洞察（来自 analyze_data 工具）
  const renderDataInsights = () => {
    if (!jsonData || !jsonData.analysis) return null

    const { insights, summary, characteristics } = jsonData.analysis

    // 如果 analysis 对象为空或没有任何有效内容，则不渲染
    if (!insights && !summary && !characteristics) return null

    return (
      <div className="data-insights">
        {summary && (
          <div className="insight-summary">
            <strong>📊 数据摘要：</strong>
            <p>{summary}</p>
          </div>
        )}

        {insights && Array.isArray(insights) && insights.length > 0 && (
          <div className="insight-items">
            <strong>💡 关键洞察：</strong>
            <ul>
              {insights.map((insight, idx) => (
                <li key={idx}>{insight}</li>
              ))}
            </ul>
          </div>
        )}

        {characteristics && Object.keys(characteristics).length > 0 && (
          <div className="insight-characteristics">
            <strong>📈 数据特征：</strong>
            <ul>
              {characteristics.total_records && (
                <li>总记录数：{characteristics.total_records}</li>
              )}
              {characteristics.key_metrics && Object.entries(characteristics.key_metrics).map(([key, value]) => (
                <li key={key}>{key}：{value}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  // 渲染分析详情区域（可折叠）
  const renderAnalysisDetails = () => {
    if (!hasAnalysisDetails()) return null

    const details = []

    // 返回数据行数（放在第一位）
    if (jsonData.row_count !== undefined) {
      details.push(
        <div key="rowcount" className="analysis-detail-item">
          <strong>数据行数：</strong>
          <span>返回 {jsonData.row_count} 行数据</span>
        </div>
      )
    }

    // SQL 查询
    if (jsonData.sql) {
      details.push(
        <div key="sql" className="analysis-detail-item">
          <strong>SQL 查询：</strong>
          <pre>{jsonData.sql}</pre>
        </div>
      )
    }

    // SQL 解释
    if (jsonData.sql_explanation) {
      details.push(
        <div key="explanation" className="analysis-detail-item">
          <strong>查询说明：</strong>
          <div className="sql-explanation">{jsonData.sql_explanation}</div>
        </div>
      )
    }

    // 图表建议
    if (jsonData.chart_suggestion) {
      const suggestion = jsonData.chart_suggestion
      details.push(
        <div key="suggestion" className="analysis-detail-item">
          <strong>图表建议：</strong>
          <span>{suggestion.chart_type} - {suggestion.reason}</span>
        </div>
      )
    }

    return (
      <div className="analysis-details-container">
        <button
          className="analysis-details-toggle"
          onClick={() => setIsDetailsOpen(!isDetailsOpen)}
        >
          {isDetailsOpen ? '▼' : '▶'} 分析详情
        </button>
        {isDetailsOpen && (
          <div className="analysis-details-content">
            {details}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        {textContent && formatContent(textContent)}
        {renderDataInsights()}
        {renderAnalysisDetails()}
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