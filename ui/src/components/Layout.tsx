import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  ListTodo, 
  FileText, 
  Settings,
  Brain,
  Activity,
  Sparkles,
  Menu,
  X
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Tasks', href: '/tasks', icon: ListTodo },
    { name: 'Files', href: '/files', icon: FileText },
    { name: 'Settings', href: '/settings', icon: Settings },
  ]

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  return (
    <div className="flex h-screen bg-apple-gray-50">
      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 256, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="glass border-r border-apple-gray-200/50 overflow-hidden"
          >
            <div className="flex flex-col h-full w-64">
              {/* Logo */}
              <div className="flex items-center gap-3 px-6 py-6 border-b border-apple-gray-200/50">
                <div className="w-10 h-10 bg-gradient-to-br from-apple-blue to-apple-purple rounded-xl flex items-center justify-center">
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-apple-gray-900">Agent</h1>
                  <p className="text-xs text-apple-gray-500">Symbolic Regression</p>
                </div>
              </div>

              {/* Navigation */}
              <nav className="flex-1 px-4 py-6">
                <div className="space-y-1">
                  {navigation.map((item) => {
                    const Icon = item.icon
                    const active = isActive(item.href)
                    
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={`nav-item ${active ? 'active' : ''}`}
                      >
                        <Icon className="w-5 h-5" />
                        <span>{item.name}</span>
                      </Link>
                    )
                  })}
                </div>
              </nav>

              {/* Status */}
              <div className="px-4 py-4 border-t border-apple-gray-200/50">
                <div className="glass rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-apple-gray-700">Agent Status</span>
                    <Activity className="w-4 h-4 text-apple-green animate-pulse-subtle" />
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-apple-green rounded-full"></div>
                    <span className="text-xs text-apple-gray-600">Connected</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="glass border-b border-apple-gray-200/50 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Sidebar Toggle Button */}
              <motion.button
                onClick={toggleSidebar}
                className="p-2 rounded-lg hover:bg-apple-gray-100 transition-colors"
                whileTap={{ scale: 0.95 }}
                title={sidebarOpen ? "收起侧边栏" : "展开侧边栏"}
              >
                {sidebarOpen ? (
                  <X className="w-5 h-5 text-apple-gray-600" />
                ) : (
                  <Menu className="w-5 h-5 text-apple-gray-600" />
                )}
              </motion.button>
              
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-apple-purple" />
                <h2 className="text-lg font-medium text-apple-gray-900">
                  {navigation.find(item => isActive(item.href))?.name || 'Dashboard'}
                </h2>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-apple-gray-500">
                {new Date().toLocaleDateString('zh-CN', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-apple-gray-50">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}

export default Layout