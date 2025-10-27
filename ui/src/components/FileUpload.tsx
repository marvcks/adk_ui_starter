import React, { useState, useCallback, useRef } from 'react'
import { Upload, X, CheckCircle, AlertCircle, FileText, Loader2 } from 'lucide-react'

interface FileUploadProps {
  onFileUpload?: (file: File, uploadUrl?: string) => void
  onUploadComplete?: (result: { success: boolean; message?: string; url?: string; error?: string }) => void
  acceptedTypes?: string[]
  maxSize?: number // MB
  className?: string
}

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error'
  progress: number
  message: string
  file?: File
  url?: string
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileUpload,
  onUploadComplete,
  acceptedTypes = ['.xyz', '.mol', '.sdf', '.pdb', '.txt', '.json', '.csv'],
  maxSize = 10,
  className = ''
}) => {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    progress: 0,
    message: ''
  })
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = useCallback((file: File): { valid: boolean; error?: string } => {
    // 检查文件大小
    if (file.size > maxSize * 1024 * 1024) {
      return {
        valid: false,
        error: `文件大小超过限制 (${maxSize}MB)。当前文件大小: ${(file.size / 1024 / 1024).toFixed(2)}MB`
      }
    }

    // 检查文件类型
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!acceptedTypes.includes(fileExtension)) {
      return {
        valid: false,
        error: `不支持的文件类型。支持的格式: ${acceptedTypes.join(', ')}`
      }
    }

    // 检查文件名
    if (file.name.length > 255) {
      return {
        valid: false,
        error: '文件名过长，请使用较短的文件名'
      }
    }

    // 检查特殊字符
    const invalidChars = /[<>:"/\\|?*]/
    if (invalidChars.test(file.name)) {
      return {
        valid: false,
        error: '文件名包含无效字符，请重命名文件'
      }
    }

    return { valid: true }
  }, [acceptedTypes, maxSize])

  const uploadFile = useCallback(async (file: File) => {
    const validation = validateFile(file)
    if (!validation.valid) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: validation.error || '文件验证失败',
        file
      })
      onUploadComplete?.({ success: false, error: validation.error })
      return
    }

    setUploadStatus({
      status: 'uploading',
      progress: 0,
      message: '正在上传文件...',
      file
    })

    try {
      const formData = new FormData()
      formData.append('file', file)

      const xhr = new XMLHttpRequest()

      // 监听上传进度
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100)
          setUploadStatus(prev => ({
            ...prev,
            progress,
            message: `上传中... ${progress}%`
          }))
        }
      })

      // 处理响应
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          try {
            const response = JSON.parse(xhr.responseText)
            if (response.success) {
              setUploadStatus({
                status: 'success',
                progress: 100,
                message: '文件上传成功！',
                file,
                url: response.url
              })
              onFileUpload?.(file, response.url)
              onUploadComplete?.({
                success: true,
                message: '文件上传成功',
                url: response.url
              })
            } else {
              throw new Error(response.message || '上传失败')
            }
          } catch (parseError) {
            throw new Error('服务器响应格式错误')
          }
        } else {
          let errorMessage = '上传失败'
          try {
            const errorResponse = JSON.parse(xhr.responseText)
            errorMessage = errorResponse.detail || errorResponse.message || errorMessage
          } catch {
            errorMessage = `HTTP ${xhr.status}: ${xhr.statusText}`
          }
          throw new Error(errorMessage)
        }
      })

      // 处理网络错误
      xhr.addEventListener('error', () => {
        throw new Error('网络连接错误，请检查网络连接')
      })

      // 处理超时
      xhr.addEventListener('timeout', () => {
        throw new Error('上传超时，请重试')
      })

      xhr.timeout = 60000 // 60秒超时
      xhr.open('POST', '/api/upload')
      xhr.send(formData)

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: errorMessage,
        file
      })
      onUploadComplete?.({ success: false, error: errorMessage })
    }
  }, [validateFile, onFileUpload, onUploadComplete])



  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      uploadFile(files[0])
    }
  }, [uploadFile])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      uploadFile(files[0])
    }
  }, [uploadFile])

  const handleClick = useCallback(() => {
    if (uploadStatus.status !== 'uploading') {
      fileInputRef.current?.click()
    }
  }, [uploadStatus.status])

  const resetUpload = useCallback(() => {
    setUploadStatus({
      status: 'idle',
      progress: 0,
      message: ''
    })
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [])

  const getStatusIcon = () => {
    switch (uploadStatus.status) {
      case 'uploading':
        return <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      case 'success':
        return <CheckCircle className="w-8 h-8 text-green-500" />
      case 'error':
        return <AlertCircle className="w-8 h-8 text-red-500" />
      default:
        return <Upload className="w-8 h-8 text-gray-400" />
    }
  }

  const getStatusColor = () => {
    switch (uploadStatus.status) {
      case 'uploading':
        return 'border-blue-300 bg-blue-50 dark:bg-blue-900/20'
      case 'success':
        return 'border-green-300 bg-green-50 dark:bg-green-900/20'
      case 'error':
        return 'border-red-300 bg-red-50 dark:bg-red-900/20'
      default:
        return isDragOver
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
    }
  }

  // 如果上传成功，显示简洁的文件卡片
  if (uploadStatus.status === 'success' && uploadStatus.file) {
    return (
      <div className={`inline-flex items-center ${className}`}>
        <div className="flex items-center space-x-2 bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-2 border border-gray-200 dark:border-gray-700">
          <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {uploadStatus.file.name}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Unknown
            </span>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              resetUpload()
            }}
            className="ml-2 p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title="移除文件"
          >
            <X className="w-3 h-3 text-gray-500 dark:text-gray-400" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <div
        className={`
          border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200
          ${getStatusColor()}
          ${uploadStatus.status === 'uploading' ? 'cursor-not-allowed' : 'cursor-pointer'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
          disabled={uploadStatus.status === 'uploading'}
        />

        <div className="flex flex-col items-center space-y-4">
          {getStatusIcon()}
          
          <div className="space-y-2">
            {uploadStatus.status === 'idle' ? (
              <>
                <p className="text-lg font-medium text-gray-700 dark:text-gray-300">
                  拖拽文件到此处或点击上传
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  支持格式: {acceptedTypes.join(', ')} (最大 {maxSize}MB)
                </p>
              </>
            ) : uploadStatus.status === 'uploading' ? (
              <>
                {uploadStatus.file && (
                  <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                    <FileText className="w-4 h-4" />
                    <span>{uploadStatus.file.name}</span>
                    <span>({(uploadStatus.file.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </div>
                )}
                <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  {uploadStatus.message}
                </p>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadStatus.progress}%` }}
                  />
                </div>
              </>
            ) : uploadStatus.status === 'error' ? (
              <>
                <p className="text-sm font-medium text-red-600 dark:text-red-400">
                  {uploadStatus.message}
                </p>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    resetUpload()
                  }}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  重新上传
                </button>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUpload