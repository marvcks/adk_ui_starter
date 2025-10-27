import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createCodeComponent } from './EnhancedCodeBlock';
import { MemoizedMarkdown } from './MemoizedMarkdown';
import { StreamingText } from './MessageAnimation';

interface MessageProps {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: Date;
  isLastMessage?: boolean;
  isStreaming?: boolean;
  tool_name?: string;
  tool_status?: string;
  input_params?: any;
  usage_metadata?: {
    prompt_tokens?: number;
    candidates_tokens?: number;
    total_tokens?: number;
  };
  charge_result?: {
    success: boolean;
    code: string;
    message: string;
    biz_no?: string;
    photon_amount?: number;
    rmb_amount?: number;
  };
}

export const MemoizedMessage = React.memo<MessageProps>(({
  id,
  role,
  content,
  timestamp,
  isLastMessage = false,
  isStreaming = false,
  tool_name,
  tool_status,
  input_params,
  usage_metadata,
  charge_result
}) => {
  const [copied, setCopied] = useState(false);

  // 如果是工具消息，直接返回null，不展示
  if (role === 'tool') {
    return null;
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className={`max-w-[80%] ${role === 'user' ? 'ml-auto' : 'mr-auto'} group`}>
      <div className={`rounded-2xl px-4 py-3 shadow-sm ${
        role === 'user'
          ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white'
          : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 glass-premium shadow-depth'
      }`}>
        {role === 'assistant' ? (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ node, inline, className, children, ...props }: any) => {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <div className="bg-gray-50 border border-gray-200 rounded p-3 my-2 overflow-x-auto">
                      <pre className="text-sm font-mono text-gray-700">
                        <code className={className} {...props}>
                          {children}
                        </code>
                      </pre>
                    </div>
                  ) : (
                    <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-700" {...props}>
                      {children}
                    </code>
                  );
                },
                a({ node, children, href, ...props }: any) {
                  // 更精确的HTML文件检测
                  const isHtmlFile = href && (
                    href.endsWith('.html') || 
                    href.endsWith('.htm') || 
                    href.includes('.html?') ||
                    href.includes('.htm?') ||
                    href.includes('.html#') ||
                    href.includes('.htm#')
                  );
                  
                  // 提取文件名，处理各种URL格式
                  let fileName = 'file.html';
                  if (href) {
                    try {
                      const url = new URL(href, window.location.href);
                      const pathParts = url.pathname.split('/');
                      const lastPart = pathParts[pathParts.length - 1];
                      if (lastPart && (lastPart.includes('.html') || lastPart.includes('.htm'))) {
                        fileName = lastPart;
                      } else if (lastPart) {
                        fileName = lastPart + '.html';
                      }
                    } catch {
                      // 如果URL解析失败，使用简单的字符串处理
                      const parts = href.split('/');
                      const lastPart = parts[parts.length - 1];
                      if (lastPart) {
                        fileName = lastPart.split('?')[0].split('#')[0];
                        if (!fileName.includes('.')) {
                          fileName += '.html';
                        }
                      }
                    }
                  }
                  
                  if (isHtmlFile) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
                        {...props}
                      >
                        {children}
                      </a>
                    );
                  }
                  
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
                      {...props}
                    >
                      {children}
                    </a>
                  )
                },
                p({ children }: any) {
                  if (isLastMessage && isStreaming) {
                    return (
                      <p>
                        <StreamingText
                          text={String(children)}
                          isStreaming={true}
                        />
                      </p>
                    )
                  }
                  return <p>{children}</p>
                }
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        )}
      </div>
      
      {/* Token 使用量和复制按钮 - 仅对 AI 消息显示 */}
      {role === 'assistant' && (
        <div className="mt-3 space-y-2">
          {/* Token 使用量显示 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium">字数: {content.length}</span>
              {usage_metadata && (
                <>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <span>输入token: {usage_metadata.prompt_tokens || 0}</span>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <span>输出token: {usage_metadata.candidates_tokens || 0}</span>
                </>
              )}
            </div>
            
            {/* 复制按钮 */}
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="复制消息"
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
          
          {/* 收费信息显示 */}
          {charge_result && (
            <div className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${
              charge_result.success 
                ? ((charge_result.photon_amount || 0) > 0
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'
                    : (charge_result.message?.includes('累积')
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                        : 'bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800'))
                : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                charge_result.success 
                  ? ((charge_result.photon_amount || 0) > 0
                      ? 'bg-green-500'
                      : (charge_result.message?.includes('累积')
                          ? 'bg-blue-500'
                          : 'bg-gray-500'))
                  : 'bg-red-500'
              }`}></span>
              <span className="font-medium">
                {charge_result.success 
                  ? ((charge_result.photon_amount || 0) > 0 
                      ? '✓ 收费成功' 
                      : (charge_result.message?.includes('累积') 
                          ? '⏳ 费用累积中' 
                          : '✓ 免费使用'))
                  : '✗ 收费失败'
                }
              </span>
              <span className="text-gray-500 dark:text-gray-400">|</span>
              <span>
                消耗光子 {charge_result.photon_amount || 0} | RMB {(charge_result.rmb_amount || 0).toFixed(2)} 元
              </span>
              {charge_result.biz_no && (
                <>
                  <span className="text-gray-500 dark:text-gray-400">|</span>
                  <span className="font-mono">订单: {charge_result.biz_no}</span>
                </>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* 用户消息的复制按钮 */}
      {role === 'user' && (
        <div className="flex justify-end mt-2">
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="复制消息"
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
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // 只有当这些关键属性改变时才重新渲染
  return prevProps.id === nextProps.id &&
         prevProps.content === nextProps.content &&
         prevProps.isStreaming === nextProps.isStreaming &&
         prevProps.isLastMessage === nextProps.isLastMessage &&
         prevProps.tool_name === nextProps.tool_name &&
         prevProps.tool_status === nextProps.tool_status &&
         prevProps.input_params === nextProps.input_params &&
         JSON.stringify(prevProps.usage_metadata) === JSON.stringify(nextProps.usage_metadata) &&
         JSON.stringify(prevProps.charge_result) === JSON.stringify(nextProps.charge_result);
});

MemoizedMessage.displayName = 'MemoizedMessage';