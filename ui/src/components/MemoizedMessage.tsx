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
  input_params
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
      
      {/* 复制按钮 */}
      <div className="flex justify-end mt-2">
        <button
          onClick={copyToClipboard}
          className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 shadow-sm"
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
         prevProps.input_params === nextProps.input_params;
});

MemoizedMessage.displayName = 'MemoizedMessage';