import React from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, ScatterChart, Scatter,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell
} from 'recharts'

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0', '#ffb366']

function ChartRenderer({ chartConfig }) {
  if (!chartConfig || !chartConfig.type) {
    return null
  }

  const { type, title, data, x_axis, y_axis, label_field, value_field } = chartConfig

  // 调试信息
  console.log('ChartRenderer - chartConfig:', chartConfig)
  console.log('ChartRenderer - data:', data)
  console.log('ChartRenderer - x_axis:', x_axis, 'y_axis:', y_axis)

  // 如果数据为空，显示提示
  if (!data || data.length === 0) {
    return (
      <div className="chart-container">
        <h3 className="chart-title">{title || '数据图表'}</h3>
        <div className="chart-empty">暂无数据</div>
      </div>
    )
  }

  // 验证数据字段
  if (data.length > 0) {
    const firstRow = data[0]
    console.log('ChartRenderer - 第一行数据:', firstRow)
    console.log('ChartRenderer - 数据字段:', Object.keys(firstRow))

    // 检查必需的字段是否存在
    if (x_axis && !(x_axis in firstRow)) {
      console.warn(`警告: x_axis 字段 "${x_axis}" 不存在于数据中`)
    }
    if (y_axis && !(y_axis in firstRow)) {
      console.warn(`警告: y_axis 字段 "${y_axis}" 不存在于数据中`)
    }
  }

  // 渲染表格
  const renderTable = () => {
    const columns = Object.keys(data[0])
    return (
      <div className="chart-table-container">
        <h3 className="chart-title">{title || '数据表格'}</h3>
        <div className="chart-table-wrapper">
          <table className="chart-table">
            <thead>
              <tr>
                {columns.map((col, idx) => (
                  <th key={idx}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {columns.map((col, colIdx) => (
                    <td key={colIdx}>{row[col]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // 渲染柱状图
  const renderBarChart = () => {
    // 格式化日期显示
    const formatXAxis = (value) => {
      if (!value) return ''
      // 如果是 ISO 日期格式，只显示日期部分
      if (typeof value === 'string' && value.includes('T')) {
        return value.split('T')[0]
      }
      return value
    }

    // 支持单个或多个 y_axis
    const yAxisFields = Array.isArray(y_axis) ? y_axis : [y_axis]

    return (
      <div className="chart-container">
        <h3 className="chart-title">{title || '柱状图'}</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={x_axis}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={0}
              tickFormatter={formatXAxis}
            />
            <YAxis />
            <Tooltip
              labelFormatter={formatXAxis}
            />
            <Legend />
            {yAxisFields.map((field, index) => (
              <Bar
                key={field}
                dataKey={field}
                fill={COLORS[index % COLORS.length]}
                name={field}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // 渲染折线图
  const renderLineChart = () => {
    const formatXAxis = (value) => {
      if (!value) return ''
      if (typeof value === 'string' && value.includes('T')) {
        return value.split('T')[0]
      }
      return value
    }

    // 支持单个或多个 y_axis
    const yAxisFields = Array.isArray(y_axis) ? y_axis : [y_axis]

    return (
      <div className="chart-container">
        <h3 className="chart-title">{title || '折线图'}</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={x_axis}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={0}
              tickFormatter={formatXAxis}
            />
            <YAxis />
            <Tooltip
              labelFormatter={formatXAxis}
            />
            <Legend />
            {yAxisFields.map((field, index) => (
              <Line
                key={field}
                type="monotone"
                dataKey={field}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                name={field}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // 渲染饼图
  const renderPieChart = () => {
    const labelKey = label_field || x_axis
    const valueKey = value_field || y_axis

    return (
      <div className="chart-container">
        <h3 className="chart-title">{title || '饼图'}</h3>
        <ResponsiveContainer width="100%" height={400}>
          <PieChart>
            <Pie
              data={data}
              dataKey={valueKey}
              nameKey={labelKey}
              cx="50%"
              cy="50%"
              outerRadius={120}
              label={(entry) => `${entry[labelKey]}: ${entry[valueKey]}`}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // 渲染散点图
  const renderScatterChart = () => (
    <div className="chart-container">
      <h3 className="chart-title">{title || '散点图'}</h3>
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={x_axis}
            type="number"
            name={x_axis}
            angle={-45}
            textAnchor="end"
            height={100}
          />
          <YAxis dataKey={y_axis} type="number" name={y_axis} />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
          <Legend />
          <Scatter name="数据点" data={data} fill="#8884d8" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )

  // 渲染面积图
  const renderAreaChart = () => {
    const formatXAxis = (value) => {
      if (!value) return ''
      if (typeof value === 'string' && value.includes('T')) {
        return value.split('T')[0]
      }
      return value
    }

    // 支持单个或多个 y_axis
    const yAxisFields = Array.isArray(y_axis) ? y_axis : [y_axis]

    return (
      <div className="chart-container">
        <h3 className="chart-title">{title || '面积图'}</h3>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={x_axis}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={0}
              tickFormatter={formatXAxis}
            />
            <YAxis />
            <Tooltip
              labelFormatter={formatXAxis}
            />
            <Legend />
            {yAxisFields.map((field, index) => (
              <Area
                key={field}
                type="monotone"
                dataKey={field}
                stroke={COLORS[index % COLORS.length]}
                fill={COLORS[index % COLORS.length]}
                fillOpacity={0.6}
                name={field}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // 渲染热力图（使用表格样式模拟）
  const renderHeatmap = () => {
    // 简化的热力图实现 - 使用颜色深浅表示数值
    const columns = Object.keys(data[0])
    const numericColumns = columns.filter(col => typeof data[0][col] === 'number')

    // 计算数值范围用于颜色映射
    const getColorIntensity = (value, col) => {
      const values = data.map(row => row[col]).filter(v => typeof v === 'number')
      const min = Math.min(...values)
      const max = Math.max(...values)
      const intensity = (value - min) / (max - min)
      return `rgba(136, 132, 216, ${0.2 + intensity * 0.6})`
    }

    return (
      <div className="chart-container">
        <h3 className="chart-title">{title || '热力图'}</h3>
        <div className="chart-table-wrapper">
          <table className="chart-table heatmap">
            <thead>
              <tr>
                {columns.map((col, idx) => (
                  <th key={idx}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {columns.map((col, colIdx) => (
                    <td
                      key={colIdx}
                      style={{
                        backgroundColor: typeof row[col] === 'number'
                          ? getColorIntensity(row[col], col)
                          : 'transparent'
                      }}
                    >
                      {row[col]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // 根据图表类型渲染对应的图表
  switch (type) {
    case 'bar':
      return renderBarChart()
    case 'line':
      return renderLineChart()
    case 'pie':
      return renderPieChart()
    case 'scatter':
      return renderScatterChart()
    case 'area':
      return renderAreaChart()
    case 'table':
      return renderTable()
    case 'heatmap':
      return renderHeatmap()
    default:
      return (
        <div className="chart-container">
          <h3 className="chart-title">{title || '图表'}</h3>
          <div className="chart-empty">不支持的图表类型: {type}</div>
        </div>
      )
  }
}

export default ChartRenderer
