import React, { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle, Clock, AlertCircle, Wrench, Copy, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ToolCallPanelProps {
  toolName: string;
  status: string;
  isLongRunning?: boolean;
  result?: any;
  timestamp: Date;
  inputParams?: any;
}

export const ToolCallPanel: React.FC<ToolCallPanelProps> = ({
  toolName,
  status,
  isLongRunning = false,
  result,
  timestamp,
  inputParams
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  // 特殊处理：transfer_to_agent 不展示参数和返回内容
  const isTransferToAgent = toolName === 'transfer_to_agent';

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'executing':
        return <Clock className="w-5 h-5 text-blue-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Wrench className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'completed':
        return '执行完成';
      case 'executing':
        return isLongRunning ? '长时间运行中' : '正在执行';
      case 'error':
        return '执行失败';
      default:
        return '等待执行';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'executing':
        return 'text-blue-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const formatJson = (data: any) => {
    try {
      if (typeof data === 'string') {
        // 尝试解析为JSON，如果失败则返回原字符串
        try {
          const parsed = JSON.parse(data);
          return JSON.stringify(parsed, null, 2);
        } catch {
          return data;
        }
      }
      if (data && typeof data === 'object') {
        return JSON.stringify(data, null, 2);
      }
      return String(data);
    } catch {
      return String(data);
    }
  };

  const renderJsonContent = (data: any) => {
    if (!data) {
      return (
        <div className="text-sm text-gray-500 dark:text-gray-400 italic">
          无数据
        </div>
      );
    }

    // 特殊处理：提取 TextContent 中的 text 内容
    const extractTextContent = (content: any): string => {
      if (typeof content === 'string') {
        try {
          const parsed = JSON.parse(content);
          return extractTextContent(parsed);
        } catch {
          return content;
        }
      }
      
      if (content && typeof content === 'object') {
        // 检查是否是 TextContent 结构
        if (content.type === 'text' && content.text) {
          return content.text;
        }
        
        // 检查是否包含 content 数组
        if (Array.isArray(content.content)) {
          const textParts = content.content
            .filter((item: any) => item.type === 'text' && item.text)
            .map((item: any) => item.text)
            .join('\n');
          if (textParts) {
            return textParts;
          }
        }
        
        // 检查是否包含 result 字段
        if (content.result) {
          return extractTextContent(content.result);
        }
        
        // 如果没有找到 TextContent，返回原始内容的格式化版本
        return JSON.stringify(content, null, 2);
      }
      
      return String(content);
    };

    const extractedText = extractTextContent(data);
    
    // 如果是JSON字符串，进行语法高亮
    if (typeof extractedText === 'string' && (extractedText.startsWith('{') || extractedText.startsWith('['))) {
      try {
        const parsed = JSON.parse(extractedText);
        return (
          <pre className="text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        );
      } catch {
        return (
          <pre className="text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
            {extractedText}
          </pre>
        );
      }
    }
    
    // 如果不是JSON格式，直接显示
    return (
      <pre className="text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
        {extractedText}
      </pre>
    );
  };

  return (
    <div className="w-full">
      {/* 可折叠的面板标题 */}
      <div
        className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-t-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <div className={`font-medium ${getStatusColor()}`}>
              {getStatusText()}: {toolName}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {timestamp.toLocaleTimeString('zh-CN')}
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </div>
      </div>

      {/* 展开的内容 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="bg-gray-100 dark:bg-gray-700 border-l border-r border-b border-gray-200 dark:border-gray-700 rounded-b-lg">
              {/* 输入参数部分 - 只在执行中显示，且不是 transfer_to_agent */}
              {status === 'executing' && !isTransferToAgent && (
                <div className="p-4 border-b border-gray-200 dark:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-800 dark:text-gray-200">输入参数</h4>
                    {inputParams && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(formatJson(inputParams));
                        }}
                        className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                      >
                        {copied ? (
                          <>
                            <Check className="w-3 h-3" />
                            <span>已复制</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>复制</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                  <div className="bg-gray-200 dark:bg-gray-200 rounded p-3 overflow-hidden">
                    {renderJsonContent(inputParams)}
                  </div>
                </div>
              )}

              {/* 工具输出部分 - 只在完成时显示，且不是 transfer_to_agent */}
              {status === 'completed' && result && !isTransferToAgent && (
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-800 dark:text-gray-200">工具输出</h4>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        copyToClipboard(formatJson(result));
                      }}
                      className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3" />
                          <span>已复制</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>复制</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="bg-gray-200 dark:bg-gray-600 rounded p-3 overflow-hidden">
                    {renderJsonContent(result)}
                  </div>
                </div>
              )}

              {/* 如果没有结果，显示状态信息 */}
              {!result && status === 'executing' && (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
                  <p>工具正在执行中...</p>
                </div>
              )}

              {!result && status === 'error' && (
                <div className="p-4 text-center text-red-500">
                  <p>工具执行失败</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}; 