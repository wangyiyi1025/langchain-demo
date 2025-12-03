import React from 'react';

/**
 * Agent执行步骤显示组件
 * 显示Agent在执行过程中的每一步
 */
const AgentSteps = ({ steps = [] }) => {
  if (!steps || steps.length === 0) {
    return null;
  }

  // 获取步骤状态图标
  const getStepIcon = (status) => {
    switch (status) {
      case 'completed':
        return <span style={{ color: '#10b981', fontSize: '18px' }}>✓</span>;
      case 'executing':
        return <span style={{ color: '#3b82f6', fontSize: '18px' }} className="rotating">⟳</span>;
      case 'failed':
        return <span style={{ color: '#ef4444', fontSize: '18px' }}>✗</span>;
      default:
        return <span style={{ color: '#d1d5db', fontSize: '18px' }}>○</span>;
    }
  };

  // 获取步骤状态文本颜色
  const getStepTextColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-700';
      case 'executing':
        return 'text-blue-700';
      case 'failed':
        return 'text-red-700';
      default:
        return 'text-gray-500';
    }
  };

  // 获取友好的工具名称
  const getToolDisplayName = (toolName) => {
    const toolNameMap = {
      'chatbi_query_only_chain': '查询数据',
      'chatbi_query_with_analysis_chain': '查询+分析',
      'chatbi_query_with_chart_chain': '查询+可视化',
      'chatbi_full_analysis_chain': '完整分析',
      'get_schema_info': '获取表结构',
      'nl_to_sql': '生成SQL',
      'execute_sql': '执行SQL',
      'analyze_data': '分析数据',
      'suggest_chart': '推荐图表',
      'generate_chart_config': '生成图表配置',
      'get_current_time': '获取当前时间',
      'get_date_info': '获取日期信息'
    };
    return toolNameMap[toolName] || toolName;
  };

  // 格式化输入文本（截取前100个字符）
  const formatInput = (input) => {
    if (!input) return '';
    const inputStr = typeof input === 'string' ? input : JSON.stringify(input);
    return inputStr.length > 100 ? inputStr.substring(0, 100) + '...' : inputStr;
  };

  return (
    <>
      <style>{`
        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .rotating {
          display: inline-block;
          animation: rotate 1s linear infinite;
        }
      `}</style>
      <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center mb-3">
          <h4 className="text-sm font-semibold text-gray-700">执行步骤</h4>
          <span className="ml-2 text-xs text-gray-500">({steps.length} 步)</span>
        </div>

        <div className="space-y-2">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex items-start space-x-3 p-3 bg-white rounded border border-gray-100 hover:border-gray-300 transition-colors"
            >
              {/* 步骤图标 */}
              <div className="flex-shrink-0 mt-0.5">
                {getStepIcon(step.status)}
              </div>

              {/* 步骤内容 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-medium text-gray-500">
                      步骤 {step.step_number}
                    </span>
                    <span className={`text-sm font-medium ${getStepTextColor(step.status)}`}>
                      {getToolDisplayName(step.tool_name)}
                    </span>
                  </div>
                  {step.duration_ms !== null && step.duration_ms !== undefined && (
                    <span className="text-xs text-gray-400">
                      {step.duration_ms}ms
                    </span>
                  )}
                </div>

                {/* 输入信息 */}
                {step.input && (
                  <div className="text-xs text-gray-600 mb-1">
                    <span className="font-medium">输入: </span>
                    <span className="text-gray-500">{formatInput(step.input)}</span>
                  </div>
                )}

                {/* 输出预览 */}
                {step.output_preview && step.status === 'completed' && (
                  <div className="text-xs text-gray-600">
                    <span className="font-medium">输出: </span>
                    <span className="text-gray-500">{step.output_preview}</span>
                  </div>
                )}

                {/* 错误信息 */}
                {step.error && step.status === 'failed' && (
                  <div className="text-xs text-red-600 mt-1">
                    <span className="font-medium">错误: </span>
                    <span>{step.error}</span>
                  </div>
                )}

                {/* 执行中状态 */}
                {step.status === 'executing' && (
                  <div className="text-xs text-blue-600">
                    执行中...
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

export default AgentSteps;
