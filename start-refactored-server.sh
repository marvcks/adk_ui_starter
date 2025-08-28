#!/bin/bash

echo "🚀 启动重构后的 Agent WebSocket 服务器..."
echo "📡 使用模块化架构，Session 模式运行 rootagent"
echo "🌐 WebSocket 端点: ws://localhost:8000/ws"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到，请先安装 Python3"
    exit 1
fi

# 检查依赖
echo "🔍 检查依赖..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "❌ FastAPI 未安装，正在安装..."
    pip3 install fastapi uvicorn
fi

if ! python3 -c "import google.adk" &> /dev/null; then
    echo "❌ Google ADK 未安装，请先安装 Google ADK"
    exit 1
fi

# 启动服务器
echo "✅ 依赖检查完成，启动服务器..."
echo ""

cd "$(dirname "$0")"
python3 websocket-server-refactored.py 