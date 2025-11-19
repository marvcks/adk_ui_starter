import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Menu, ChevronLeft, Paperclip } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import SessionList from './SessionList'
import { useAgentConfig } from '../hooks/useAgentConfig'
import { MessageAnimation, LoadingDots } from './MessageAnimation'
import { MemoizedMessage } from './MemoizedMessage'
import { ToolCallPanel } from './ToolCallPanel'
import FileUpload from './FileUpload'
import axios from 'axios'
import { Bot } from 'lucide-react'

const API_BASE_URL = ''  // Use proxy in vite config

interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: Date
  tool_name?: string
  tool_status?: string
  input_params?: any
  is_long_running?: boolean
  tool_result?: any
  isStreaming?: boolean
  usage_metadata?: {
    prompt_tokens?: number
    candidates_tokens?: number
    total_tokens?: number
  }
  charge_result?: {
    success: boolean
    code: string
    message: string
    biz_no?: string
  }
}

interface Session {
  id: string
  title: string
  created_at: string
  last_message_at: string
  message_count: number
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showLoadingDelay, setShowLoadingDelay] = useState(false)
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showFileUpload, setShowFileUpload] = useState(false)
  
  // 添加上传文件信息的状态
  const [uploadedFiles, setUploadedFiles] = useState<Array<{
    name: string;
    size: number;
    url: string;
  }>>([])
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messageIdef = useRef<Set<string>>(new Set())
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  // 移除了HTML预览相关的函数

  // Load agent configuration
  const { config, loading: configLoading } = useAgentConfig()

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  // 延迟显示加载动画，避免闪烁
  useEffect(() => {
    if (isLoading) {
      loadingTimeoutRef.current = setTimeout(() => {
        setShowLoadingDelay(true)
      }, 200) // 200ms 延迟
    } else {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current)
      }
      setShowLoadingDelay(false)
    }
    
    return () => {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current)
      }
    }
  }, [isLoading])

  const [ws, setWs] = useState<WebSocket | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')

  const parseBool = (v: any) => {
    if (typeof v === 'boolean') return v
    const s = String(v ?? '').toLowerCase()
    return s === 'true' || s === '1' || s === 'yes' || s === 'on'
  }

  const initialShowTool = (() => {
    const ls = localStorage.getItem('show_tool')
    if (ls !== null) return parseBool(ls)
    const envVal: any = (import.meta as any).env?.VITE_SHOW_TOOL
    return parseBool(envVal ?? true)
  })()

  const initialShowToolParams = (() => {
    const ls = localStorage.getItem('show_tool_params')
    if (ls !== null) return parseBool(ls)
    const envVal: any = (import.meta as any).env?.VITE_SHOW_TOOL_PARAMS
    return parseBool(envVal ?? true)
  })()

  const [showTool, setShowTool] = useState<boolean>(initialShowTool)
  const [showToolParams, setShowToolParams] = useState<boolean>(initialShowToolParams)

  useEffect(() => {
    localStorage.setItem('show_tool', String(showTool))
  }, [showTool])

  useEffect(() => {
    localStorage.setItem('show_tool_params', String(showToolParams))
  }, [showToolParams])

  useEffect(() => {
    // Keep track of current websocket instance
    let currentWebSocket: WebSocket | null = null
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

    // Connect to WebSocket
    const connectWebSocket = () => {
      // Clean up any existing connection
      if (currentWebSocket?.readyState === WebSocket.OPEN || currentWebSocket?.readyState === WebSocket.CONNECTING) {
        currentWebSocket.close()
      }
      
      setConnectionStatus('connecting')
      
      // 从cookie中获取用户的AccessKey和ClientName
      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop()?.split(';').shift();
        return null;
      }
      
      const appAccessKey = getCookie('appAccessKey');
      const clientName = getCookie('clientName');

      console.log('appAccessKey: ', appAccessKey)
      console.log('clientName: ', clientName)
      
      // 动态获取 WebSocket URL，支持代理和远程访问
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.hostname
      const port = window.location.port
      let wsUrl = `${protocol}//${host}`
      if (port) {
        wsUrl += `:${port}`
      }
      wsUrl += '/ws'
      
      // 如果有认证信息，添加到查询参数中
      if (appAccessKey || clientName) {
        const params = new URLSearchParams()
        if (appAccessKey) params.append('appAccessKey', appAccessKey)
        if (clientName) params.append('clientName', clientName)
        wsUrl += `?${params.toString()}`
        // console.log('Connecting to WebSocket with authentication parameters')
      }
      
      console.log('Connecting to WebSocket:', wsUrl)
      const websocket = new WebSocket(wsUrl)
      currentWebSocket = websocket
      
      websocket.onopen = () => {
        // console.log('WebSocket connected')
        setConnectionStatus('connected')
        setWs(websocket)
        
        // 如果没有通过查询参数认证，仍然发送认证消息作为备用方案
        if (!appAccessKey && !clientName) {
          const sendAuthInfo = () => {
            try {
              // 再次尝试从cookie获取认证信息
              const appAccessKey = getCookie('appAccessKey');
              const clientName = getCookie('clientName');
              
              if (appAccessKey || clientName) {
                console.log('Sending authentication info to WebSocket server');
                websocket.send(JSON.stringify({
                  type: 'authenticate',
                  appAccessKey: appAccessKey || '',
                  clientName: clientName || ''
                }));
              } else {
                console.log('No authentication info found in cookies');
              }
            } catch (error) {
              console.error('Error sending authentication info:', error);
            }
          }
          
          // 延迟发送认证信息，确保WebSocket连接稳定
          setTimeout(sendAuthInfo, 100);
        }
      }
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // console.log('Received WebSocket message:', data)
          handleWebSocketMessage(data)
        } catch (error) {
          // console.error('WebSocket message error:', error)
        }
      }
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('disconnected')
      }

      websocket.onclose = () => {
        // console.log('WebSocket disconnected')
        setConnectionStatus('disconnected')
        setWs(null)
        
        // Auto-reconnect after 3 seconds
        reconnectTimeout = setTimeout(() => {
          // console.log('Attempting to reconnect...')
          connectWebSocket()
        }, 3000)
      }
    }

    connectWebSocket()
    
    return () => {
      // Clean up on unmount
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (currentWebSocket) {
        currentWebSocket.close()
      }
    }
  }, [])

  const scrollToBottom = () => {
    // 使用setTimeout确保DOM更新后再滚动
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      // 备用方案：如果scrollIntoView不起作用，直接操作滚动容器
      const scrollContainer = messagesEndRef.current?.parentElement?.parentElement
      if (scrollContainer) {
        // 滚动到底部，但留出一点空间
        const targetScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight
        scrollContainer.scrollTo({
          top: targetScroll,
          behavior: 'smooth'
        })
      }
    }, 100)
  }

  // Session management functions
  const handleCreateSession = useCallback(async () => {
    if (ws && connectionStatus === 'connected' && !isCreatingSession) {
      setIsCreatingSession(true)
      // 清空当前消息
      setMessages([])
      ws.send(JSON.stringify({ type: 'create_session' }))
      // 设置超时，避免永久等待
      setTimeout(() => {
        setIsCreatingSession(false)
      }, 3000)
    }
  }, [ws, connectionStatus, isCreatingSession])

  const handleSelectSession = useCallback(async (sessionId: string) => {
    if (ws && connectionStatus === 'connected') {
      ws.send(JSON.stringify({ 
        type: 'switch_session',
        session_id: sessionId 
      }))
    }
  }, [ws, connectionStatus])

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    if (ws && connectionStatus === 'connected') {
      ws.send(JSON.stringify({ 
        type: 'delete_session',
        session_id: sessionId 
      }))
    }
  }, [ws, connectionStatus])

  const handleSend = () => {
    if (!input.trim()) return
    if (!ws || connectionStatus !== 'connected') {
      alert('未连接到服务器，请稍后重试')
      return
    }

    // 构建发送给服务器的消息内容，包含用户输入和文件信息
    let serverMessageContent = input
    
    // 如果有上传的文件，追加文件信息到服务器消息
    if (uploadedFiles.length > 0) {
      const fileInfos = uploadedFiles.map(file => 
        `已上传文件: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)\n文件URL: ${file.url}`
      ).join('\n\n')
      
      serverMessageContent = serverMessageContent + '\n\n' + fileInfos
    }

    // 显示在聊天界面的消息内容，只包含用户输入，不包含文件信息
    const displayMessageContent = input

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: displayMessageContent,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, newMessage])
    setInput('')
    setIsLoading(true)
    
    // 清空已上传的文件列表
    setUploadedFiles([])
    
    // 隐藏文件上传组件
    setShowFileUpload(false)
    
    // 发送消息后立即滚动到底部
    scrollToBottom()

    // Send message through WebSocket (包含文件信息)
    ws.send(JSON.stringify({
      type: 'message',
      content: serverMessageContent
    }))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const handleWebSocketMessage = useCallback((data: any) => {
    const { type, content, timestamp, id } = data
    
    // 如果消息有ID，检查是否已经处理过
    if (id && messageIdef.current.has(id)) {
      return
    }
    if (id) {
      messageIdef.current.add(id)
    }
    
    // Handle authentication responses
    if (type === 'auth_success') {
      console.log('Authentication successful');
      return;
    }
    
    if (type === 'auth_error') {
      console.warn('Authentication failed:', data.message);
      return;
    }
    
    // Handle shell command responses
    if (type === 'shell_output') {
      // Removed shell output handling
      return
    }
    
    if (type === 'shell_error') {
      // Removed shell error handling
      return
    }
    
    if (type === 'sessions_list') {
      // 更新会话列表
      setSessions(data.sessions || [])
      setCurrentSessionId(data.current_session_id)
      setIsCreatingSession(false)
      return
    }
    
    if (type === 'session_messages') {
      // 加载会话历史消息
      const messages = data.messages || []
      setMessages(messages.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      })))
      // 清除消息ID缓存，避免重复
      messageIdef.current.clear()
      messages.forEach((msg: any) => {
        if (msg.id) {
          messageIdef.current.add(msg.id)
        }
      })
      setIsCreatingSession(false)
      return
    }
    
    if (type === 'user') {
      // Skip echoed user messages
      return
    }
    
    if (type === 'tool') {
      // Tool execution status
      const { tool_name, status, is_long_running, result, input_params, tool_input, args, function_call } = data
      let content = ''
      
      if (status === 'executing') {
        const icon = is_long_running ? '⏳' : '🔧'
        content = `${icon} 正在执行: **${tool_name}**${is_long_running ? ' (长时间运行)' : ''}`
      } else if (status === 'completed') {
        if (result) {
          // 保留原始格式，包括换行符
          content = `✅ 工具执行完成: **${tool_name}**\n\`\`\`json\n${result}\n\`\`\``
        } else {
          content = `✅ 工具执行完成: **${tool_name}**`
        }
      } else {
        content = `📊 工具状态更新: **${tool_name}** - ${status}`
      }
      
      // 优先使用 args 字段，这是 ADK 中工具调用的标准格式
      const toolInputParams = args || input_params || tool_input || function_call?.args
      
      const toolMessage: Message = {
        id: id || `tool-${Date.now()}`,
        role: 'tool' as const,
        content,
        timestamp: new Date(timestamp || Date.now()),
        tool_name,
        tool_status: status,
        input_params: toolInputParams,
        is_long_running,
        tool_result: result
      }
      
      // 使用函数式更新来避免消息重复
      setMessages(prev => {
        // 检查是否已经存在相同ID的消息
        if (prev.some(m => m.id === toolMessage.id)) {
          return prev
        }
        return [...prev, toolMessage]
      })
      // 工具消息后滚动到底部
      scrollToBottom()
      return
    }
    
    if (type === 'assistant' || type === 'response') {
      const assistantMessage: Message = {
        id: id || `assistant-${Date.now()}`,
        role: 'assistant',
        content: content || '',
        timestamp: new Date(timestamp || Date.now()),
        usage_metadata: data.usage_metadata,
        charge_result: data.charge_result
      }
      
      // 使用函数式更新来避免消息重复
      setMessages(prev => {
        // 检查是否已经存在相同ID的消息
        if (prev.some(m => m.id === assistantMessage.id)) {
          return prev
        }
        return [...prev, assistantMessage]
      })
      // 收到新消息后滚动到底部
      scrollToBottom()
    }
    
    if (type === 'complete') {
      setIsLoading(false)
      // 加载完成后滚动到底部
      scrollToBottom()
    }
    
    if (type === 'error') {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `❌ 错误: ${content}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
      setIsLoading(false)
    }
  }, [])

  const handleQuickPrompt = (title: string, content: string) => {
    setInput(content)
    handleSend()
  }

  const handleFileUpload = (file: File, uploadUrl?: string) => {
    // 保存上传的文件信息，不直接写入输入框
    if (uploadUrl) {
      setUploadedFiles(prev => [...prev, {
        name: file.name,
        size: file.size,
        url: uploadUrl
      }])
    }
    // 不要立即隐藏FileUpload组件，让用户看到上传成功的文件卡片
    // setShowFileUpload(false)
  }

  const handleUploadComplete = (result: any) => {
    if (result.success) {
      // 可以在这里添加成功提示或其他处理
      console.log('文件上传成功:', result)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Session List Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="border-r border-gray-200 dark:border-gray-700 overflow-hidden"
          >
            <div style={{ width: '280px' }}>
              <SessionList
                sessions={sessions}
                currentSessionId={currentSessionId}
                onCreateSession={handleCreateSession}
                onSelectSession={handleSelectSession}
                onDeleteSession={handleDeleteSession}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex transition-all duration-300">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 aurora-bg">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50 glass-premium glass-glossy flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Sidebar Toggle Button */}
            <motion.button
              onClick={toggleSidebar}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              whileTap={{ scale: 0.95 }}
              title={sidebarOpen ? "收起侧边栏" : "展开侧边栏"}
            >
              {sidebarOpen ? (
                <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              ) : (
                <Menu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              )}
            </motion.button>
            
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                {config.ui?.title || 'Agent'}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${
              connectionStatus === 'connected' 
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                : connectionStatus === 'connecting'
                ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-500' : 
                connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' : 
                'bg-red-500'
              }`} />
              <span>
                {connectionStatus === 'connected' ? '已连接' : 
                 connectionStatus === 'connecting' ? '连接中...' : 
                 '未连接'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowTool(v => !v)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                  showTool
                    ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800'
                    : 'bg-gray-100 text-gray-600 border-gray-300 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700'
                }`}
                title="显示工具"
              >
                工具
              </motion.button>
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowToolParams(v => !v)}
                disabled={!showTool}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                  showTool
                    ? (showToolParams
                        ? 'bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800'
                        : 'bg-gray-100 text-gray-600 border-gray-300 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700')
                    : 'opacity-50 cursor-not-allowed bg-gray-100 text-gray-400 border-gray-300 dark:bg-gray-800 dark:text-gray-500 dark:border-gray-700'
                }`}
                title="显示详情"
              >
                详情
              </motion.button>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 relative">
          <div className="max-w-4xl mx-auto space-y-4 h-full">
            {messages.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <img 
                    src="/agent-raise-orca.png" 
                    alt="ORCA Agent Logo" 
                    className="w-20 h-20 mx-auto mb-4 object-contain"
                  />
                  <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">
                    欢迎使用 {config.agent?.name || 'MolPilot'}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-500 mb-8">
                    {config.agent?.welcomeMessage || '请告诉我需要进行的计算化学任务'}
                  </p>
                  
                  {/* 快速提示词按钮 */}
                  <div className="grid grid-cols-2 gap-4 max-w-2xl mx-auto">
                    <button
                      onClick={() => handleQuickPrompt(
                        "Deep Learning-based Functional",
                        "对比不同泛函下水分子的偶极矩。使用PySCF计算B3LYP和Skala泛函下的偶极矩的差异，并与实验值进行对比。"
                      )}
                      className="p-4 text-left bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg transition-all duration-200 group"
                    >
                      <div className="font-medium text-gray-800 dark:text-gray-200 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        Deep Learning-based Functional
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-3">
                        对比不同泛函下水分子的偶极矩...
                      </div>
                    </button>
                    
                    <button
                      onClick={() => handleQuickPrompt(
                        "pKA",
                        "Calculate the pKa of acetic acid in water using two calculations at the B3LYP/6-31G* level of theorywith the CPCM implicit solvation model."
                      )}
                      className="p-4 text-left bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg transition-all duration-200 group"
                    >
                      <div className="font-medium text-gray-800 dark:text-gray-200 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        pKA
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-3">
                        Calculate the pKa of acetic acid in water using ...
                      </div>
                    </button>
                    
                    <button
                      onClick={() => handleQuickPrompt(
                        "Carbocations",
                        "给定一个碳正离子生成反应: R-H -- R+ + H-。你的任务是使用ORCA计算R-H为甲烷时的碳正离子生成焓和吉布斯自由能。\n\n请使用DFT方法（B3LYP泛函和6-31G*基组）优化这些结构（氢负离子除外），并从输出文件中提取相关信息，计算每种R-H的碳正离子生成焓和吉布斯自由能。将结果（单位为kcal/mol）以Markdown表格形式报告。\n\n关于电荷和自旋多重度：分子电荷为0，自旋多重度为1；碳正离子电荷为1，自旋多重度为1；氢负离子电荷为-1，自旋多重度为1。"
                      )}
                      className="p-4 text-left bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg transition-all duration-200 group"
                    >
                      <div className="font-medium text-gray-800 dark:text-gray-200 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        Carbocations
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-3">
                        给定一个碳正离子生成反应: R-H -- R+ + H-。你的任务是...
                      </div>
                    </button>
                    
                    <button
                      onClick={() => handleQuickPrompt(
                        "Case Study",
                        "研究添加隐式溶剂分子（水）如何改变丙氨酸分子的振动频率。使用ORCA比较气相计算和溶剂（CPCM）中的红外光谱计算结果。所有两个体系均使用PBE0/def2-TZVP方法。最后生成一份报告。"
                      )}
                      className="p-4 text-left bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg transition-all duration-200 group"
                    >
                      <div className="font-medium text-gray-800 dark:text-gray-200 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        Case Study
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-3">
                        研究隐式溶剂分子对丙氨酸分子振动频率的影响，比较气相和溶剂计算结果...
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <AnimatePresence initial={false} mode="popLayout">
                {(showTool ? messages : messages.filter(m => m.role !== 'tool')).map((message, index, visibleMessages) => (
                  message.role === 'tool' ? (
                    <motion.div
                      key={message.id}
                      layout="position"
                      initial={index === visibleMessages.length - 1 ? { opacity: 0, y: 20 } : false}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ duration: 0.2 }}
                      className="flex gap-4 justify-start"
                    >
                      <div className="w-full">
                        <ToolCallPanel
                          toolName={message.tool_name || ''}
                          status={message.tool_status || ''}
                          isLongRunning={message.is_long_running}
                          result={showToolParams ? message.tool_result : undefined}
                          timestamp={message.timestamp}
                          inputParams={showToolParams ? message.input_params : undefined}
                        />
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key={message.id}
                      layout="position"
                      initial={index === visibleMessages.length - 1 ? { opacity: 0, y: 20 } : false}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ duration: 0.2 }}
                      className={`flex gap-4 ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <MemoizedMessage
                        id={message.id}
                        role={message.role}
                        content={message.content}
                        timestamp={message.timestamp}
                        isLastMessage={index === visibleMessages.length - 1}
                        isStreaming={message.isStreaming}
                        tool_name={message.tool_name}
                        tool_status={message.tool_status}
                        input_params={message.input_params}
                        usage_metadata={message.usage_metadata}
                        charge_result={message.charge_result}
                      />
                    </motion.div>
                  )
                ))}
              </AnimatePresence>
            )}
            
            {showLoadingDelay && (
              <MessageAnimation isNew={true} type="assistant">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-4"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center shadow-lg">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-2xl px-4 py-3 shadow-sm border border-gray-200 dark:border-gray-700">
                    <LoadingDots />
                  </div>
                </motion.div>
              </MessageAnimation>
            )}
            
            {/* 底部垫高，确保最后一条消息不贴底 */}
            <div className="h-24" />
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-700 glass-premium p-4">
          <div className="max-w-4xl mx-auto">
            {/* File Upload Panel */}
            <AnimatePresence>
              {showFileUpload && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mb-4"
                >
                  <FileUpload
                    onFileUpload={handleFileUpload}
                    onUploadComplete={handleUploadComplete}
                    acceptedTypes={['.xyz', '.mol', '.sdf', '.pdb', '.txt', '.json', '.csv']}
                    maxSize={10}
                    className="border border-gray-200 dark:border-gray-600 rounded-xl"
                  />
                </motion.div>
              )}
            </AnimatePresence>
            
            <div className="flex gap-3">
              <div className="flex items-end">
                <button
                  onClick={() => setShowFileUpload(!showFileUpload)}
                  className={`p-2 rounded-lg transition-colors ${
                    showFileUpload 
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' 
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                  title="上传文件"
                >
                  <Paperclip className="w-5 h-5" />
                </button>
              </div>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息..."
                className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-all input-animated glow"
                rows={1}
                style={{
                  minHeight: '48px',
                  maxHeight: '200px'
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement
                  target.style.height = 'auto'
                  target.style.height = `${target.scrollHeight}px`
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading || connectionStatus !== 'connected'}
                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium hover:from-blue-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                发送
              </button>
            </div>
          </div>
        </div>
        </div>
        
        {/* Removed Shell Terminal */}
      </div>
    </div>
  )
}

export default ChatInterface