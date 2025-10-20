import { useState, useEffect } from 'react'
import axios from 'axios'

interface AgentConfig {
  agent: {
    name: string
    description: string
    welcomeMessage: string
  }
  ui: {
    title: string
    theme?: {
      primaryColor: string
      secondaryColor: string
    }
    features: {
      showFileExplorer: boolean
      showSessionList: boolean
      enableFileUpload?: boolean
    }
  }
  files: {
    outputDirectory: string
    watchDirectories: string[]
  }
  websocket: {
    host: string
    port: number
    reconnectInterval?: number
  }
}

const defaultConfig: AgentConfig = {
  agent: {
    name: 'MolPilot',
    description: '计算化学智能体',
    welcomeMessage: '请告诉我需要进行的计算化学任务'
  },
  ui: {
    title: 'MolPilot',
    features: {
      showFileExplorer: true,
      showSessionList: true
    }
  },
  files: {
    outputDirectory: 'output',
    watchDirectories: ['output']
  },
  websocket: {
    host: 'localhost',
    port: 8000
  }
}

export function useAgentConfig() {
  const [config, setConfig] = useState<AgentConfig>(defaultConfig)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await axios.get('/api/config')
        setConfig(response.data)
        
        // Update document title
        if (response.data.ui?.title) {
          document.title = response.data.ui.title
        }
      } catch (err) {
        console.error('Failed to load agent config:', err)
        setError('Failed to load configuration')
        // Use default config on error
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  return { config, loading, error }
}