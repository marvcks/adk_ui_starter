import React from 'react';
import { ToolCallPanel } from './ToolCallPanel';

export const ToolCallDemo: React.FC = () => {
  const demoData = [
    {
      toolName: 'search_molecule_database',
      status: 'completed',
      timestamp: new Date(),
      result: { molecules: ['C6H6', 'CH4', 'H2O'], count: 3 },
      inputParams: { query: 'organic molecules', limit: 10 }
    },
    {
      toolName: 'run_simulation',
      status: 'executing',
      timestamp: new Date(),
      isLongRunning: true,
      inputParams: { temperature: 300, pressure: 1.0 }
    },
    {
      toolName: 'analyze_results',
      status: 'error',
      timestamp: new Date(),
      result: { error: 'Invalid input parameters' },
      inputParams: { data: null }
    },
    {
      toolName: 'generate_report',
      status: 'pending',
      timestamp: new Date(),
      inputParams: { format: 'PDF', include_charts: true }
    }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-6">
        工具调用面板演示
      </h1>
      
      <div className="space-y-4">
        {demoData.map((demo, index) => (
          <ToolCallPanel
            key={index}
            toolName={demo.toolName}
            status={demo.status}
            isLongRunning={demo.isLongRunning}
            result={demo.result}
            timestamp={demo.timestamp}
            inputParams={demo.inputParams}
          />
        ))}
      </div>
      
      <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h2 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-2">
          功能说明
        </h2>
        <ul className="text-blue-700 dark:text-blue-300 space-y-1 text-sm">
          <li>• 点击面板标题可以展开/折叠详细内容</li>
          <li>• 展开的内容背景使用浅灰色，提供良好的视觉层次</li>
          <li>• 支持一键复制 JSON 内容到剪贴板</li>
          <li>• 根据执行状态显示不同的图标和颜色</li>
          <li>• 平滑的展开/折叠动画效果</li>
        </ul>
      </div>
    </div>
  );
}; 